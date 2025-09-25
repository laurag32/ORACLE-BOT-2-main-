# ai_agent.py
import json
import time
import math
from typing import Optional, Dict, Any

from web3 import Web3
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

from utils.helpers import load_contract, get_gas_price  # send_tx used below if available
from price_fetcher import get_price
from telegram_notifier import send_alert

WATCHERS_FILE = "watchers.json"

# Configurable defaults (you can override in bot.py if you prefer)
DEFAULT_GAS_ESTIMATE = 210000
GAS_ESTIMATE_BUFFER = 1.20   # 20% buffer
RETRY_GAS_BUMP_FACTOR = 1.25
MAX_RETRIES = 3

# Common function name variants we'll probe
PENDING_FN_CANDIDATES = [
    ("pendingReward", ("pid", "address")),  # pendingReward(uint256,address)
    ("pendingReward", ()),                   # pendingReward()
    ("pendingRewards", ("pid", "address")),
    ("pendingTokens", ()),                   # some farms
    ("earned", ()),                          # balancer style
]

HARVEST_FN_CANDIDATES = [
    ("harvest", ()),         # harvest()
    ("harvest", ("pid",)),   # harvest(uint256)
    ("getReward", ()),       # sometimes called getReward
    ("claimRewards", ()),    # balancer
    ("claim", ()),           # generic
]


def save_watchers_state(watchers: list):
    """Persist updated watchers to file (atomic-ish)."""
    with open(WATCHERS_FILE, "w") as f:
        json.dump(watchers, f, indent=2)


def _call_read_safe(fn, *args):
    """Call contract read function safely returning None on failure."""
    try:
        return fn(*args)
    except (ContractLogicError, BadFunctionCallOutput, ValueError) as e:
        # Contract may not have the exact signature or chain not synced
        return None
    except Exception:
        return None


def detect_pending_reward(w3: Web3, contract, watcher: Dict[str, Any], wallet_address: str) -> Dict[str, Any]:
    """
    Try to detect a pending reward amount and token symbol from the contract.
    Returns dict: {"amount": float (token units), "symbol": str or None, "method": "fnName", "args": tuple}
    """
    # Try watcher-specified fields first
    if watcher.get("rewardAmount") and watcher.get("rewardToken"):
        return {"amount": float(watcher["rewardAmount"]), "symbol": watcher["rewardToken"], "method": "watcher_static", "args": ()}

    # 1) Try common pending functions with expected signatures
    for fn_name, sig in PENDING_FN_CANDIDATES:
        try:
            fn = getattr(contract.functions, fn_name, None)
            if not fn:
                continue

            # If signature expects pid and address
            if "pid" in sig and "address" in sig:
                pid = watcher.get("pid", 0)
                val = _call_read_safe(fn, pid, wallet_address)
                if val is not None:
                    return {"amount": float(val), "symbol": watcher.get("rewardToken"), "method": fn_name, "args": (pid, wallet_address)}

            # No-arg pendingReward()
            if len(sig) == 0:
                val = _call_read_safe(fn)
                if val is not None:
                    return {"amount": float(val), "symbol": watcher.get("rewardToken"), "method": fn_name, "args": ()}

        except Exception:
            continue

    # 2) Try earned()
    fn = getattr(contract.functions, "earned", None)
    if fn:
        val = _call_read_safe(fn)
        if val is not None:
            return {"amount": float(val), "symbol": watcher.get("rewardToken"), "method": "earned", "args": ()}

    # 3) Not found — fallback to watcher hint or zero
    return {"amount": float(watcher.get("rewardAmount", 0.0)), "symbol": watcher.get("rewardToken"), "method": "none", "args": ()}


def detect_harvest_function(contract, watcher: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find proper harvest/claim function and required args from ABI.
    Returns dict {"name": str, "args": tuple}
    """
    # Look for functions in ABI by name heuristics
    for name, sig in HARVEST_FN_CANDIDATES:
        fn = getattr(contract.functions, name, None)
        if fn:
            # fn may be overloaded — we'll try to introspect by building later
            # For now return name and rely on build step for arguments
            return {"name": name, "args_signature": sig}
    return None


def build_tx_for_function(w3: Web3, contract, func_name: str, watcher: Dict[str, Any], public_address: str):
    """
    Attempt to build a transaction dict for the chosen function name using sensible args
    Returns (tx_dict, used_args)
    """
    fn_obj = getattr(contract.functions, func_name, None)
    if fn_obj is None:
        raise ValueError(f"No function {func_name} found on contract")

    # Try calling with pid if that overloaded signature expects it
    pid = watcher.get("pid", None)
    try:
        # try no-arg first
        tx = fn_obj().build_transaction({
            "from": public_address,
            "nonce": w3.eth.get_transaction_count(public_address),
            "gasPrice": w3.eth.gas_price,
        })
        return tx, ()
    except Exception:
        # try with pid
        if pid is not None:
            try:
                tx = fn_obj(pid).build_transaction({
                    "from": public_address,
                    "nonce": w3.eth.get_transaction_count(public_address),
                    "gasPrice": w3.eth.gas_price,
                })
                return tx, (pid,)
            except Exception:
                pass

        # try variety: some functions expect (uint256,address) or arrays — we don't brute force
        raise ValueError(f"Could not build transaction for function {func_name} with common arg patterns.")


def estimate_gas_for_tx(w3: Web3, tx: dict) -> int:
    """Use web3.eth.estimate_gas with a buffer; fallback to default."""
    try:
        est = w3.eth.estimate_gas(tx)
        return int(est * GAS_ESTIMATE_BUFFER)
    except Exception as e:
        print(f"[AI Agent] Gas estimation failed: {e}; falling back to default {DEFAULT_GAS_ESTIMATE}")
        return DEFAULT_GAS_ESTIMATE


def compute_gas_cost_usd(gas_gwei: float, gas_limit: int) -> float:
    """Compute gas cost in USD using MATIC price from CoinGecko (price_fetcher)."""
    matic_price = get_price("MATIC")
    # gas_gwei * 1e-9 = gas price in ETH (in this case MATIC) per unit
    return (gas_gwei * 1e-9) * gas_limit * matic_price


def decide_to_harvest(watcher: Dict[str, Any], pending_info: Dict[str, Any], gas_gwei: float, gas_limit: int, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply safety/profit rules and return decision dict:
    { "should": bool, "reason": str, "expected_profit_usd": float, "gas_cost_usd": float }
    """
    reward_amount = float(pending_info.get("amount", 0.0))
    reward_token = pending_info.get("symbol", watcher.get("rewardToken", "MATIC"))
    token_price = get_price(reward_token) if reward_token else 0.0
    reward_usd = reward_amount * token_price

    gas_cost_usd = compute_gas_cost_usd(gas_gwei, gas_limit)

    min_reward_usd = config.get("min_reward_usd", 1.0)
    profit_multiplier = config.get("profit_multiplier", 2.0)
    abs_max_gas = config.get("absolute_max_gas_gwei", 600)

    if gas_gwei > abs_max_gas:
        return {"should": False, "reason": f"gas_above_absolute_max ({gas_gwei} gwei)", "expected_profit_usd": reward_usd, "gas_cost_usd": gas_cost_usd}

    expected_profit = reward_usd - gas_cost_usd
    if reward_usd < min_reward_usd:
        return {"should": False, "reason": f"reward_less_than_min (${reward_usd:.4f} < ${min_reward_usd})", "expected_profit_usd": expected_profit, "gas_cost_usd": gas_cost_usd}

    if expected_profit < (gas_cost_usd * (profit_multiplier - 1)):
        # This enforces profit >= gas * (profit_multiplier-1)
        return {"should": False, "reason": f"profit_ratio_too_low (exp_profit=${expected_profit:.4f})", "expected_profit_usd": expected_profit, "gas_cost_usd": gas_cost_usd}

    # Passed all checks — should harvest
    return {"should": True, "reason": "ok", "expected_profit_usd": expected_profit, "gas_cost_usd": gas_cost_usd}


def send_tx_with_retries(w3: Web3, contract, watcher: Dict[str, Any], public_address: str, private_key: str, func_name: str, func_args: tuple, gas_price_gwei: float, gas_limit: int):
    """
    Build, sign and send the transaction with a small retry/gas bump strategy.
    Returns tx_hash on success.
    """
    # Use contract.functions.<func_name>(*func_args) to create tx dict
    fn_obj = getattr(contract.functions, func_name)
    # create function call object
    call_obj = fn_obj(*func_args) if func_args else fn_obj()
    # build tx template
    tx = call_obj.build_transaction({
        "from": public_address,
        "nonce": w3.eth.get_transaction_count(public_address),
        "gasPrice": int(gas_price_gwei * 10**9),
    })

    # attempt retries
    local_gas_limit = gas_limit
    local_gas_price = gas_price_gwei
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tx["gas"] = local_gas_limit
            tx["gasPrice"] = int(local_gas_price * 10**9)

            # Sign and send using web3 account (assumes private key available and account unlocked)
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            # common errors: replacement underpriced or transient RPC issues
            errstr = str(e)
            print(f"[AI Agent] send_tx attempt {attempt} failed: {errstr}")
            # If we have underpriced/replacement error, bump gas price and retry
            if "replacement transaction underpriced" in errstr or "could not replace existing tx" in errstr or "replacement transaction" in errstr.lower():
                # increase gas price
                local_gas_price = local_gas_price * RETRY_GAS_BUMP_FACTOR
                local_gas_limit = int(local_gas_limit * 1.05)
                time.sleep(1 + attempt)  # short backoff
                continue
            # other errors - raise up so caller can count fail
            raise

    raise RuntimeError("Max retries hit while sending tx")


def analyze_and_act(w3: Web3, watcher: Dict[str, Any], public_address: str, private_key: str, config: Dict[str, Any]) -> Optional[str]:
    """
    Full analyze -> decide -> act pipeline for one watcher.
    Returns tx hash on success, None otherwise.
    """
    try:
        # Load contract
        contract = load_contract(w3, watcher["contract_address"], watcher["abi_file"])
    except Exception as e:
        print(f"[AI Agent] Failed to load contract for {watcher.get('name')}: {e}")
        watcher["last_error"] = f"load_contract_failed: {e}"
        return None

    # Step 1: detect pending reward
    pending = detect_pending_reward(w3, contract, watcher, public_address)
    # Step 2: detect harvest function
    harvest_info = detect_harvest_function(contract, watcher)
    if harvest_info is None:
        watcher["last_error"] = "no_harvest_function_found"
        return None

    func_name = harvest_info["name"]

    # Step 3: attempt build tx to estimate gas
    try:
        tx_template, used_args = build_tx_for_function(w3, contract, func_name, watcher, public_address)
        gas_limit = estimate_gas_for_tx(w3, tx_template)
    except Exception as e:
        print(f"[AI Agent] Error building tx for {func_name}: {e}")
        watcher["last_error"] = f"build_tx_error: {e}"
        return None

    # Step 4: compute gas price (gwei) and decision
    gas_price_gwei = get_gas_price(w3)
    decision = decide_to_harvest(watcher, pending, gas_price_gwei, gas_limit, config)

    # Log decision
    print(f"[AI Agent] Watcher {watcher.get('name')} pending={pending.get('amount'):.6f} {pending.get('symbol')} reward_usd~{pending.get('amount') * (get_price(pending.get('symbol') or watcher.get('rewardToken','MATIC'))):.4f} gas={gas_price_gwei}gwei limit={gas_limit} -> decision={decision['should']} reason={decision['reason']}")

    if not decision["should"]:
        watcher["last_decision"] = decision
        return None

    # Step 5: send tx with retries/bump
    try:
        tx_hash = send_tx_with_retries(w3, contract, watcher, public_address, private_key, func_name, used_args, gas_price_gwei, gas_limit)
        # On success update watchers state and return tx
        watcher["last_harvest"] = time.time()
        watcher.pop("last_error", None)
        watcher.pop("last_decision", None)

        # persist watchers.json
        # we'll read and update the file atomically here
        try:
            with open(WATCHERS_FILE, "r") as f:
                watchers = json.load(f)
            # find and update the matching watcher by contract_address + name or address
            updated = False
            for w in watchers:
                if w.get("contract_address") == watcher.get("contract_address") and w.get("name") == watcher.get("name"):
                    w.update(watcher)
                    updated = True
                    break
            if not updated:
                # fallback append
                watchers.append(watcher)
            save_watchers_state(watchers)
        except Exception as e:
            print(f"[AI Agent] Warning: couldn't persist watchers.json: {e}")

        return tx_hash

    except Exception as e:
        watcher["last_error"] = f"send_tx_failed: {e}"
        print(f"[AI Agent] send_tx ultimately failed: {e}")
        # bubble up notification
        send_alert(f"❌ {watcher.get('name')} send_tx failed: {e}")
        return None
