import os
from web3 import Web3

def get_web3():
    """
    Returns Web3 instance with RPC failover
    """
    rpc_urls = [os.getenv("RPC_URL_1"), os.getenv("RPC_URL_2")]
    for url in rpc_urls:
        try:
            w3 = Web3(Web3.HTTPProvider(url))
            if w3.is_connected():
                return w3
        except:
            continue
    raise Exception("All RPCs failed")
