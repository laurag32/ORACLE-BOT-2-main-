# bot.py
import os
import json
import time
import threading
from flask import Flask

from rpc_manager import get_web3
from telegram_notifier import send_alert
from ai_agent import analyze_and_act

CONFIG_FILE = "config.json"
WATCHERS_FILE = "watchers.json"

with open(CONFIG_FILE) as f:
    config = json.load(f)

BOT_ENABLED = True
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")
w3 = get_web3()

with open(WATCHERS_FILE, "r") as f:
    watchers = json.load(f)

fail_count = 0

def save_watchers():
    tmp = WATCHERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(watchers, f, indent=2)
    os.replace(tmp, WATCHERS_FILE)

def run_bot():
    global fail_count
    print("🚀 Oracle Bot started...")

    while True:
        try:
            for watcher in watchers:
                try:
                    tx_hash = analyze_and_act(w3, watcher, PUBLIC_ADDRESS, PRIVATE_KEY, config)
                    if tx_hash:
                        msg = f"✅ {watcher['name']} harvested: {tx_hash}"
                        print(msg)
                        try:
                            send_alert(msg)
                        except Exception:
                            pass
                        save_watchers()
                        fail_count = 0
                except Exception as e:
                    print(f"❌ Error on {watcher['name']}: {e}")
                    try:
                        send_alert(f"❌ Error on {watcher['name']}: {e}")
                    except Exception:
                        pass
                    fail_count += 1
                    if fail_count >= 2:
                        print(f"⏸ Pausing for {config.get('fail_pause_minutes', 10)} mins after 2 fails...")
                        time.sleep(config.get('fail_pause_minutes', 10) * 60)
                        fail_count = 0
            time.sleep(int(os.getenv("MAIN_LOOP_SLEEP_S", 60)))
        except Exception as loop_err:
            print(f"🔥 Main loop error: {loop_err}")
            try:
                send_alert(f"🔥 Main loop error: {loop_err}")
            except Exception:
                pass
            time.sleep(60)

# Flask health endpoints
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
