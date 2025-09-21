# utils/helpers.py

import json
import time
from web3 import Web3


def estimate_gas(w3: Web3, tx: dict) -> int:
    """Estimate gas for a given transaction."""
    try:
        return w3.eth.estimate_gas(tx)
    except Exception as e:
        print(f"⚠️ Gas estimation failed: {e}")
        return 0


def send_signed_tx(w3: Web3, signed_txn) -> str:
    """Send a signed transaction and return its hash."""
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        print(f"⚠️ Sending transaction failed: {e}")
        return None


def retry_async(func, retries: int = 3, delay: int = 2):
    """
    Retry a function call with exponential backoff.
    func: callable (no-arg function or lambda).
    """
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            print(f"⚠️ Retry {i+1}/{retries} failed: {e}")
            if i == retries - 1:
                raise
            time.sleep(delay * (i + 1))


def load_contract(w3: Web3, contract_address: str, abi_path: str):
    """
    Load a contract instance using its ABI and address.
    - w3: Web3 instance
    - contract_address: Deployed contract address
    - abi_path: Path to ABI JSON file
    """
    try:
        with open(abi_path, "r") as f:
            abi = json.load(f)
        return w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
    except Exception as e:
        print(f"⚠️ Failed to load contract {contract_address}: {e}")
        return None
