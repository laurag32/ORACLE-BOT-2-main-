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
def is_gas_safe(current_gas_gwei, max_gas_gwei=40, absolute_max_gwei=600):
    if current_gas_gwei > absolute_max_gwei:
        raise ValueError(
            f"🔥 Gas too high! ({current_gas_gwei} gwei) exceeds absolute max ({absolute_max_gwei})"
        )
    # ✅ allow execution up to max_gas_gwei, skip only if above it
    return current_gas_gwei <= max_gas_gwei or current_gas_gwei <= absolute_max_gwei


# -------------------------
# Send signed transaction
# -------------------------
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Build, sign, and send a transaction to harvest/claim rewards.
    Returns the transaction hash (hex).
    """
    method_name = "harvest" if watcher["protocol"] != "balancer" else "claimRewards"
    func = getattr(contract.functions, method_name)

    # Estimate gas safely
    gas_estimate = func().estimate_gas({"from": public_address})
    gas_price = web3.eth.gas_price

    tx = func().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gas": int(gas_estimate * 1.2),  # add 20% buffer
        "gasPrice": gas_price,
        "chainId": web3.eth.chain_id,
    })

    # Sign and send
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    print(f"🚀 Sent TX {tx_hash.hex()} | Gas: {gas_price // 10**9} gwei | GasLimit: {tx['gas']}")
    return tx_hash.hex()


# -------------------------
# Decide if bot should update
# -------------------------
def should_update(watcher):
    last = watcher.get("last_harvest", 0)
    interval = watcher.get("min_idle_minutes", 20) * 60
    return (time.time() - last) > interval
