import json
import time
from web3 import Web3

# -------------------------
# Load contract ABI and create contract object
# -------------------------
def load_contract(web3: Web3, contract_address: str, abi_path: str):
    """
    Load a smart contract using ABI JSON file.
    """
    with open(abi_path, "r") as f:
        abi = json.load(f)
    return web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi
    )

# -------------------------
# Get current gas price in gwei
# -------------------------
def get_gas_price(web3: Web3) -> int:
    """
    Return current gas price in gwei (not wei)
    """
    wei_price = web3.eth.gas_price
    gwei_price = wei_price // 1_000_000_000  # convert wei → gwei
    return gwei_price

# -------------------------
# Send signed transaction
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Build, sign, and send a transaction for a given contract + watcher.
    """
    nonce = web3.eth.get_transaction_count(public_address)

    # Determine which method to call
    if hasattr(contract.functions, "harvest"):
        tx_func = contract.functions.harvest()
    elif hasattr(contract.functions, "claimRewards"):
        tx_func = contract.functions.claimRewards()
    else:
        raise Exception("No valid harvest/claim method found in contract ABI.")

    tx = tx_func.build_transaction({
        "from": public_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "gas": 300000,  # adjust if needed
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    return tx_hash.hex()

# -------------------------
# Decide if bot should update
# -------------------------
def should_update(watcher: dict) -> bool:
    """
    Check if enough time has passed since last update for this watcher.
    Uses watcher["last_harvest"] and watcher["min_idle_minutes"].
    """
    now = time.time()
    last = watcher.get("last_harvest", 0)
    min_idle = watcher.get("min_idle_minutes", 5) * 60  # minutes → seconds

    if (now - last) >= min_idle:
        watcher["last_harvest"] = now  # update last run
        return True
    return False
