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

# Load env vars
load_dotenv()

BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"
ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_BALANCER = os.getenv("ENABLE_BALANCER", "false").lower() == "true"  # disabled by default
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"
ENABLE_ORACLE = os.getenv("ENABLE_ORACLE", "true").lower() == "true"

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# Safety + policy
MAX_GAS_GWEI = int(os.getenv("MAX_GAS_GWEI", "40"))           # normal execution limit (you set to 40)
ABSOLUTE_MAX_GAS_GWEI = int(os.getenv("ABSOLUTE_MAX_GAS_GWEI", "600"))  # hard cutoff
MIN_PROFIT_USD = float(os.getenv("MIN_PROFIT_USD", "1.0"))
PROFIT_MULTIPLIER = float(os.getenv("PROFIT_MULTIPLIER", "4.0"))  # your temporary bump
FAIL_PAUSE_MINS = int(os.getenv("FAIL_PAUSE_MINS", "10"))

WATCHERS_FILE = "watchers.json"

# Init web3
w3 = get_web3()

# Exit if bot disabled
if not BOT_ENABLED:
    print("⏸ BOT_DISABLED in .env — exiting.")
    try:
        send_alert("Bot disabled via .env toggle. No jobs running.")
    except Exception:
        pass
    exit(0)

# Load watchers (must exist)
with open(WATCHERS_FILE, "r") as f:
    watchers = json.load(f)

fail_count = 0

def save_watchers():
    """Persist watchers list atomically."""
    tmp = WATCHERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(watchers, f, indent=2)
    os.replace(tmp, WATCHERS_FILE)


def run_bot():
    global fail_count
    print("🚀 Oracle Bot started...")

    config = {
        "min_reward_usd": MIN_PROFIT_USD,
        "profit_multiplier": PROFIT_MULTIPLIER,
        "absolute_max_gas_gwei": ABSOLUTE_MAX_GAS_GWEI,
    }

    while True:
        try:
            # get current gas (ai_agent will re-check inside, but we can log)
            # gas_price = get_gas_price(w3)  # ai_agent fetches fresh

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

                # Should be updated (ai_agent performs final check too)
                try:
                    # ai_agent handles detection, gas estimate, sending
                    tx_hash = analyze_and_act(w3, watcher, PUBLIC_ADDRESS, PRIVATE_KEY, config)
                    if tx_hash:
                        msg = f"✅ {name} harvested: {tx_hash}"
                        print(msg)
                        try:
                            send_alert(msg)
                        except Exception:
                            pass
                        # watcher updated & persisted inside ai_agent; we re-save to be safe
                        save_watchers()
                        fail_count = 0
                    else:
                        # Nothing done for this watcher (skip)
                        pass

                except Exception as e:
                    print(f"❌ Error on {name}: {e}")
                    try:
                        send_alert(f"❌ Error on {name}: {e}")
                    except Exception:
                        pass
                    fail_count += 1
                    if fail_count >= 2:
                        print("⏸ Pausing after 2 fails...")
                        try:
                            send_alert("Bot paused for 10 mins after 2 fails.")
                        except Exception:
                            pass
                        time.sleep(FAIL_PAUSE_MINS * 60)
                        fail_count = 0

            # main loop wait
            time.sleep(int(os.getenv("MAIN_LOOP_SLEEP_S", "60")))

        except Exception as loop_err:
            print(f"🔥 Main loop error: {loop_err}")
            try:
                send_alert(f"🔥 Main loop error: {loop_err}")
            except Exception:
                pass
            time.sleep(60)


# Flask health endpoints for Render / UptimeRobot
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Oracle Bot is running!"

@app.route("/ping")
def ping():
    return "pong 🏓"


if __name__ == "__main__":
    # Run bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Start Flask server for Render port binding
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
