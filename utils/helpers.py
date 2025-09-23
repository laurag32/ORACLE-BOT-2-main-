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
    return True  # harvest allowed if <= absolute_max_gwei

# -------------------------
# Send signed transaction with dynamic gas estimation
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Send harvest transaction. Method auto-selected based on protocol.
    Estimates gas dynamically for any pool.
    """
    method_name = "harvest" if watcher["protocol"] != "balancer" else "claimRewards"
    func = getattr(contract.functions, method_name)

    # Build the transaction with dynamic gas limit
    transaction = func().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price,
    })

    # Estimate gas dynamically
    try:
        estimated_gas = web3.eth.estimate_gas(transaction)
        transaction["gas"] = int(estimated_gas * 1.2)  # Add 20% buffer
    except Exception as e:
        print(f"[Helpers] Gas estimation failed, using default 210000: {e}")
        transaction["gas"] = 210000  # fallback

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

# -------------------------
# Decide if bot should update
# -------------------------
def should_update(watcher):
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
