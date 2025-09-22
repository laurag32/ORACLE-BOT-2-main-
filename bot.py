import os
import json
import time
import threading
from dotenv import load_dotenv
from utils.helpers import (
    load_contract,
    get_gas_price,
    send_tx,
    should_update,
)
from profit_logger import log_profit
from telegram_notifier import send_alert
from rpc_manager import get_web3
from flask import Flask

# -------------------------
# Load env vars
# -------------------------
load_dotenv()

BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"

ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_BALANCER = os.getenv("ENABLE_BALANCER", "true").lower() == "true"
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"
ENABLE_ORACLE = os.getenv("ENABLE_ORACLE", "true").lower() == "true"

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# Safety params
MAX_GAS_GWEI = 40          # Updated from 20 → 40 gwei
MIN_PROFIT_USD = 1
GAS_MULTIPLIER = 2
FAIL_PAUSE_MINS = 10

# Init web3
w3 = get_web3()

# Exit early if bot disabled
if not BOT_ENABLED:
    print("⏸ BOT_DISABLED in .env — exiting.")
    send_alert("Bot disabled via .env toggle. No jobs running.")
    exit(0)

# Load watchers
with open("watchers.json") as f:
    watchers = json.load(f)

fail_count = 0

# -------------------------
# Core bot loop
# -------------------------
def run_bot():
    global fail_count
    print("🚀 Oracle Bot started...")

    while True:
        try:
            gas_price = get_gas_price(w3)
            if gas_price > MAX_GAS_GWEI:
                print(f"⛽ Gas too high ({gas_price} gwei). Skipping.")
                time.sleep(60)
                continue

            for watcher in watchers:
                protocol = watcher["protocol"]
                name = watcher.get("name", "Unnamed")

                # Respect toggles
                if protocol == "autofarm" and not ENABLE_AUTOFARM:
                    continue
                if protocol == "balancer" and not ENABLE_BALANCER:
                    continue
                if protocol == "quickswap" and not ENABLE_QUICKSWAP:
                    continue
                if protocol == "oracle" and not ENABLE_ORACLE:
                    continue

                # Check if eligible to run
                if not should_update(watcher):
                    continue

                # Load contract
                contract = load_contract(
                    w3, watcher["contract_address"], watcher["abi_file"]
                )

                try:
                    tx = send_tx(w3, contract, watcher, PRIVATE_KEY, PUBLIC_ADDRESS)
                    profit = log_profit(tx, protocol, gas_price)

                    if profit < MIN_PROFIT_USD or profit < gas_price * GAS_MULTIPLIER:
                        print(f"⚠️ Skipping {protocol}: profit too low.")
                        continue

                    send_alert(
                        f"✅ {protocol} job executed. Profit: ${profit:.2f}, Gas: {gas_price} gwei"
                    )
                    fail_count = 0

                except Exception as e:
                    print(f"❌ Error on {protocol}: {e}")
                    fail_count += 1
                    send_alert(f"❌ Error on {protocol}: {str(e)}")

                    if fail_count >= 2:
                        print("⏸ Pausing after 2 fails...")
                        send_alert("Bot paused for 10 mins after 2 fails.")
                        time.sleep(FAIL_PAUSE_MINS * 60)
                        fail_count = 0

            time.sleep(60)

        except Exception as loop_err:
            print(f"🔥 Main loop error: {loop_err}")
            send_alert(f"🔥 Main loop error: {str(loop_err)}")
            time.sleep(60)


# -------------------------
# Flask health server
# -------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Oracle Bot is running!"

@app.route("/ping")
def ping():
    return "pong 🏓"

if __name__ == "__main__":
    # Run the bot in a background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Start Flask server for Render port binding
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
