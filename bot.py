# bot.py
import os
import json
import time
import threading
from flask import Flask

from ai_agent import analyze_and_act
from utils.helpers import load_config, load_watchers
from profit_logger import log_profit
from rpc_manager import get_w3
from telegram_notifier import send_alert


CONFIG_FILE = "config.json"
WATCHERS_FILE = "watchers.json"


def run_bot():
    config = load_config(CONFIG_FILE)
    watchers = load_watchers(WATCHERS_FILE)

    # Setup Web3 connection
    w3 = get_w3(config["deployment"]["network"])

    public_address = config["wallet"]["address"]
    private_key = config["wallet"].get("private_key")

    if not private_key:
        raise RuntimeError("⚠️ Private key not set in config.json under wallet.private_key")

    print("[BOT] 🚀 Oracle Harvester started...")

    while True:
        for watcher in watchers:
            try:
                # enforce idle time before next harvest
                min_idle = watcher.get("min_idle_minutes", 20) * 60
                last_harvest = watcher.get("last_harvest", 0)
                if time.time() - last_harvest < min_idle:
                    continue

                # Run AI Agent analysis & harvest
                tx_hash = analyze_and_act(w3, watcher, public_address, private_key, config)
                if tx_hash:
                    print(f"[BOT] ✅ Harvested {watcher['name']} -> {tx_hash}")
                    send_alert(f"✅ Harvested {watcher['name']} | {config['deployment']['explorer_url']}{tx_hash}")
                    log_profit(watcher, tx_hash, config)

                    # update last_harvest and persist to file
                    watcher["last_harvest"] = int(time.time())
                    with open(WATCHERS_FILE, "w") as f:
                        json.dump(watchers, f, indent=2)

                else:
                    print(f"[BOT] Skipped {watcher['name']} (decision=NO)")

            except Exception as e:
                print(f"[BOT] ❌ Error on {watcher.get('name')}: {e}")
                send_alert(f"❌ Error on {watcher.get('name')}: {e}")
                time.sleep(config.get("fail_pause_minutes", 10) * 60)

        # Sleep between full cycles
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

    # Start Flask server (for uptime checks / Render port binding)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
