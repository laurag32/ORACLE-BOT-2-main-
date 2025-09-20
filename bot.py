import json, time
from utils.helpers import send_harvest_tx, send_oracle_update_tx, get_gas_price_gwei, load_env, get_web3
from tracker.profit_tracker import ProfitTracker
from tracker.scheduler import setup_schedules
from profit_logger import log_profit
from summary_reporter import generate_summary
from telegram_notifier import send_alert

# Load environment and config
env = load_env()
config = json.load(open("config.json"))
watchers = json.load(open("watchers.json"))
oracle_jobs = json.load(open("oracle_jobs.json"))

# Initialize Web3
w3 = get_web3()
profit_tracker = ProfitTracker()

def run_jobs():
    # Harvest jobs
    for watcher in watchers:
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

    # Oracle jobs
    for job in oracle_jobs:
        elapsed = time.time() - job.get("last_update", 0)
        if elapsed < job.get("min_update_interval", 300):
            continue
        try:
            tx_hash, price = send_oracle_update_tx(w3, job, env, config)
            log_profit(job["name"], price, 0, tx_hash)
            profit_tracker.add_profit(job["name"], price)
            send_alert(f"📡 Oracle Update: {job['name']} = {price} | Tx: {tx_hash}")
            job["last_update"] = time.time()
        except Exception as e:
            send_alert(f"❌ Oracle Update Failed: {job['name']} | {str(e)}")

def main():
    send_alert("🚀 Oracle Bot started on Polygon (Harvest + Oracle jobs).")
    setup_schedules(schedule_time=config["telegram"]["daily_summary_time"], profit_tracker=profit_tracker)
    while True:
        run_jobs()
        time.sleep(60)

if __name__ == "__main__":
    main()
