import json
import time
from web3 import Web3

# Load ABI and contract
def load_contract(web3: Web3, contract_address: str, abi_file: str):
    try:
        with open(abi_file, "r") as f:
            abi = json.load(f)
        return web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
    except Exception as e:
        raise RuntimeError(f"Error loading contract {contract_address}: {e}")

# Get current gas price
def get_gas_price(web3: Web3):
    try:
        return web3.eth.gas_price
    except Exception as e:
        raise RuntimeError(f"Error fetching gas price: {e}")

# Send transaction
def send_tx(web3: Web3, tx, private_key: str):
    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        raise RuntimeError(f"Error sending transaction: {e}")

# Decide if Oracle/feed should update
def should_update(last_update: float, min_update_interval: int) -> bool:
    return time.time() - last_update >= min_update_interval
