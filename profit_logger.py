from web3 import Web3

def log_profit(tx_hash, watcher, gas_gwei, public_address, contract):
    """
    Calculates estimated profit from a harvest transaction.
    Handles contracts with pendingReward() with or without inputs.
    Returns USD value or 0 if cannot calculate.
    """
    reward_token = watcher.get("rewardToken", None)
    pid = watcher.get("pid", None)

    try:
        # Detect pendingReward function
        method_candidates = [f for f in dir(contract.functions) if f.lower().startswith("pendingreward")]
        if not method_candidates:
            print(f"[ProfitLogger] No pendingReward function for {watcher['name']}")
            return 0.0

        method_name = method_candidates[0]
        func = getattr(contract.functions, method_name)

        # Determine if function requires pid/address
        inputs = func.abi.get("inputs", [])
        if len(inputs) == 0:
            pending = func().call()
        elif len(inputs) == 1 and pid is not None:
            pending = func(pid).call()
        else:
            print(f"[ProfitLogger] Unsupported pendingReward signature for {watcher['name']}")
            return 0.0

        # Convert raw token amount to human-readable (assume 18 decimals)
        amount = Web3.from_wei(pending, 'ether')

        # Rough USD conversion placeholder (replace with actual price feed if available)
        price_usd = 1.0  # Default placeholder; integrate with price fetcher if you want real USD
        profit_usd = float(amount) * price_usd

        print(f"[ProfitLogger] Estimated profit for {watcher['name']}: ${profit_usd:.2f}")
        return profit_usd

    except Exception as e:
        print(f"[ProfitLogger] Error: Could not transact with/call contract function, {e}")
        return 0.0
