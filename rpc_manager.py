import os
import random

class RPCManager:
    def __init__(self):
        self.rpcs = [
            os.getenv("RPC_URL_1", "https://polygon-rpc.com"),
            os.getenv("RPC_URL_2"),
            os.getenv("RPC_URL_3")
        ]
        self.rpcs = [r for r in self.rpcs if r]

    def get_rpc(self):
        return random.choice(self.rpcs) if self.rpcs else "https://polygon-rpc.com"
