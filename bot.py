# bot.py
import os
import json
import time
import threading
from flask import Flask
from dotenv import load_dotenv
from rpc_manager import get_web3
from telegram_notifier import send_alert
from ai_agent import analyze_and_act, save_watchers_state

# Load .env locally (Render uses environment variables directly)
load_dotenv()

# -------------------------
# CONFIG FROM ENV VARIABLES
# -------------------------
BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"
ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_BALANCER = os.getenv("ENABLE_BALANCER", "false").lower() == "true"
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"
ENABLE_ORACLE = os.getenv("ENABLE_ORACLE", "true").lower() == "true"

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

MAX_GAS_GWEI = int(os.getenv("MAX_GAS_GWEI", 40))
ABSOLUTE_MAX_GAS_GWEI = int(os.getenv("ABSOLUTE_MAX_GAS_GWEI", 600))
MIN_REWARD_USD = float(os.getenv("MIN_REWARD_USD", 1.0))
PROFIT_MULTIPLIER = float(os.getenv("PROFIT_MULTIPLIER", 4.0))
FAIL_PAUSE_MINS = int(os.getenv("FAIL_PAUSE_MINS", 10))
MAIN_LOOP_SLEEP_S = int(os.getenv("MAIN_LOOP_SLEEP_S", 60))

WATCHERS_FILE = "watchers.json"

# -------------------------
# INIT WEB3
# -------------------------
w3 = get_web3()

# Exit if bot disabled
if not BOT_ENABLED:
    print("⏸ BOT_DISABLED via env — exiting.")
    try:
        send_alert("Bot disabled via environment variable. No jobs running.")
    except Exception:
        pass
    exit(0)

# Load watchers safely
if os.path.exists(WATCHERS_FILE):
    with open(WATCHERS_FILE, "r") as f:
        watchers = json.load(f)
else:
    watchers = []

fail_count = 0

def save_watchers():
    save_watchers_state(watchers)

def run_bot():
    global fail_count
    print("🚀 Oracle Bot started...")

    config = {
        "min_reward_usd": MIN_REWARD_USD,
        "profit_multiplier": PROFIT_MULTIPLIER,
        "absolute_max_gas_gwei": ABSOLUTE_MAX_GAS_GWEI,
    }

    while True:
        try:
            for watcher in watchers:
                protocol = watcher.get("protocol", "").lower()
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

                try:
                    tx_hash = analyze_and_act(w3, watcher, PUBLIC_ADDRESS, PRIVATE_KEY, config)
                    if tx_hash:
                        msg = f"✅ {name} harvested: {tx_hash}"
                        print(msg)
                        try:
                            send_alert(msg)
                        except Exception:
                            pass
                        save_watchers()
                        fail_count = 0  # reset fail count after success
                    else:
                        # log skipped harvest
                        last_decision = watcher.get("last_decision", {})
                        reason = last_decision.get("reason", "no_action")
                        print(f"⏸ {name} skipped: {reason}")

                except Exception as e:
                    print(f"❌ Error on {name}: {e}")
                    try:
                        send_alert(f"❌ Error on {name}: {e}")
                    except Exception:
                        pass
                    fail_count += 1
                    if fail_count >= 2:
                        print(f"⏸ Pausing bot for {FAIL_PAUSE_MINS} minutes after {fail_count} consecutive errors...")
                        try:
                            send_alert(f"Bot paused for {FAIL_PAUSE_MINS} mins after {fail_count} fails.")
                        except Exception:
                            pass
                        time.sleep(FAIL_PAUSE_MINS * 60)
                        fail_count = 0

            time.sleep(MAIN_LOOP_SLEEP_S)

        except Exception as loop_err:
            print(f"🔥 Main loop error: {loop_err}")
            try:
                send_alert(f"🔥 Main loop error: {loop_err}")
            except Exception:
                pass
            time.sleep(60)

# -------------------------
# FLASK HEALTHCHECK
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
