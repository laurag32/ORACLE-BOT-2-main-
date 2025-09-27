# price_fetcher.py
import requests
import logging
import time
from threading import Lock

logger = logging.getLogger("PriceFetcher")
logging.basicConfig(level=logging.INFO)

SYMBOL_MAP = {
    "AUTO": "auto",
    "QUICK": "quick",
    "MATIC": "matic-network",
    "USDC": "usd-coin",
    "DAI": "dai",
    "USDT": "tether",
    "ETH": "ethereum",
    "WBTC": "wrapped-bitcoin"
}

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

_prices = {sym: 0.0 for sym in SYMBOL_MAP.keys()}
_last_fetch_time = 0
_CACHE_DURATION = 30
_lock = Lock()


def fetch_prices(symbols=None):
    global _prices, _last_fetch_time
    symbols = symbols or SYMBOL_MAP.keys()

    with _lock:
        now = time.time()
        if now - _last_fetch_time < _CACHE_DURATION:
            return {sym: _prices.get(sym, 0.0) for sym in symbols}

        ids = ",".join([SYMBOL_MAP[sym] for sym in symbols if sym in SYMBOL_MAP])
        params = {"ids": ids, "vs_currencies": "usd"}

        for attempt in range(3):
            try:
                response = requests.get(COINGECKO_API, params=params, timeout=10)
                data = response.json()
                for sym in symbols:
                    cg_id = SYMBOL_MAP.get(sym)
                    if cg_id and cg_id in data and "usd" in data[cg_id]:
                        _prices[sym] = float(data[cg_id]["usd"])
                    else:
                        logger.warning(f"[PriceFetcher] Failed to fetch {sym}: '{cg_id}'")
                _last_fetch_time = time.time()
                return {sym: _prices.get(sym, 0.0) for sym in symbols}
            except requests.RequestException as e:
                logger.warning(f"[PriceFetcher] Fetch attempt {attempt+1} failed: {e}")
                time.sleep(1 + attempt)

        logger.error("[PriceFetcher] All fetch attempts failed, returning cached prices or 0.0")
        return {sym: _prices.get(sym, 0.0) for sym in symbols}


def get_price(symbol):
    prices = fetch_prices([symbol])
    return prices.get(symbol, 0.0)


if __name__ == "__main__":
    while True:
        prices = fetch_prices()
        logger.info(f"[PriceFetcher] Current Prices: {prices}")
        time.sleep(_CACHE_DURATION)
