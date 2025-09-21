import json
import os
import time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# Load contract ABI
def load_contract(w3: Web3, contract_address: str, abi_file: str):
    """Load a smart contract given an ABI file and contract address."""
    with open(abi_file, "r") as f:
        abi = json.load(f)
    return w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

# Gas estimator
def get_gas_price(w3: Web3):
    """Fetch current gas price in gwei."""
    return w3.eth.gas_price

# Send transaction
def send_tx(w3: Web3, contract_function, gas_limit=300000):
    """Sign and send a transaction."""
    try:
        nonce = w3.eth.get_transaction_count(PUBLIC_ADDRESS)

        tx = contract_function.build_transaction({
            "from": PUBLIC_ADDRESS,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": get_gas_price(w3),
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"[TX] Sent transaction: {tx_hash.hex()}")
        return tx_hash.hex()
    except Exception as e:
        print(f"[TX Error] {e}")
        return None

# Decision logic
def should_update(last_update, min_update_interval, gas_price, max_gas_gwei):
    """
    Decide whether an oracle/vault should be updated.
    Rules:
      - Must respect min idle time
      - Must skip if gas is too high
    """
    now = time.time()
    if now - last_update < min_update_interval:
        return False
    if gas_price > Web3.to_wei(max_gas_gwei, "gwei"):
        return False
    return True
