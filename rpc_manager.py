import os, random, time
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

RPC_URLS = [os.getenv(f"RPC_URL_{i}") for i in range(1,5)]
RPC_URLS = [r for r in RPC_URLS if r]

FAIL_LIMIT = 3
COOLDOWN_SECONDS = 120
ALERT_THRESHOLD = 300

rpc_status = {rpc: {"fails":0, "cooldown_until":0, "last_ok":None, "was_dead":False} for rpc in RPC_URLS}
_last_all_dead = None

def get_web3():
    global _last_all_dead
    while True:
        shuffled = RPC_URLS[:]
        random.shuffle(shuffled)
        now = time.time()
        for rpc in shuffled:
            status = rpc_status[rpc]
            if now < status["cooldown_until"]:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout':30}))
                if w3.is_connected():
                    status.update({"fails":0,"cooldown_until":0,"last_ok":time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),"was_dead":False})
                    print(f"[RPC] ✅ Connected via {rpc}")
                    return w3
                else:
                    status["fails"] += 1
            except:
                status["fails"] += 1
            if status["fails"] >= FAIL_LIMIT:
                status["cooldown_until"] = now + COOLDOWN_SECONDS
                status["was_dead"] = True
        if not any(not rpc_status[r]["was_dead"] and time.time() >= rpc_status[r]["cooldown_until"] for r in RPC_URLS):
            if _last_all_dead is None:
                _last_all_dead = now
            elif time.time() - _last_all_dead > ALERT_THRESHOLD:
                print("[RPC] 🚨 All RPCs appear dead or cooling.")
                _last_all_dead = now
        time.sleep(5)
