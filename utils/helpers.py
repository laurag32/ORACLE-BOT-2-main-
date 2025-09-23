import json
import time
from web3 import Web3
from web3.exceptions import TransactionNotFound

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
# Send signed transaction
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Send harvest transaction. Auto-select method and handle uint256 argument if required.
    """
    # Determine method
    method_name = "harvest" if watcher["protocol"] != "balancer" else "claimRewards"

    # Find method function
    func_obj = getattr(contract.functions, method_name, None)
    if func_obj is None:
        raise ValueError(f"❌ Method {method_name} not found in contract.")

    # Check if function requires a uint256 argument
    abi_functions = [f for f in contract.abi if f.get("name") == method_name]
    requires_uint256 = False
    for f in abi_functions:
        for inp in f.get("inputs", []):
            if inp.get("type") == "uint256":
                requires_uint256 = True
                break

    # Build transaction
    if requires_uint256:
        pid = watcher.get("pid", 0)
        tx = func_obj(pid).build_transaction({
            "from": public_address,
            "nonce": web3.eth.get_transaction_count(public_address),
            "gasPrice": web3.eth.gas_price,
        })
    else:
        tx = func_obj().build_transaction({
            "from": public_address,
            "nonce": web3.eth.get_transaction_count(public_address),
            "gasPrice": web3.eth.gas_price,
        })

    # Sign and send
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
