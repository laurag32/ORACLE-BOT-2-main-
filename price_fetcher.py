import requests
import logging

logger = logging.getLogger("PriceFetcher")

SYMBOL_MAP = {
    "AUTO": "auto",
    "QUICK": "quick",
    "MATIC": "polygon-ecosystem-token",
    "USDC": "usd-coin",
    "DAI": "dai",
    "USDT": "tether",
    "ETH": "ethereum",
    "WBTC": "wrapped-bitcoin"
}

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

_prices_cache = {}

def get_price(symbol: str) -> float:
    global _prices_cache
    symbol = symbol.upper()
    if symbol not in SYMBOL_MAP:
        return 0.0
    try:
        cg_id = SYMBOL_MAP[symbol]
        response = requests.get(COINGECKO_API, params={"ids": cg_id, "vs_currencies": "usd"}, timeout=10)
        data = response.json()
        _prices_cache[symbol] = float(data[cg_id]["usd"])
        return _prices_cache[symbol]
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
        return _prices_cache.get(symbol, 0.0)
