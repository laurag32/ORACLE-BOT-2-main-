import csv
import os
import time

LOG_FILE = "logs/profit_log.csv"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_profit(job_name, profit_usd, gas_price, tx_hash):
    """
    Logs each successful harvest or oracle update
    """
    timestamp = int(time.time())
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "job_name", "profit_usd", "gas_gwei", "tx_hash"])
        writer.writerow([timestamp, job_name, profit_usd, gas_price, tx_hash])
