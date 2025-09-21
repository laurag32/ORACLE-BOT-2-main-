import os
import random
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Load RPCs from .env
RPC_URLS = [
    os.getenv("RPC_URL_1"),
    os.getenv("RPC_URL_2"),
]

def get_web3():
    """Return a working Web3 provider with basic failover."""
    for _ in range(len(RPC_URLS)):
        rpc = random.choice(RPC_URLS)
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
            if w3.is_connected():
                return w3
        except Exception as e:
            print(f"[RPC Manager] Failed RPC {rpc}: {e}")
            continue
    raise RuntimeError("No working RPC available.")
