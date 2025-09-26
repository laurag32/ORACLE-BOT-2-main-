# ai_agent.py
import json
import time
from typing import Optional, Dict, Any
from web3 import Web3
from web3.exceptions import ContractLogicError, BadFunctionCallOutput
from utils.helpers import load_contract, get_gas_price
from price_fetcher import get_price
from telegram_notifier import send_alert

WATCHERS_FILE = "watchers.json"

# Gas and retry defaults
DEFAULT_GAS_ESTIMATE = 210000
GAS_ESTIMATE_BUFFER = 1.2
RETRY_GAS_BUMP_FACTOR = 1.25
MAX_RETRIES = 3

# Common function name variants
PENDING_FN_CANDIDATES = [
    ("pendingReward", ("pid", "address")),
    ("pendingReward", ()),
    ("pendingTokens", ()),
    ("earned", ())
]

HARVEST_FN_CANDIDATES = [
    ("harvest", ()),
    ("harvest", ("pid",)),
    ("getReward", ()),
    ("claimRewards", ()),
    ("claim", ())
]

def save_watchers_state(watchers: list):
    with open(WATCHERS_FILE, "w") as f:
        json.dump(watchers, f, indent=2)

def _call_read_safe(fn, *args):
    try:
        return fn(*args)
    except (ContractLogicError, BadFunctionCallOutput, ValueError):
        return None
    except Exception:
        return None

def detect_pending_reward(w3: Web3, contract, watcher: Dict[str, Any], wallet_address: str) -> Dict[str, Any]:
    if watcher.get("rewardAmount") and watcher.get("rewardToken"):
        return {"amount": float(watcher["rewardAmount"]), "symbol": watcher["rewardToken"], "method": "watcher_static", "args": ()}

    for fn_name, sig in PENDING_FN_CANDIDATES:
        fn = getattr(contract.functions, fn_name, None)
        if not fn:
            continue

        # pid + address signature
        if "pid" in sig and "address" in sig:
            pid = watcher.get("pid", 0)
            val = _call_read_safe(fn, pid, wallet_address)
            if val is not None:
                return {"amount": float(val), "symbol": watcher.get("rewardToken"), "method": fn_name, "args": (pid, wallet_address)}

        # no-arg
        if len(sig) == 0:
            val = _call_read_safe(fn)
            if val is not None:
                return {"amount": float(val), "symbol": watcher.get("rewardToken"), "method": fn_name, "args": ()}

    # fallback
    return {"amount": float(watcher.get("rewardAmount", 0.0)), "symbol": watcher.get("rewardToken"), "method": "none", "args": ()}

def detect_harvest_function(contract, watcher: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for name, sig in HARVEST_FN_CANDIDATES:
        fn = getattr(contract.functions, name, None)
        if fn:
            return {"name": name, "args_signature": sig}
    return None

def build_tx_for_function(w3: Web3, contract, func_name: str, watcher: Dict[str, Any], public_address: str):
    fn_obj = getattr(contract.functions, func_name, None)
    if fn_obj is None:
        raise ValueError(f"No function {func_name} found")

    pid = watcher.get("pid", None)
    try:
        tx = fn_obj().build_transaction({
            "from": public_address,
            "nonce": w3.eth.get_transaction_count(public_address),
            "gasPrice": w3.eth.gas_price,
        })
        return tx, ()
    except Exception:
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
        raise ValueError(f"Could not build tx for {func_name}")

def estimate_gas_for_tx(w3: Web3, tx: dict) -> int:
    try:
        est = w3.eth.estimate_gas(tx)
        return int(est * GAS_ESTIMATE_BUFFER)
    except Exception:
        return DEFAULT_GAS_ESTIMATE

def compute_gas_cost_usd(gas_gwei: float, gas_limit: int) -> float:
    matic_price = get_price("MATIC")
    return (gas_gwei * 1e-9) * gas_limit * matic_price

def decide_to_harvest(watcher: Dict[str, Any], pending_info: Dict[str, Any], gas_gwei: float, gas_limit: int, config: Dict[str, Any]) -> Dict[str, Any]:
    reward_amount = float(pending_info.get("amount", 0.0))
    reward_token = pending_info.get("symbol", watcher.get("rewardToken", "MATIC"))
    token_price = get_price(reward_token) or 0.0
    reward_usd = reward_amount * token_price

    gas_cost_usd = compute_gas_cost_usd(gas_gwei, gas_limit)

    min_reward_usd = config.get("min_reward_usd", 1.0)
    profit_multiplier = config.get("profit_multiplier", 2.0)
    abs_max_gas = config.get("absolute_max_gas_gwei", 600)

    if gas_gwei > abs_max_gas:
        return {"should": False, "reason": f"gas_above_absolute_max ({gas_gwei} gwei)", "expected_profit_usd": reward_usd, "gas_cost_usd": gas_cost_usd}

    expected_profit = reward_usd - gas_cost_usd
    if expected_profit < (gas_cost_usd * (profit_multiplier - 1)):
        return {"should": False, "reason": f"profit_ratio_too_low (exp_profit=${expected_profit:.4f})", "expected_profit_usd": expected_profit, "gas_cost_usd": gas_cost_usd}

    # Passed all checks
    return {"should": True, "reason": "ok", "expected_profit_usd": expected_profit, "gas_cost_usd": gas_cost_usd}

def send_tx_with_retries(w3: Web3, contract, watcher: Dict[str, Any], public_address: str, private_key: str, func_name: str, func_args: tuple, gas_price_gwei: float, gas_limit: int):
    fn_obj = getattr(contract.functions, func_name)
    call_obj = fn_obj(*func_args) if func_args else fn_obj()
    tx = call_obj.build_transaction({
        "from": public_address,
        "nonce": w3.eth.get_transaction_count(public_address),
        "gasPrice": int(gas_price_gwei * 1e9),
    })

    local_gas_limit = gas_limit
    local_gas_price = gas_price_gwei
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tx["gas"] = local_gas_limit
            tx["gasPrice"] = int(local_gas_price * 1e9)
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            errstr = str(e)
            if "replacement transaction" in errstr.lower():
                local_gas_price *= RETRY_GAS_BUMP_FACTOR
                local_gas_limit = int(local_gas_limit * 1.05)
                time.sleep(1 + attempt)
                continue
            raise
    raise RuntimeError("Max retries hit while sending tx")

def analyze_and_act(w3: Web3, watcher: Dict[str, Any], public_address: str, private_key: str, config: Dict[str, Any]) -> Optional[str]:
    try:
        contract = load_contract(w3, watcher["contract_address"], watcher["abi_file"])
    except Exception as e:
        watcher["last_error"] = f"load_contract_failed: {e}"
        return None

    pending = detect_pending_reward(w3, contract, watcher, public_address)
    harvest_info = detect_harvest_function(contract, watcher)
    if harvest_info is None:
        watcher["last_error"] = "no_harvest_function_found"
        return None

    func_name = harvest_info["name"]
    try:
        tx_template, used_args = build_tx_for_function(w3, contract, func_name, watcher, public_address)
        gas_limit = estimate_gas_for_tx(w3, tx_template)
    except Exception as e:
        watcher["last_error"] = f"build_tx_error: {e}"
        return None

    gas_price_gwei = get_gas_price(w3)
    decision = decide_to_harvest(watcher, pending, gas_price_gwei, gas_limit, config)

    if not decision["should"]:
        watcher["last_decision"] = decision
        return None

    try:
        tx_hash = send_tx_with_retries(w3, contract, watcher, public_address, private_key, func_name, used_args, gas_price_gwei, gas_limit)
        watcher["last_harvest"] = time.time()
        watcher.pop("last_error", None)
        watcher.pop("last_decision", None)

        # persist watchers.json
        try:
            with open(WATCHERS_FILE, "r") as f:
                watchers = json.load(f)
            updated = False
            for w in watchers:
                if w.get("contract_address") == watcher.get("contract_address") and w.get("name") == watcher.get("name"):
                    w.update(watcher)
                    updated = True
                    break
            if not updated:
                watchers.append(watcher)
            save_watchers_state(watchers)
        except Exception:
            pass

        return tx_hash

    except Exception as e:
        watcher["last_error"] = f"send_tx_failed: {e}"
        send_alert(f"❌ {watcher.get('name')} send_tx failed: {e}")
        return None
