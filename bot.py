import os
import json
import time
import logging
from web3 import Web3
from ai_agent import analyze_and_act
from rpc_manager import RPCManager
from telegram_notifier import send_alert
from summary_reporter import SummaryReporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bot")

# Load config.json
with open("config.json") as f:
    config = json.load(f)

# Setup Web3 RPC manager
rpc_manager = RPCManager()
w3 = Web3(Web3.HTTPProvider(rpc_manager.get_rpc()))

# Load watchers
with open("watchers.json") as f:
    watchers = json.load(f)

wallet_address = os.getenv("WALLET_ADDRESS")
private_key = os.getenv("PRIVATE_KEY")

if not wallet_address or not private_key:
    logger.error("Missing WALLET_ADDRESS or PRIVATE_KEY in environment.")
    exit(1)

reporter = SummaryReporter(config)

def main():
    logger.info("🚀 Oracle Bot started (production mode)")
    while True:
        for watcher in watchers:
            try:
                tx_hash = analyze_and_act(w3, watcher, wallet_address, private_key, config)
                if tx_hash:
                    send_alert(f"✅ Harvested {watcher['name']} tx: {tx_hash}")
                    reporter.log_success(watcher, tx_hash)
            except Exception as e:
                logger.error(f"Error in watcher {watcher['name']}: {e}")
                reporter.log_failure(watcher, str(e))
        time.sleep(60)

if __name__ == "__main__":
    main()
