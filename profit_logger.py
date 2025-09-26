# profit_logger.py
import csv
import os
import time
from decimal import Decimal
from price_fetcher import PriceFetcher
from utils.helpers import load_config

CONFIG_FILE = "config.json"
LOG_FILE = "logs/profit_log.csv"

pf = PriceFetcher()
config = load_config(CONFIG_FILE)


def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)


def gas_cost_usd_from(gas_gwei: float, gas_limit: int) -> float:
    """Compute USD gas cost using MATIC price"""
    pf.fetch_prices()
    matic_price = pf.get_price("MATIC")
    return (gas_gwei * 1e-9) * gas_limit * matic_price


def log_profit(watcher: dict, tx_hash: str, config: dict) -> float:
    """
    Log profit into CSV. Returns profit in USD.
    """
    try:
        _ensure_logs_dir()

        pf.fetch_prices()

        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = watcher.get("rewardAmount", 0.0)

        token_price = pf.get_price(reward_token)
        matic_price = pf.get_price("MATIC")

        reward_usd = float(reward_amount) * float(token_price)

        # conservative fallback gas cost
        gas_cost_usd = (config["max_gas_gwei"] * 1e-9) * 210000 * matic_price

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
