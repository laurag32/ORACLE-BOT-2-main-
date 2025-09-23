import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv
from flask import Blueprint, jsonify
from telegram_notifier import send_alert   # 👈 Telegram integration

load_dotenv()

# Collect RPCs from .env
RPC_URLS = [
    os.getenv("POLYGON_RPC_1"),
    os.getenv("POLYGON_RPC_2"),
    os.getenv("POLYGON_RPC_3"),
    os.getenv("POLYGON_RPC_4"),
]

# Remove None or empty
RPC_URLS = [rpc for rpc in RPC_URLS if rpc]

if not RPC_URLS:
    raise RuntimeError("❌ No RPC endpoints found in .env (POLYGON_RPC_1...POLYGON_RPC_4)")

# Failover settings
FAIL_LIMIT = 3            # max fails before cooldown
COOLDOWN_SECONDS = 300    # 5 minutes
ALERT_THRESHOLD = 5 * 60  # send alert if all RPCs dead for >5 mins

rpc_status = {
    rpc: {"fails": 0, "cooldown_until": 0, "last_ok": None, "was_dead": False}
    for rpc in RPC_URLS
}
last_all_dead = None

def get_web3():
    """
    Return a working Web3 provider with failover, cooldown,
    and Telegram alerts for RPC down/up events.
    """
    global last_all_dead

    while True:
        shuffled = RPC_URLS[:]
        random.shuffle(shuffled)
        now = time.time()
        working = False

        for rpc in shuffled:
            status = rpc_status[rpc]

            # Skip if in cooldown
            if now < status["cooldown_until"]:
                continue

            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    print(f"[RPC Manager] ✅ Connected via {rpc}")
                    
                    # Reset fail counter on success
                    if status["was_dead"]:
                        send_alert(f"✅ RPC back online: {rpc}")
                        status["was_dead"] = False

                    rpc_status[rpc]["fails"] = 0
                    rpc_status[rpc]["last_ok"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                    last_all_dead = None  # reset tracker
                    return w3

                else:
                    print(f"[RPC Manager] ⚠️ Failed to connect {rpc}")
                    status["fails"] += 1

            except Exception as e:
                print(f"[RPC Manager] ❌ Error with {rpc}: {e}")
                status["fails"] += 1

            # Apply cooldown if too many fails
            if status["fails"] >= FAIL_LIMIT:
                status["cooldown_until"] = now + COOLDOWN_SECONDS
                status["was_dead"] = True
                print(f"[RPC Manager] ⏸ {rpc} in cooldown for {COOLDOWN_SECONDS//60} mins")

        # If we reached here, no RPC worked
        if not working:
            if last_all_dead is None:
                last_all_dead = now
            elif now - last_all_dead > ALERT_THRESHOLD:
                send_alert("🚨 All Polygon RPCs unreachable for 5+ minutes. Bot is stalled.")
                last_all_dead = now  # reset so we don’t spam alerts

            print("[RPC Manager] 🌐 All RPCs failed or cooling down. Retrying in 30s...")
            time.sleep(30)

# -------------------------
# Flask Blueprint for RPC status
# -------------------------
rpc_bp = Blueprint("rpc_status", __name__)

@rpc_bp.route("/rpc-status")
def rpc_status_endpoint():
    """
    Return JSON with health info for all RPCs.
    """
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
