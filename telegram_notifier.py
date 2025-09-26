import os
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_alert(message: str):
    """Send Telegram message via bot"""
    if not TOKEN or not CHAT_ID:
        print(f"[Telegram] Skipped (no credentials): {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
        if resp.status_code != 200:
            print(f"[Telegram] Failed {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")
