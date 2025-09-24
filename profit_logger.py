import csv
import os
import time
from price_fetcher import get_price

LOG_FILE = "logs/profit_log.csv"

def log_profit(tx_hash, watcher, gas_gwei, public_address, contract):
    """
    Fetch real-time earned rewards from contract, calculate profit.
    Logs into CSV and returns profit in USD.
    """
    try:
        os.makedirs("logs", exist_ok=True)

        reward_token = watcher.get("rewardToken", "MATIC")

        # Fetch actual earned reward from contract
        earned = 0.0
        protocol = watcher.get("protocol")
        try:
            if protocol == "autofarm":
                pid = watcher.get("pid", 0)
                earned = contract.functions.pendingReward(pid, public_address).call()
            elif protocol == "balancer":
                earned = contract.functions.earned().call()
            elif protocol == "quickswap":
                if hasattr(contract.functions, "pendingReward"):
                    pid = watcher.get("pid", 0)
                    earned = contract.functions.pendingReward(pid, public_address).call()
                elif hasattr(contract.functions, "pendingTokens"):
                    pid = watcher.get("pid", 0)
                    earned = contract.functions.pendingTokens(pid, public_address).call()
        except Exception as e:
            print(f"[ProfitLogger] Could not fetch real-time reward: {e}")
            earned = watcher.get("rewardAmount", 0.0)

        # Convert to human-readable if needed
        reward_amount = earned / 10**18 if earned > 1e18 else earned

        # --- Prices ---
        token_price = get_price(reward_token)
        matic_price = get_price("MATIC")

        # --- Rewards & Costs ---
        reward_usd = reward_amount * token_price
        gas_cost_usd = (gas_gwei * 1e-9) * 210000 * matic_price  # rough estimate
        profit = reward_usd - gas_cost_usd

        # --- CSV logging ---
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(
                    ["timestamp", "protocol", "reward_token", "reward_amount", "profit_usd", "gas_cost_usd", "tx_hash"]
                )
            writer.writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    protocol,
                    reward_token,
                    f"{reward_amount:.6f}",
                    f"{profit:.4f}",
                    f"{gas_cost_usd:.4f}",
                    tx_hash,
                ]
            )

        print(
            f"[ProfitLogger] {protocol} profit: ${profit:.4f}, gas: ${gas_cost_usd:.4f}, tx: {tx_hash}"
        )

        return profit
    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
