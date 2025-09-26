import os
import json
import time
import threading
from flask import Flask

from rpc_manager import get_web3
from telegram_notifier import send_alert
from ai_agent import analyze_and_act

# --------------------------
# Environment-based config
# --------------------------
config = {
    "max_gas_gwei": int(os.getenv("MAX_GAS_GWEI", "55")),
    "min_profit_ratio": float(os.getenv("MIN_PROFIT_RATIO", "0.10")),  # 10%
    "fail_pause_minutes": int(os.getenv("FAIL_PAUSE_MINUTES", "10")),
    "telegram": {
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "daily_summary_time": os.getenv("DAILY_SUMMARY_TIME", "23:55"),
        "enable_real_time_alerts": os.getenv("ENABLE_REAL_TIME_ALERTS", "true").lower() == "true"
    },
    "wallet": {
        "address": os.getenv("WALLET_ADDRESS"),
        "private_key": os.getenv("PRIVATE_KEY")
    }
}

# Bot toggles
BOT_ENABLED = os.getenv("BOT_ENABLED", "true").lower() == "true"
ENABLE_AUTOFARM = os.getenv("ENABLE_AUTOFARM", "true").lower() == "true"
ENABLE_BALANCER = os.getenv("ENABLE_BALANCER", "false").lower() == "true"
ENABLE_QUICKSWAP = os.getenv("ENABLE_QUICKSWAP", "true").lower() == "true"
ENABLE_ORACLE = os.getenv("ENABLE_ORACLE", "true").lower() == "true"

WATCHERS_FILE = "watchers.json"

# Init web3
w3 = get_web3()

# Exit if bot disabled
if not BOT_ENABLED:
    print("⏸ BOT_DISABLED via environment — exiting.")
    try:
        send_alert("Bot disabled via environment. No jobs running.")
    except Exception:
        pass
    exit(0)

# Load watchers
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
                    tx_hash = analyze_and_act(
                        w3,
                        watcher,
                        config["wallet"]["address"],
                        config["wallet"]["private_key"],
                        config
                    )

                    if tx_hash:
                        msg = f"✅ {name} harvested: {tx_hash}"
                        print(msg)
                        if config["telegram"]["enable_real_time_alerts"]:
                            try:
                                send_alert(msg)
                            except Exception:
                                pass
                        save_watchers()
                        fail_count = 0
                    else:
                        pass

                except Exception as e:
                    print(f"❌ Error on {name}: {e}")
                    if config["telegram"]["enable_real_time_alerts"]:
                        try:
                            send_alert(f"❌ Error on {name}: {e}")
                        except Exception:
                            pass
                    fail_count += 1
                    if fail_count >= 2:
                        print(f"⏸ Pausing for {config['fail_pause_minutes']} mins after 2 fails...")
                        if config["telegram"]["enable_real_time_alerts"]:
                            try:
                                send_alert(f"Bot paused for {config['fail_pause_minutes']} mins after 2 fails.")
                            except Exception:
                                pass
                        time.sleep(config['fail_pause_minutes'] * 60)
                        fail_count = 0

            time.sleep(int(os.getenv("MAIN_LOOP_SLEEP_S", "60")))

        except Exception as loop_err:
            print(f"🔥 Main loop error: {loop_err}")
            if config["telegram"]["enable_real_time_alerts"]:
                try:
                    send_alert(f"🔥 Main loop error: {loop_err}")
                except Exception:
                    pass
            time.sleep(60)


# --------------------------
# Flask health endpoints
# --------------------------
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
