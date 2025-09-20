import os, json, requests
from web3 import Web3
from rpc_manager import get_web3

def load_env():
    return {
        "private_key": os.getenv("PRIVATE_KEY"),
        "public_address": os.getenv("PUBLIC_ADDRESS"),
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat": os.getenv("TELEGRAM_CHAT_ID"),
        "rpc_urls": [os.getenv("RPC_URL_1"), os.getenv("RPC_URL_2")]
    }

def get_gas_price_gwei(w3):
    return w3.eth.gas_price // 1_000_000_000

def send_harvest_tx(w3, watcher, env, config, gas_price):
    abi_path = f"abi/{watcher['protocol'].lower()}.json"
    contract = w3.eth.contract(address=Web3.to_checksum_address(watcher["address"]),
                               abi=json.load(open(abi_path)))
    nonce = w3.eth.get_transaction_count(env["public_address"])
    tx = None
    if watcher["protocol"] == "Autofarm":
        tx = contract.functions.earn(watcher["pid"]).build_transaction({
            "from": env["public_address"], "nonce": nonce,
            "gasPrice": w3.to_wei(gas_price, "gwei")
        })
    elif watcher["protocol"] == "QuickSwap":
        tx = contract.functions.deposit(watcher["pid"], 0).build_transaction({
            "from": env["public_address"], "nonce": nonce,
            "gasPrice": w3.to_wei(gas_price, "gwei")
        })
    elif watcher["protocol"] == "Balancer":
        tx = contract.functions.claimProtocolFees().build_transaction({
            "from": env["public_address"], "nonce": nonce,
            "gasPrice": w3.to_wei(gas_price, "gwei")
        })
    else:
        return False, 0, None
    tx["gas"] = w3.eth.estimate_gas(tx)
    try:
        pending = contract.functions.pendingReward(watcher.get("pid", 0), env["public_address"]).call()
        reward_usd = get_reward_usd(watcher["rewardToken"], pending / 1e18)
    except:
        reward_usd = 0
    gas_cost_usd = get_reward_usd("MATIC", w3.from_wei(tx["gas"] * w3.to_wei(gas_price, "gwei"), "ether"))
    if reward_usd < config["min_reward_usd"] or reward_usd < gas_cost_usd * config["min_profit_ratio"]:
        return False, 0, None
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=env["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return True, reward_usd, tx_hash.hex()

def send_oracle_update_tx(w3, job, env, config):
    contract = w3.eth.contract(address=Web3.to_checksum_address(job["contract_address"]),
                               abi=json.load(open(job["abi_file"])))
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={job['token'].lower()}&vs_currencies=usd"
    res = requests.get(url).json()
    price = res[job["token"].lower()]["usd"]
    nonce = w3.eth.get_transaction_count(env["public_address"])
    tx = contract.functions.updatePrice(int(price * 1e8)).build_transaction({
        "from": env["public_address"], "nonce": nonce,
        "gasPrice": w3.to_wei(config["max_gas_gwei"], "gwei")
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=env["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), price

def get_reward_usd(token_symbol, amount):
    try:
        res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={token_symbol.lower()}&vs_currencies=usd").json()
        return amount * res[token_symbol.lower()]["usd"]
    except:
        return 0
