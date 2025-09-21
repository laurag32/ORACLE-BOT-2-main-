import json
import os
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
    Return current gas price in wei.
    """
    return web3.eth.gas_price

# Send signed transaction
def send_tx(web3: Web3, signed_tx):
    """
    Broadcast a signed transaction and return tx hash.
    """
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

# Decide if bot should update (dummy for now, tweak logic later)
def should_update(last_update_time: float, interval: int = 300):
    """
    Check if enough time has passed since last update.
    Default = 5 minutes.
    """
    import time
    return (time.time() - last_update_time) > interval
