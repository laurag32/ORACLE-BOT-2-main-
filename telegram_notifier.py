import os, requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing in .env!")

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        response = requests.post(url, json=payload)
        if not response.ok:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Telegram send exception: {e}")
