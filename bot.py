import os
import json
import time
import threading
from dotenv import load_dotenv
from flask import Flask
from utils.helpers import (
    load_contract,
    get_gas_price,
    send_tx,
    should_update,
    is_gas_safe
)
from profit_logger import log_profit
from telegram_notifier import send_alert
from rpc_manager import get_web3

# -------------------------
# Load env vars
# -------------------------
load_dotenv()

BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"
ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# -------------------------
# Safety params
# -------------------------
MAX_GAS_GWEI = 600
ABSOLUTE_MAX_GAS_GWEI = 600
MIN_PROFIT_USD = 1
GAS_MULTIPLIER = 4
FAIL_PAUSE_MINS = 10

# -------------------------
# Init web3
# -------------------------
w3 = get_web3()

if not BOT_ENABLED:
    print("⏸ BOT_DISABLED — exiting.")
    send_alert("Bot disabled via .env toggle.")
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
            try:
                is_gas_safe(gas_price, MAX_GAS_GWEI, ABSOLUTE_MAX_GAS_GWEI)
            except ValueError as e:
                print(str(e))
                send_alert(str(e))
                time.sleep(600)
                continue

            for watcher in watchers:
                protocol = watcher["protocol"]
                name = watcher.get("name", "Unnamed")

                if protocol == "autofarm" and not ENABLE_AUTOFARM:
                    continue
                if protocol == "quickswap" and not ENABLE_QUICKSWAP:
                    continue

                if not should_update(watcher):
                    continue

                contract = load_contract(
                    w3, watcher["contract_address"], watcher["abi_file"]
                )

                try:
                    print(f"✅ Ready to harvest {name} on {protocol}...")
                    tx_hash = send_tx(w3, contract, watcher, PRIVATE_KEY, PUBLIC_ADDRESS)

                    profit = log_profit(tx_hash, watcher, gas_price, PUBLIC_ADDRESS, contract)

                    if profit < MIN_PROFIT_USD or profit < gas_price * GAS_MULTIPLIER:
                        print(f"⚠️ Skipping {protocol}: profit too low (${profit:.2f}).")
                        continue

                    send_alert(f"✅ {protocol} job executed. Profit: ${profit:.2f}, Gas: {gas_price} gwei")

                    watcher["last_harvest"] = time.time()
                    with open("watchers.json", "w") as f:
                        json.dump(watchers, f, indent=2)

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
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
