import requests
import time

price_cache = {}
CACHE_TTL = 60  # seconds
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

SYMBOL_MAP = {
    "AUTO": "auto",
    "BAL": "balancer",
    "QUICK": "quick",
    "MATIC": "matic-network",
    "USDC": "usd-coin",
    "DAI": "dai",
    "USDT": "tether"
}

def get_price(symbol: str) -> float:
    now = time.time()
    symbol = symbol.upper()

    if symbol not in SYMBOL_MAP:
        raise ValueError(f"Token {symbol} not supported in SYMBOL_MAP")

    if symbol in price_cache and now - price_cache[symbol]["ts"] < CACHE_TTL:
        return price_cache[symbol]["price"]

    try:
        resp = requests.get(COINGECKO_API, params={
            "ids": SYMBOL_MAP[symbol],
            "vs_currencies": "usd"
        }, timeout=10)
        data = resp.json()
        usd_price = data[SYMBOL_MAP[symbol]]["usd"]

        price_cache[symbol] = {"price": usd_price, "ts": now}
        return usd_price

    except Exception as e:
        print(f"[PriceFetcher] Failed to fetch {symbol}: {e}")
        if symbol in price_cache:
            return price_cache[symbol]["price"]
        return 0.0
