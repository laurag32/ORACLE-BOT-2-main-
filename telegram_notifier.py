import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_alert(message: str):
    """Send a message to Telegram via bot."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[TelegramNotifier] Missing Telegram credentials")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[TelegramNotifier] Error: {resp.text}")
    except Exception as e:
        print(f"[TelegramNotifier] Exception: {e}")
