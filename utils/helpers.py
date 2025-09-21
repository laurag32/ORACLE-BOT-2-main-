import json
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_contract(w3: Web3, contract_address: str, abi_path: str):
    """
    Load a contract instance from ABI and address.
    """
    with open(abi_path, "r") as abi_file:
        abi = json.load(abi_file)
    return w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)


def get_gas_price(w3: Web3) -> int:
    """
    Fetch current gas price from the connected network.
    """
    try:
        return w3.eth.gas_price
    except Exception as e:
        print(f"[ERROR] Could not fetch gas price: {e}")
        return int(30 * 1e9)  # fallback: 30 gwei


def send_tx(w3: Web3, tx, private_key: str) -> str:
    """
    Sign and send a raw transaction.
    Returns transaction hash.
    """
    try:
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        print(f"[ERROR] Transaction failed: {e}")
        return None


def should_update(last_update_ts: int, interval: int) -> bool:
    """
    Decide if it’s time to run the update again.
    last_update_ts: timestamp of last run (int)
    interval: time interval in seconds (int)
    """
    import time
    return (time.time() - last_update_ts) >= interval
