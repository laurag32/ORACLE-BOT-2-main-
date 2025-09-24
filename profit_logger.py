def log_profit(tx_hash, watcher, gas_price, public_address, contract):
    try:
        protocol = watcher["protocol"]
        earned = 0

        if protocol == "autofarm":
            # Autofarm: call pendingReward(pid, address) or fallback
            func_name = "pendingReward"
            func = getattr(contract.functions, func_name, None)
            if func:
                try:
                    earned = func(watcher.get("pid", 0), public_address).call()
                except:
                    earned = func().call()
        elif protocol == "quickswap":
            func_name = "pendingReward"
            func = getattr(contract.functions, func_name, None)
            if func:
                try:
                    earned = func(watcher.get("pid", 0), public_address).call()
                except:
                    earned = func().call()

        profit_usd = earned / 1e18  # assuming token decimals 18
        return profit_usd
    except Exception as e:
        print(f"[ProfitLogger] Error: {e}")
        return 0.0
