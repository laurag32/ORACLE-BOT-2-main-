# profit_logger.py
import csv
import os
import time
from price_fetcher import get_price

LOG_FILE = "logs/profit_log.csv"

def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

def gas_cost_usd_from(gas_gwei: float, gas_limit: int) -> float:
    matic_price = get_price("MATIC")
    return (gas_gwei * 1e-9) * gas_limit * matic_price

def safe_reward_amount(amount) -> float:
    """Safely convert any reward to float."""
    if amount is None:
        return 0.0
    try:
        return float(amount)
    except (ValueError, TypeError):
        if isinstance(amount, dict) and "pendingReward" in amount:
            try:
                return float(amount["pendingReward"])
            except Exception:
                return 0.0
        return 0.0

def log_profit(tx_hash: str, watcher: dict, gas_gwei: float, gas_limit: int) -> float:
    try:
        _ensure_logs_dir()
        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = safe_reward_amount(watcher.get("rewardAmount", 0.0))
        token_price = get_price(reward_token)
        reward_usd = reward_amount * token_price
        gas_cost_usd = gas_cost_usd_from(gas_gwei, gas_limit)
        profit = reward_usd - gas_cost_usd

        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow([
                    "timestamp",
                    "protocol",
                    "name",
                    "profit_usd",
                    "gas_cost_usd",
                    "tx_hash",
                    "reward_token",
                    "reward_amount"
                ])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                watcher.get("protocol"),
                watcher.get("name"),
                f"{profit:.6f}",
                f"{gas_cost_usd:.6f}",
                tx_hash,
                reward_token,
                f"{reward_amount:.8f}"
            ])

        print(f"[ProfitLogger] {watcher.get('protocol')} {watcher.get('name')} profit: ${profit:.6f}, gas: ${gas_cost_usd:.6f}, tx: {tx_hash}")
        return float(profit)

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
