import logging
import os
from decimal import Decimal

logger = logging.getLogger("ProfitLogger")

MIN_PROFIT_RATIO = float(os.getenv("MIN_PROFIT_RATIO", 1.10))

def is_profitable(reward_usd: float, gas_usd: float) -> bool:
    """Check if reward / gas >= min profit ratio"""
    if gas_usd <= 0:
        return True
    ratio = Decimal(reward_usd) / Decimal(gas_usd)
    logger.info(f"[ProfitCheck] reward={reward_usd:.4f} gas={gas_usd:.4f} ratio={ratio:.2f} min={MIN_PROFIT_RATIO}")
    return ratio >= Decimal(MIN_PROFIT_RATIO)

def log_profit(watcher, reward_usd, gas_usd, tx_hash):
    if is_profitable(reward_usd, gas_usd):
        logger.info(f"[ProfitLogger] ✅ {watcher['name']} profit={reward_usd - gas_usd:.4f} USD tx={tx_hash}")
    else:
        logger.info(f"[ProfitLogger] ❌ {watcher['name']} skipped: reward={reward_usd:.4f}, gas={gas_usd:.4f}")
