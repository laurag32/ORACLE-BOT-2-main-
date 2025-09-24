import json
import time
from web3 import Web3

# -------------------------
# Load contract ABI and create contract object
# -------------------------
def load_contract(web3: Web3, contract_address: str, abi_path: str):
    with open(abi_path, "r") as f:
        abi = json.load(f)
    return web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

# -------------------------
# Get current gas price in gwei
# -------------------------
def get_gas_price(web3: Web3):
    return web3.eth.gas_price // 10**9  # wei → gwei

# -------------------------
# Check if gas is safe
# -------------------------
def is_gas_safe(current_gas_gwei, max_gas_gwei=600, absolute_max_gwei=600):
    if current_gas_gwei > absolute_max_gwei:
        raise ValueError(
            f"🔥 Gas too high! ({current_gas_gwei} gwei) exceeds absolute max ({absolute_max_gwei})"
        )
    return current_gas_gwei <= max_gas_gwei

# -------------------------
# Send signed transaction with dynamic gas and proper arguments
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Send harvest transaction. Auto-detects arguments if needed.
    Supports:
      - harvest()
      - harvest(uint256)
      - claimRewards()
    """
    protocol = watcher.get("protocol", "").lower()

    # Determine method and arguments
    if protocol == "balancer":
        method_name = "claimRewards"
        args = []
    else:
        method_name = "harvest"
        args = [watcher["pid"]] if "pid" in watcher else []

    # Get function object
    try:
        func = getattr(contract.functions, method_name)(*args)
    except AttributeError as e:
        raise ValueError(f"[Helpers] Contract does not have function {method_name} with args {args}: {e}")

    # Build transaction
    tx = func.build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price
    })

    # Dynamic gas estimation
    try:
        estimated_gas = web3.eth.estimate_gas(tx)
        tx["gas"] = int(estimated_gas * 1.2)  # 20% buffer
    except Exception as e:
        print(f"[Helpers] Gas estimation failed, using default 210000: {e}")
        tx["gas"] = 210000

    # Sign & send
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

# -------------------------
# Decide if bot should update
# -------------------------
def should_update(watcher):
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
