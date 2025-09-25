# utils/helpers.py
import json
import time
from web3 import Web3
from web3.exceptions import ContractLogicError

# Load contract ABI and create contract object
def load_contract(web3: Web3, contract_address: str, abi_path: str):
    """
    Load a smart contract using ABI JSON file path (relative to repo).
    """
    with open(abi_path, "r") as f:
        abi = json.load(f)
    addr = Web3.to_checksum_address(contract_address)
    return web3.eth.contract(address=addr, abi=abi)


# Get current gas price in gwei
def get_gas_price(web3: Web3) -> int:
    """
    Return current gas price in GWEI (int).
    """
    try:
        wei = web3.eth.gas_price
        return int(wei // 10**9)
    except Exception:
        # fallback
        return 0


# Estimate gas for a prepared transaction dictionary safely
def estimate_gas_safe(web3: Web3, tx: dict, fallback: int = 210000) -> int:
    try:
        est = web3.eth.estimate_gas(tx)
        return int(est)
    except Exception as e:
        print(f"[Helpers] Gas estimate failed: {e}; using fallback {fallback}")
        return fallback


# Sign and broadcast a prepared tx dict (expects tx['gasPrice'] in wei)
def sign_and_send_tx(web3: Web3, tx: dict, private_key: str) -> str:
    """
    Signs the tx and sends it. Returns tx hash hex.
    """
    signed = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()


# Backwards-compatible simple send_tx wrapper (for tests / legacy)
def send_tx(web3: Web3, contract, watcher, private_key, public_address):
    """
    Legacy wrapper that calls a default harvest/claim with no args.
    Prefer ai_agent's robust pipeline.
    """
    method = getattr(contract.functions, "harvest", None) or getattr(contract.functions, "claimRewards", None)
    if method is None:
        raise ValueError("No harvest/claim function found on contract.")
    tx = method().build_transaction({
        "from": public_address,
        "nonce": web3.eth.get_transaction_count(public_address),
        "gasPrice": web3.eth.gas_price,
    })
    # estimate gas with helper
    gas_limit = estimate_gas_safe(web3, tx, fallback=210000)
    tx["gas"] = int(gas_limit * 1.2)
    return sign_and_send_tx(web3, tx, private_key)
