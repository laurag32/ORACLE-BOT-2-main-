import json
import time
from datetime import datetime
from web3 import Web3
from utils.helpers import load_env, get_gas_price_gwei, send_harvest_tx, get_reward_usd
from tracker.profit_tracker import ProfitTracker
from tracker.scheduler import setup_schedules
from profit_logger import log_profit
from summary_reporter import generate_summary
from rpc_manager import get_web3
from telegram_notifier import send_alert  # ✅ fully integrated

# Load environment and configuration
env = load_env()
config = json.load(open("config.json"))
watchers = json.load(open("watchers.json"))

# Initialize Web3 with RPC failover
w3 = get_web3()

profit_tracker = ProfitTracker()

def run_watchers():
    """
    Main loop to process all watchers and execute harvests if profitable
    """
    for watcher in watchers:
        # Skip vaults harvested recently
        elapsed = time.time() - watcher.get("last_harvest", 0)
        if elapsed < watcher["min_idle_minutes"] * 60:
            continue

        gas_price = get_gas_price_gwei(w3)
        if gas_price > config["max_gas_gwei"]:
            send_alert(f"⏸ {watcher['protocol']} | Gas {gas_price} gwei > {config['max_gas_gwei']}, skipped")
            continue

        try:
            success, profit_usd, tx_hash = send_harvest_tx(w3, watcher, env, config, gas_price)
            if success:
                log_profit(watcher["protocol"], profit_usd, gas_price, tx_hash)
                profit_tracker.add_profit(watcher["protocol"], profit_usd)
                send_alert(f"✅ {watcher['protocol']} | ${profit_usd:.2f} | Tx: {tx_hash}")
                watcher["last_harvest"] = time.time()
            else:
                send_alert(f"⚠️ {watcher['protocol']} | Vault {watcher['name']} skipped or failed")
        except Exception as e:
            send_alert(f"❌ {watcher['protocol']} | ERROR: {str(e)}")

# Schedule daily summary and monthly log rotation
setup_schedules(schedule_time=config["telegram"]["daily_summary_time"], profit_tracker=profit_tracker)

def main():
    send_alert("🚀 Oracle Bot started on Polygon.")
    while True:
        run_watchers()
        time.sleep(60)

if __name__ == "__main__":
    main()
