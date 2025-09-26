# price_fetcher.py
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

class PriceFetcher:
    def __init__(self, symbols=None):
        self.symbols = symbols or SYMBOL_MAP.keys()
        self.prices = {sym: 0.0 for sym in self.symbols}

    def fetch_prices(self):
        ids = ",".join([SYMBOL_MAP[sym] for sym in self.symbols if sym in SYMBOL_MAP])
        params = {"ids": ids, "vs_currencies": "usd"}
        try:
            data = requests.get(COINGECKO_API, params=params, timeout=10).json()
            for sym in self.symbols:
                cg_id = SYMBOL_MAP.get(sym)
                if cg_id and cg_id in data:
                    self.prices[sym] = float(data[cg_id]["usd"])
                else:
                    logger.warning(f"Failed to fetch {sym}")
            return self.prices
        except Exception as e:
            logger.error(f"Price fetch failed: {e}")
            return {sym: 0.0 for sym in self.symbols}

    def get_price(self, symbol):
        return self.prices.get(symbol, 0.0)

# Global singleton
global_price_fetcher = PriceFetcher()
global_price_fetcher.fetch_prices()
