def log_profit(tx_hash, watcher, gas_gwei, public_address, contract):
    """
    Reads real-time earned rewards from contracts and logs USD profit.
    Autofarm: pendingReward(pid, address)
    Balancer: earned()
    Quickswap: pendingReward or pendingTokens depending on farm
    """
    try:
        method_candidates = ["pendingReward", "earned", "pendingTokens"]
        func = None
        for name in method_candidates:
            if hasattr(contract.functions, name):
                func = getattr(contract.functions, name)
                break
        if func is None:
            print(f"[ProfitLogger] Could not find reward function for {watcher['protocol']}")
            return 0.0

        # Build call
        sig = func._function_signature() if hasattr(func, "_function_signature") else None
        if watcher.get("pid") and watcher.get("address"):
            args = [watcher["pid"], public_address]
        elif watcher.get("pid"):
            args = [watcher["pid"]]
        else:
            args = []

        earned_amount = func(*args).call()
        # convert to USD via watcher.price if available
        usd_value = earned_amount * watcher.get("price", 0)
        print(f"[ProfitLogger] Earned: {earned_amount}, USD: {usd_value:.2f}")
        return usd_value

    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
