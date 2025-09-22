import json
import time
from web3 import Web3

# Load contract ABI and create contract object
def load_contract(web3: Web3, contract_address: str, abi_path: str):
    with open(abi_path, "r") as f:
        abi = json.load(f)
    return web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

# Get current gas price in gwei
def get_gas_price(web3: Web3):
    return web3.eth.gas_price // 10**9  # wei → gwei

# Send signed transaction
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    # Determine function to call based on protocol
    fn_name = "harvest" if watcher["protocol"].lower() in ["autofarm", "quickswap"] else "claimRewards"

    # Build transaction
    tx = getattr(contract.functions, fn_name)().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

# Decide if bot should update based on last_harvest
def should_update(watcher):
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
