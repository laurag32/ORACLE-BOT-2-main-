import csv
import os
import time
from price_fetcher import get_price

LOG_FILE = "logs/profit_log.csv"

def log_profit(tx_hash, watcher, gas_gwei):
    try:
        os.makedirs("logs", exist_ok=True)

        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = watcher.get("rewardAmount", 0.0)

        token_price = get_price(reward_token)
        matic_price = get_price("MATIC")

        reward_usd = reward_amount * token_price
        gas_cost_usd = (gas_gwei * 1e-9) * 210000 * matic_price
        profit = reward_usd - gas_cost_usd

        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "protocol", "profit_usd", "gas_cost_usd", "tx_hash"])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                watcher.get("protocol", "unknown"),
                f"{profit:.4f}",
                f"{gas_cost_usd:.4f}",
                tx_hash
            ])

        print(f"[ProfitLogger] {watcher.get('protocol')} profit: ${profit:.4f}, gas: ${gas_cost_usd:.4f}, tx: {tx_hash}")
        return profit

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
