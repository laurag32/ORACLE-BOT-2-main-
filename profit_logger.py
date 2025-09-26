# profit_logger.py
import csv
import os
import time
from price_fetcher import global_price_fetcher
from utils.helpers import gas_cost_usd_from, load_contract
from web3.exceptions import ContractLogicError

LOG_FILE = "logs/profit_log.csv"

def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

def try_read_reward_from_contract(contract, watcher, public_address):
    try:
        if hasattr(contract.functions, "earned"):
            return float(contract.functions.earned().call()), watcher.get("rewardToken", "MATIC")
    except Exception:
        pass
    try:
        if hasattr(contract.functions, "pendingReward"):
            pid = watcher.get("pid")
            if pid is not None:
                return float(contract.functions.pendingReward(pid, public_address).call()), watcher.get("rewardToken", "MATIC")
            else:
                return float(contract.functions.pendingReward().call()), watcher.get("rewardToken", "MATIC")
    except Exception:
        pass
    return 0.0, watcher.get("rewardToken", "MATIC")

def log_profit(tx_hash: str, watcher: dict, gas_gwei: float, gas_limit: int, web3=None, config=None) -> float:
    try:
        _ensure_logs_dir()

        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = watcher.get("rewardAmount", 0.0)

        if web3 and watcher.get("abi_file") and watcher.get("contract_address"):
            try:
                contract = load_contract(web3, watcher["contract_address"], watcher["abi_file"])
                read_amount, read_token = try_read_reward_from_contract(contract, watcher, watcher.get("public_address", ""))
                if read_amount and read_amount > 0:
                    reward_amount, reward_token = read_amount, read_token
            except Exception as e:
                print(f"[ProfitLogger] Warning: couldn't read reward: {e}")

        token_price = global_price_fetcher.get_price(reward_token)
        matic_price = global_price_fetcher.get_price("MATIC")

        reward_usd = float(reward_amount) * float(token_price)
        gas_cost_usd = gas_cost_usd_from(gas_gwei, gas_limit, matic_price)

        profit = reward_usd - gas_cost_usd
        margin = (config or {}).get("profit_multiplier", 1.0)
        meets_margin = reward_usd >= gas_cost_usd * margin

        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "protocol", "name", "profit_usd", "gas_cost_usd", "tx_hash", "reward_token", "reward_amount", "meets_margin"])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                watcher.get("protocol"),
                watcher.get("name"),
                f"{profit:.6f}",
                f"{gas_cost_usd:.6f}",
                tx_hash,
                reward_token,
                f"{reward_amount:.8f}",
                meets_margin
            ])

        print(f"[ProfitLogger] {watcher.get('protocol')} {watcher.get('name')} profit: ${profit:.6f}, meets margin={meets_margin}, tx: {tx_hash}")
        return float(profit)

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
