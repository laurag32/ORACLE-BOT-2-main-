# telegram_notifier.py
import requests
import json
from utils.helpers import load_config

CONFIG_FILE = "config.json"
config = load_config(CONFIG_FILE)

BOT_TOKEN = config["telegram"]["bot_token"]
CHAT_ID = config["telegram"]["chat_id"]
REALTIME = config["telegram"]["enable_real_time_alerts"]


def send_alert(message: str):
    """
    Send Telegram alert if enabled.
    """
    if not REALTIME:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print(f"[Telegram] ⚠️ Failed to send: {r.text}")
    except Exception as e:
        print(f"[Telegram] ❌ Error: {e}")
