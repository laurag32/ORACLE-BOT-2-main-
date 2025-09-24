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
    return True

# -------------------------
# Send signed transaction dynamically
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Auto-selects correct function and handles:
      - harvest()
      - harvest(uint256)
      - claimRewards()
    """
    # Detect candidate functions
    method_candidates = [
        f for f in dir(contract.functions)
        if f.lower().startswith("harvest") or f == "claimRewards"
    ]
    if not method_candidates:
        raise ValueError(f"No valid harvest function found for {watcher['protocol']}")

    method_name = method_candidates[0]
    func = getattr(contract.functions, method_name)

    # Build transaction
    try:
        if "(uint256)" in method_name:
            # Provide PID argument if required
            pid = watcher.get("pid", 0)
            tx = func(pid).build_transaction({
                "from": public_address,
                "nonce": web3.eth.get_transaction_count(public_address),
                "gasPrice": web3.eth.gas_price,
            })
        else:
            tx = func().build_transaction({
                "from": public_address,
                "nonce": web3.eth.get_transaction_count(public_address),
                "gasPrice": web3.eth.gas_price,
            })
    except Exception as e:
        raise ValueError(f"Error building tx: {e}")

    # Estimate gas dynamically
    try:
        estimated_gas = web3.eth.estimate_gas(tx)
        tx["gas"] = int(estimated_gas * 1.2)  # +20% buffer
    except Exception as e:
        print(f"[Helpers] Gas estimation failed, using default 210000: {e}")
        tx["gas"] = 210000

    # Sign & send transaction
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
