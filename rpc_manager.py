import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv
from telegram_notifier import send_alert

load_dotenv()

RPC_URLS = [os.getenv(f"RPC_URL_{i}") for i in range(1,5)]
RPC_URLS = [rpc for rpc in RPC_URLS if rpc]

if not RPC_URLS:
    raise RuntimeError("❌ No RPC endpoints found")

FAIL_LIMIT = 3
COOLDOWN = 300
ALERT_THRESHOLD = 300
rpc_status = {rpc: {"fails": 0, "cooldown_until": 0, "was_dead": False} for rpc in RPC_URLS}
last_all_dead = None

def get_web3():
    global last_all_dead
    while True:
        shuffled = RPC_URLS[:]
        random.shuffle(shuffled)
        now = time.time()
        for rpc in shuffled:
            status = rpc_status[rpc]
            if now < status["cooldown_until"]:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    if status["was_dead"]:
                        send_alert(f"✅ RPC back online: {rpc}")
                        status["was_dead"] = False
                    status["fails"] = 0
                    last_all_dead = None
                    return w3
                else:
                    status["fails"] += 1
            except:
                status["fails"] += 1

            if status["fails"] >= FAIL_LIMIT:
                status["cooldown_until"] = now + COOLDOWN
                status["was_dead"] = True
                print(f"[RPC Manager] ⏸ {rpc} in cooldown for {COOLDOWN//60} mins")

        if not any(Web3(Web3.HTTPProvider(rpc)).is_connected() for rpc in RPC_URLS):
            if last_all_dead is None:
                last_all_dead = now
            elif now - last_all_dead > ALERT_THRESHOLD:
                send_alert("🚨 All RPCs unreachable")
                last_all_dead = now
        time.sleep(30)
