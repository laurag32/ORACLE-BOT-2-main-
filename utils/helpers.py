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
    return web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)


# -------------------------
# Get current gas price in gwei
# -------------------------
def get_gas_price(web3: Web3):
    """
    Returns current gas price in gwei.
    """
    return web3.eth.gas_price // 10**9  # wei → gwei


# -------------------------
# Check if gas is safe to execute a transaction
# -------------------------
def is_gas_safe(current_gas_gwei, max_gas_gwei=40, absolute_max_gwei=600):
    """
    Returns True if current gas is <= max_gas_gwei.
    Raises ValueError if gas > absolute_max_gwei.
    """
    if current_gas_gwei > absolute_max_gwei:
        raise ValueError(f"🔥 Gas too high! ({current_gas_gwei} gwei) exceeds absolute max ({absolute_max_gwei})")
    return current_gas_gwei <= max_gas_gwei


# -------------------------
# Send signed transaction
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Send a transaction to harvest or claim rewards.
    """
    # Determine method based on protocol
    method_name = "harvest" if watcher["protocol"] != "balancer" else "claimRewards"
    func = getattr(contract.functions, method_name)

    # Build transaction
    tx = func().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price,
    })

    # Sign and send
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()


# -------------------------
# Decide if bot should update based on watcher object
# -------------------------
def should_update(watcher):
    """
    Check if enough time has passed since last update.
    Uses watcher's 'last_harvest' and 'min_idle_minutes'.
    """
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
