import csv
import os
import time
from price_fetcher import get_price

LOG_FILE = "logs/profit_log.csv"

def log_profit(tx_hash, watcher, gas_gwei, web3=None, contract=None):
    """
    Calculate profit using real-time reward from contract.
    Supports Autofarm, Balancer, Quickswap.
    """
    try:
        os.makedirs("logs", exist_ok=True)

        protocol = watcher.get("protocol", "").lower()
        reward_token = watcher.get("rewardToken", "MATIC")
        reward_amount = 0.0

        # Fetch actual earned reward from contract
        if contract and web3:
            try:
                if protocol == "autofarm":
                    pid = watcher.get("pid", 0)
                    reward_amount = contract.functions.pendingReward(pid, watcher.get("address")).call()
                elif protocol == "balancer":
                    reward_amount = contract.functions.earned().call()
                elif protocol == "quickswap":
                    pid = watcher.get("pid", 0)
                    reward_amount = contract.functions.pendingReward(pid, watcher.get("address")).call()
                reward_amount = web3.from_wei(reward_amount, 'ether')
            except Exception as e:
                print(f"[ProfitLogger] Could not fetch real reward, using static rewardAmount: {e}")
                reward_amount = watcher.get("rewardAmount", 0.0)
        else:
            reward_amount = watcher.get("rewardAmount", 0.0)

        # Prices
        token_price = get_price(reward_token)
        matic_price = get_price("MATIC")

        # Profit calculation
        reward_usd = reward_amount * token_price
        gas_cost_usd = (gas_gwei * 1e-9) * 210000 * matic_price  # fallback 210k gas
        profit = reward_usd - gas_cost_usd

        # CSV logging
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(
                    ["timestamp", "protocol", "reward_amount", "profit_usd", "gas_cost_usd", "tx_hash"]
                )
            writer.writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    protocol,
                    f"{reward_amount:.6f}",
                    f"{profit:.4f}",
                    f"{gas_cost_usd:.4f}",
                    tx_hash,
                ]
            )

        print(
            f"[ProfitLogger] {protocol} profit: ${profit:.4f}, reward: {reward_amount:.6f} {reward_token}, gas: ${gas_cost_usd:.4f}, tx: {tx_hash}"
        )

        return profit

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
