import csv
import os
import time

LOG_FILE = "logs/profit_log.csv"

def log_profit(protocol, profit_usd, gas_cost_usd, tx_hash):
    """Log profit data into a CSV file."""
    os.makedirs("logs", exist_ok=True)

    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "protocol", "profit_usd", "gas_cost_usd", "tx_hash"])
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), protocol, profit_usd, gas_cost_usd, tx_hash])

    print(f"[ProfitLogger] {protocol} profit: ${profit_usd:.4f}, gas: ${gas_cost_usd:.4f}, tx: {tx_hash}")
