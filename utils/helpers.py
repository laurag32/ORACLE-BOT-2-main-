import json
import os
import time
from web3 import Web3

# Load contract ABI and create contract object
def load_contract(web3: Web3, contract_address: str, abi_path: str):
    """
    Load a smart contract using ABI JSON file.
    """
    with open(abi_path, "r") as f:
        abi = json.load(f)
    return web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

# Get current gas price
def get_gas_price(web3: Web3):
    """
    Return current gas price in gwei.
    """
    return web3.eth.gas_price // 10**9  # convert wei → gwei

# Send signed transaction
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Example: Send a transaction to harvest or claim rewards.
    """
    # Construct transaction (dummy example, replace with actual method call)
    tx = contract.functions.harvest().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

# Decide if bot should update based on watcher object
def should_update(watcher):
    """
    Check if enough time has passed since last update.
    Uses watcher's 'last_harvest' and 'min_idle_minutes'.
    """
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
