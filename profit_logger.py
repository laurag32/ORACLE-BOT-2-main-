import csv
import os
import time
from web3 import Web3
from price_fetcher import get_price

LOG_FILE = "logs/profit_log.csv"

def log_profit(tx_hash, protocol, gas_gwei, reward_token="MATIC", reward_amount=0.0, w3: Web3=None):
    """
    Calculate profit using actual gas from tx receipt, log into CSV, and return profit in USD.
    """
    try:
        os.makedirs("logs", exist_ok=True)

        # --- Prices ---
        token_price = get_price(reward_token)
        matic_price = get_price("MATIC")

        # --- Get actual gas used ---
        gas_cost_usd = 0.0
        if w3 is not None:
            try:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                gas_used = receipt.gasUsed
                gas_price_wei = receipt.effectiveGasPrice
                gas_cost_usd = (gas_used * gas_price_wei * 1e-18) * matic_price
            except Exception as e:
                print(f"[ProfitLogger] ⚠️ Could not fetch gas used, fallback estimate: {e}")
                gas_cost_usd = (gas_gwei * 1e-9) * 210000 * matic_price  # fallback estimate
        else:
            gas_cost_usd = (gas_gwei * 1e-9) * 210000 * matic_price  # fallback if w3 not passed

        # --- Rewards & Profit ---
        reward_usd = reward_amount * token_price
        profit = reward_usd - gas_cost_usd

        # --- CSV logging ---
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "protocol", "profit_usd", "gas_cost_usd", "tx_hash"])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                protocol,
                f"{profit:.4f}",
                f"{gas_cost_usd:.4f}",
                tx_hash
            ])

        print(f"[ProfitLogger] {protocol} profit: ${profit:.4f}, gas: ${gas_cost_usd:.4f}, tx: {tx_hash}")
        return profit

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0


# -------------------------
# Helper: get pending rewards
# -------------------------
def get_pending_rewards(contract, watcher, user_address):
    """
    Query contract for pending rewards based on protocol.
    """
    try:
        protocol = watcher["protocol"]

        if protocol == "autofarm":
            return contract.functions.pendingAUTO(watcher["pid"], user_address).call()

        elif protocol == "balancer":
            return contract.functions.getPendingRewards(user_address).call()

        elif protocol == "quickswap":
            return contract.functions.pendingQUICK(watcher["pid"], user_address).call()

        else:
            return 0.0

    except Exception as e:
        print(f"[ProfitLogger] Error fetching pending rewards for {protocol}: {e}")
        return 0.0
