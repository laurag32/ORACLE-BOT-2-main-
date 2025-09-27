# bot.py
import os
import json
import time
import threading
from dotenv import load_dotenv
from flask import Flask

from rpc_manager import get_web3
from telegram_notifier import send_alert
from ai_agent import analyze_and_act

# Load environment variables
load_dotenv()

BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"
ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_BALANCER = os.getenv("ENABLE_BALANCER", "false").lower() == "true"
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"
ENABLE_ORACLE = os.getenv("ENABLE_ORACLE", "true").lower() == "true"

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

MAX_GAS_GWEI = int(os.getenv("MAX_GAS_GWEI", "40"))
ABSOLUTE_MAX_GAS_GWEI = int(os.getenv("ABSOLUTE_MAX_GAS_GWEI", "600"))
MIN_PROFIT_USD = float(os.getenv("MIN_PROFIT_USD", "1.0"))
PROFIT_MULTIPLIER = float(os.getenv("PROFIT_MULTIPLIER", "4.0"))
FAIL_PAUSE_MINS = int(os.getenv("FAIL_PAUSE_MINS", "10"))

WATCHERS_FILE = "watchers.json"

# Initialize Web3
w3 = get_web3()

# Exit if bot disabled
if not BOT_ENABLED:
    print("⏸ BOT_DISABLED — exiting.")
    try:
        send_alert("Bot disabled via .env toggle. No jobs running.")
    except Exception:
        pass
    exit(0)

# Load watchers
try:
    with open(WATCHERS_FILE, "r") as f:
        watchers = json.load(f)
    print(f"✅ Loaded {len(watchers)} watchers")
except Exception as e:
    print(f"❌ Failed to load watchers.json: {e}")
    watchers = []

fail_count = 0

def save_watchers():
    """Persist watchers list safely."""
    try:
        tmp = WATCHERS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(watchers, f, indent=2)
        os.replace(tmp, WATCHERS_FILE)
    except Exception as e:
        print(f"[save_watchers] Failed: {e}")

def run_bot():
    global fail_count
    print("🚀 Bot thread starting...")

    config = {
        "min_reward_usd": MIN_PROFIT_USD,
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
                    print(f"[Bot] Checking {protocol} -> {name}")
                    tx_hash = analyze_and_act(w3, watcher, PUBLIC_ADDRESS, PRIVATE_KEY, config)
                    if tx_hash:
                        msg = f"✅ {name} harvested: {tx_hash}"
                        print(msg)
                        try:
                            send_alert(msg)
                        except Exception as te:
                            print(f"[Telegram] Failed to send alert: {te}")
                        save_watchers()
                        fail_count = 0
                    else:
                        print(f"[Bot] No action needed for {name}")

                except Exception as e:
                    print(f"[Bot Error] {name}: {e}")
                    try:
                        send_alert(f"[Bot Error] {name}: {e}")
                    except Exception:
                        pass
                    fail_count += 1
                    if fail_count >= 2:
                        print(f"⏸ Pausing for {FAIL_PAUSE_MINS} mins after {fail_count} consecutive fails")
                        try:
                            send_alert(f"Bot paused for {FAIL_PAUSE_MINS} mins after consecutive fails")
                        except Exception:
                            pass
                        time.sleep(FAIL_PAUSE_MINS * 60)
                        fail_count = 0

            time.sleep(int(os.getenv("MAIN_LOOP_SLEEP_S", "60")))

        except Exception as loop_err:
            print(f"[Main Loop Error] {loop_err}")
            try:
                send_alert(f"[Main Loop Error] {loop_err}")
            except Exception:
                pass
            time.sleep(60)


# Flask for health checks
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Oracle Bot is running!"

@app.route("/ping")
def ping():
    return "pong 🏓"

if __name__ == "__main__":
    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
