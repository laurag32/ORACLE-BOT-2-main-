import requests

def get_token_price(token_symbol: str):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_symbol}&vs_currencies=usd"
        resp = requests.get(url).json()
        return resp.get(token_symbol, {}).get("usd", 0)
    except Exception as e:
        print(f"[PriceFetcher] Failed to fetch {token_symbol} price: {e}")
        return 0
