# utils/helpers.py
import json
from web3 import Web3

def load_contract(web3: Web3, contract_address: str, abi_path: str):
    with open(abi_path, "r") as f:
        abi = json.load(f)
    addr = Web3.to_checksum_address(contract_address)
    return web3.eth.contract(address=addr, abi=abi)

def get_gas_price(web3: Web3) -> int:
    try:
        wei = web3.eth.gas_price
        return int(wei // 10**9)
    except Exception:
        return 0

def estimate_gas_safe(web3: Web3, tx: dict, fallback: int = 210000) -> int:
    try:
        return int(web3.eth.estimate_gas(tx))
    except Exception as e:
        print(f"[Helpers] Gas estimate failed: {e}; fallback {fallback}")
        return fallback

def sign_and_send_tx(web3: Web3, tx: dict, private_key: str) -> str:
    signed = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()

def gas_cost_usd_from(gas_gwei: float, gas_limit: int, matic_price: float) -> float:
    return (gas_gwei * 1e-9) * gas_limit * matic_price
# utils/helpers.py (add to bottom of file)

import json

def load_config(path="config.json"):
    with open(path, "r") as f:
        return json.load(f)

def load_watchers(path="watchers.json"):
    with open(path, "r") as f:
        return json.load(f)
