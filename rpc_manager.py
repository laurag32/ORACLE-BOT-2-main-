# rpc_manager.py
import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Read RPC_URL_* from .env (supports RPC_URL_1..RPC_URL_4)
RPC_URLS = [
    os.getenv("RPC_URL_1"),
    os.getenv("RPC_URL_2"),
    os.getenv("RPC_URL_3"),
    os.getenv("RPC_URL_4"),
]
RPC_URLS = [r for r in RPC_URLS if r]

if not RPC_URLS:
    raise RuntimeError("❌ No RPC endpoints found in .env (RPC_URL_1...RPC_URL_4)")

FAIL_LIMIT = 3
COOLDOWN_SECONDS = 120
ALERT_THRESHOLD = 5 * 60

rpc_status = {rpc: {"fails": 0, "cooldown_until": 0, "last_ok": None, "was_dead": False} for rpc in RPC_URLS}
_last_all_dead = None

def get_web3():
    """
    Return a working Web3 provider with simple failover.
    This will loop until at least one RPC connects.
    """
    global _last_all_dead
    while True:
        shuffled = RPC_URLS[:]
        random.shuffle(shuffled)
        now = time.time()
        any_ok = False

        for rpc in shuffled:
            status = rpc_status[rpc]
            if now < status["cooldown_until"]:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    # reset fail counters
                    status["fails"] = 0
                    status["cooldown_until"] = 0
                    status["last_ok"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                    status["was_dead"] = False
                    print(f"[RPC Manager] ✅ Connected via {rpc}")
                    return w3
                else:
                    status["fails"] += 1
                    print(f"[RPC Manager] ⚠️ No connect: {rpc} (fails={status['fails']})")
            except Exception as e:
                status["fails"] += 1
                print(f"[RPC Manager] ❌ Error with {rpc}: {e}")

            if status["fails"] >= FAIL_LIMIT:
                status["cooldown_until"] = now + COOLDOWN_SECONDS
                status["was_dead"] = True
                print(f"[RPC Manager] ⏸ {rpc} in cooldown for {COOLDOWN_SECONDS//60} mins")

        # If none returned, wait and try again
        # Optionally, notify once if all dead
        if not any(not rpc_status[r]["was_dead"] and time.time() >= rpc_status[r]["cooldown_until"] for r in RPC_URLS):
            if _last_all_dead is None:
                _last_all_dead = now
            elif time.time() - _last_all_dead > ALERT_THRESHOLD:
                print("[RPC Manager] 🚨 All RPCs appear dead or cooling.")
                _last_all_dead = now

        time.sleep(5)
