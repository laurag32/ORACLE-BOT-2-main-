# profit_logger.py
import csv
import os
import time
from decimal import Decimal
from price_fetcher import get_price
from web3.exceptions import ContractLogicError

LOG_FILE = "logs/profit_log.csv"

def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

def gas_cost_usd_from(gas_gwei: float, gas_limit: int) -> float:
    """Compute USD gas cost using MATIC price"""
    matic_price = get_price("MATIC")
    # gas_gwei * 1e-9 = MATIC per gas unit
    return (gas_gwei * 1e-9) * gas_limit * matic_price

def try_read_reward_from_contract(contract, watcher, public_address):
    """
    Best-effort read of reward amount from contract after harvest.
    Returns (amount_token, token_symbol) or (0.0, watcher.get('rewardToken')) fallback.
    """
    # If watcher already supplies rewardAmount, use it
    if watcher.get("rewardAmount"):
        try:
            return float(watcher["rewardAmount"]), watcher.get("rewardToken")
        except Exception:
            pass

    # Try standard view functions
    try:
        # try earned()
        if hasattr(contract.functions, "earned"):
            val = contract.functions.earned().call()
            return float(val), watcher.get("rewardToken", "MATIC")
    except ContractLogicError:
        pass
    except Exception:
        pass

    try:
        # pendingReward(pid, address)
        if hasattr(contract.functions, "pendingReward"):
            pid = watcher.get("pid")
            if pid is not None:
                try:
                    val = contract.functions.pendingReward(pid, public_address).call()
                    return float(val), watcher.get("rewardToken", "MATIC")
                except Exception:
                    # try no-arg pendingReward()
                    try:
                        val = contract.functions.pendingReward().call()
                        return float(val), watcher.get("rewardToken", "MATIC")
                    except Exception:
                        pass
    except Exception:
        pass

    # fallback: zero
    return 0.0, watcher.get("rewardToken", "MATIC")


def log_profit(tx_hash: str, watcher: dict, gas_gwei: float, gas_limit: int, web3=None) -> float:
    """
    Log profit into CSV. Returns profit in USD (float).
    If `web3` and watcher['abi_file'] & watcher['contract_address'] present, attempt to read actual reward amount.
    """
    try:
        _ensure_logs_dir()

        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = watcher.get("rewardAmount", 0.0)

        # If web3 provided, try reading the contract for up-to-date rewardAmount
        if web3 and watcher.get("abi_file") and watcher.get("contract_address"):
            try:
                from utils.helpers import load_contract
                contract = load_contract(web3, watcher["contract_address"], watcher["abi_file"])
                read_amount, read_token = try_read_reward_from_contract(contract, watcher, watcher.get("public_address", ""))
                # Prefer contract-read amount if > 0
                if read_amount and read_amount > 0:
                    reward_amount = read_amount
                    reward_token = read_token
            except Exception as e:
                print(f"[ProfitLogger] Warning: couldn't read reward from contract: {e}")

        token_price = get_price(reward_token)
        matic_price = get_price("MATIC")

        reward_usd = float(reward_amount) * float(token_price)
        gas_cost_usd = gas_cost_usd_from(gas_gwei, gas_limit)

        profit = reward_usd - gas_cost_usd

        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "protocol", "name", "profit_usd", "gas_cost_usd", "tx_hash", "reward_token", "reward_amount"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), watcher.get("protocol"), watcher.get("name"), f"{profit:.6f}", f"{gas_cost_usd:.6f}", tx_hash, reward_token, f"{reward_amount:.8f}"])

        print(f"[ProfitLogger] {watcher.get('protocol')} {watcher.get('name')} profit: ${profit:.6f}, gas: ${gas_cost_usd:.6f}, tx: {tx_hash}")
        return float(profit)

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
