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
    is_gas_safe,
    get_pending_rewards  # 👈 new import
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

# -------------------------
# Safety params
# -------------------------
MAX_GAS_GWEI = 600            # ✅ harvest at anything ≤600
ABSOLUTE_MAX_GAS_GWEI = 600   # 🔒 hard stop if >600
MIN_PROFIT_USD = 1
FAIL_PAUSE_MINS = 10

# -------------------------
# Init web3
# -------------------------
w3 = get_web3()

# Exit if bot disabled
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
    print("🚀 Oracle Bot started in HARVEST mode...")

    while True:
        try:
            gas_price = get_gas_price(w3)

            # Gas safety check
            try:
                if not is_gas_safe(gas_price, MAX_GAS_GWEI, ABSOLUTE_MAX_GAS_GWEI):
                    print(f"⛽ Gas too high ({gas_price} gwei). Skipping this round.")
                    time.sleep(60)
                    continue
            except ValueError as e:
                print(str(e))
                send_alert(str(e))
                time.sleep(600)  # pause 10 min before retry
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
                    print(f"✅ Checking rewards for {name} on {protocol}...")
                    reward_token = watcher.get("rewardToken", "MATIC")

                    # 🔥 fetch actual pending rewards from contract
                    reward_amount = get_pending_rewards(contract, watcher, w3, PUBLIC_ADDRESS)

                    if reward_amount <= 0:
                        print(f"⚠️ No rewards to harvest for {protocol}.")
                        continue

                    print(f"💰 {protocol} pending rewards: {reward_amount} {reward_token}")

                    # build + send harvest tx
                    tx = send_tx(w3, contract, watcher, PRIVATE_KEY, PUBLIC_ADDRESS)

                    # compute profit using *real reward*
                    profit = log_profit(
                        tx,
                        protocol,
                        gas_price,
                        reward_token=reward_token,
                        reward_amount=reward_amount
                    )

                    if profit < MIN_PROFIT_USD:
                        print(f"⚠️ Skipping {protocol}: profit too low (${profit:.2f}).")
                        continue

                    send_alert(
                        f"✅ {protocol} harvested. Profit: ${profit:.2f}, Gas: {gas_price} gwei"
                    )
                    watcher["last_harvest"] = time.time()
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
    return "✅ Oracle Bot (HARVEST MODE) is running!"

@app.route("/ping")
def ping():
    return "pong 🏓"

if __name__ == "__main__":
    # Run the bot in a background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Start Flask server
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
