# price_fetcher.py
import requests
import logging

logger = logging.getLogger("PriceFetcher")

# Correct CoinGecko IDs
SYMBOL_MAP = {
    "AUTO": "auto",
    "QUICK": "quick",
    "MATIC": "matic-network",  # corrected
    "USDC": "usd-coin",
    "DAI": "dai",
    "USDT": "tether",
    "ETH": "ethereum",
    "WBTC": "wrapped-bitcoin"
}

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

# Global cache for prices
_prices = {sym: 0.0 for sym in SYMBOL_MAP.keys()}

def fetch_prices(symbols=None):
    """Fetch current USD prices from CoinGecko."""
    global _prices
    symbols = symbols or SYMBOL_MAP.keys()
    ids = ",".join([SYMBOL_MAP[sym] for sym in symbols if sym in SYMBOL_MAP])
    params = {"ids": ids, "vs_currencies": "usd"}

    try:
        response = requests.get(COINGECKO_API, params=params, timeout=10)
        data = response.json()
        for sym in symbols:
            cg_id = SYMBOL_MAP.get(sym)
            if cg_id and cg_id in data:
                _prices[sym] = float(data[cg_id]["usd"])
            else:
                logger.warning(f"[PriceFetcher] Failed to fetch {sym}: '{cg_id}'")
        return _prices
    except requests.RequestException as e:
        logger.error(f"[PriceFetcher] Price fetch failed: {e}")
        return {sym: 0.0 for sym in symbols}

def get_price(symbol):
    """Return last fetched price (USD) for a symbol. Fetches if missing."""
    if _prices.get(symbol, 0.0) == 0.0:
        fetch_prices([symbol])
    return _prices.get(symbol, 0.0)

# Optional: continuously update prices if run directly
if __name__ == "__main__":
    import time
    while True:
        prices = fetch_prices()
        logger.info(f"[PriceFetcher] Current Prices: {prices}")
        time.sleep(30)  # fetch every 30 seconds
