import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv
from telegram_notifier import send_alert
from flask import Blueprint, jsonify

load_dotenv()

# -------------------------
# Collect RPC URLs
# -------------------------
RPC_URLS = [
    os.getenv("RPC_URL_1"),
    os.getenv("RPC_URL_2"),
    os.getenv("RPC_URL_3"),
    os.getenv("RPC_URL_4"),
]
RPC_URLS = [rpc for rpc in RPC_URLS if rpc]

if not RPC_URLS:
    raise RuntimeError("❌ No RPC endpoints found in .env (RPC_URL_1...RPC_URL_4)")

# -------------------------
# Failover / cooldown settings
# -------------------------
FAIL_LIMIT = 3              # max fails before cooldown
COOLDOWN_SECONDS = 300      # 5 minutes cooldown
ALERT_THRESHOLD = 5 * 60    # 5 min alert if all dead

rpc_status = {
    rpc: {"fails": 0, "cooldown_until": 0, "last_ok": None, "was_dead": False} 
    for rpc in RPC_URLS
}
last_all_dead = None

# -------------------------
# Web3 provider with failover
# -------------------------
def get_web3():
    """
    Return a working Web3 instance.
    Handles failover, cooldowns, and Telegram alerts if all RPCs fail.
    """
    global last_all_dead
    while True:
        shuffled = RPC_URLS[:]
        random.shuffle(shuffled)
        now = time.time()
        working = False

        for rpc in shuffled:
            status = rpc_status[rpc]

            # Skip if cooling down
            if now < status["cooldown_until"]:
                continue

            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    working = True
                    if status["was_dead"]:
                        send_alert(f"✅ RPC back online: {rpc}")
                        status["was_dead"] = False
                    status["fails"] = 0
                    status["last_ok"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                    last_all_dead = None
                    return w3
                else:
                    status["fails"] += 1
            except Exception as e:
                print(f"[RPC Manager] ❌ Error with {rpc}: {e}")
                status["fails"] += 1

            # Apply cooldown if fails exceed limit
            if status["fails"] >= FAIL_LIMIT:
                status["cooldown_until"] = now + COOLDOWN_SECONDS
                status["was_dead"] = True
                print(f"[RPC Manager] ⏸ {rpc} in cooldown for {COOLDOWN_SECONDS//60} mins")

        # Alert if all RPCs dead
        if not working:
            if last_all_dead is None:
                last_all_dead = now
            elif now - last_all_dead > ALERT_THRESHOLD:
                send_alert("🚨 All RPCs unreachable for 5+ minutes. Bot is stalled.")
                last_all_dead = now

        print("[RPC Manager] 🌐 No RPCs available right now, retrying in 30s...")
        time.sleep(30)

# -------------------------
# Flask blueprint for RPC status
# -------------------------
rpc_bp = Blueprint("rpc_status", __name__)

@rpc_bp.route("/rpc-status")
def rpc_status_endpoint():
    now = time.time()
    report = {}
    for rpc, status in rpc_status.items():
        report[rpc] = {
            "fails": status["fails"],
            "cooldown_remaining": max(0, int(status["cooldown_until"] - now)),
            "last_ok": status["last_ok"],
            "was_dead": status["was_dead"]
        }
    return jsonify(report)
