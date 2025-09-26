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
    """
    Fetch USD price for a token symbol via CoinGecko.
    Caches last successful fetch.
    """
    global _prices_cache
    symbol = symbol.upper()
    if symbol not in SYMBOL_MAP:
        return 0.0
    try:
        cg_id = SYMBOL_MAP[symbol]
        response = requests.get(COINGECKO_API, params={"ids": cg_id, "vs_currencies": "usd"}, timeout=10)
        data = response.json()
        price = float(data[cg_id]["usd"])
        _prices_cache[symbol] = price
        return price
    except Exception as e:
        logger.warning(f"[PriceFetcher] Failed to fetch {symbol}: {e}")
        return _prices_cache.get(symbol, 0.0)
