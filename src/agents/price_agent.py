# # src/agents/price_agent.py
# """
# AlphaVantage primary price provider with yfinance fallback.
# Provides:
#  - get_latest_price(ticker) -> {'provider','status','symbol','last':{'price': float}}
#  - get_intraday_bars(ticker, interval='5min', outputsize='compact') -> dict (time-series)
# Notes: AlphaVantage free tier = 5 requests/minute and 500/day by default.
# """

# import os
# import requests
# from typing import Optional, Dict
# from src.utils.config import ALPHAVANTAGE_KEY
# _modname = __name__  # safe, works when module loaded as top-level or package

# ALPHA_BASE = "https://www.alphavantage.co/query"

# def _alphavantage_global_quote(ticker: str) -> Dict:
#     if not ALPHAVANTAGE_KEY:
#         raise RuntimeError("ALPHAVANTAGE_KEY not set in environment")
#     params = {
#         "function": "GLOBAL_QUOTE",
#         "symbol": ticker,
#         "apikey": ALPHAVANTAGE_KEY
#     }
#     r = requests.get(ALPHA_BASE, params=params, timeout=15)
#     r.raise_for_status()
#     j = r.json()
#     # Expected structure: { "Global Quote": { "01. symbol":"AAPL", "05. price":"123.45", ... } }
#     if "Global Quote" in j and j["Global Quote"]:
#         g = j["Global Quote"]
#         price_str = g.get("05. price") or g.get("05. Price") or None
#         if price_str:
#             try:
#                 price = float(price_str)
#             except Exception:
#                 raise RuntimeError(f"AlphaVantage returned non-numeric price: {price_str}")
#             return {"provider": "alphavantage", "status": "success", "symbol": ticker, "last": {"price": price}}
#     # AlphaVantage sometimes returns an object with note or error message
#     raise RuntimeError(f"AlphaVantage returned no quote for {ticker}: {j}")

# def get_intraday_bars(ticker: str, interval: str = "5min", outputsize: str = "compact") -> Dict:
#     """
#     Get intraday bars from AlphaVantage.
#     interval: '1min','5min','15min','30min','60min'
#     outputsize: 'compact' (latest 100 points) or 'full' (full-length)
#     Returns the raw JSON from AlphaVantage (you must parse timestamps).
#     """
#     if not ALPHAVANTAGE_KEY:
#         raise RuntimeError("ALPHAVANTAGE_KEY not set in environment")
#     params = {
#         "function": "TIME_SERIES_INTRADAY",
#         "symbol": ticker,
#         "interval": interval,
#         "outputsize": outputsize,
#         "datatype": "json",
#         "apikey": ALPHAVANTAGE_KEY
#     }
#     r = requests.get(ALPHA_BASE, params=params, timeout=20)
#     r.raise_for_status()
#     j = r.json()
#     if "Error Message" in j:
#         raise RuntimeError(f"AlphaVantage error for {ticker}: {j['Error Message']}")
#     if "Note" in j:
#         # Rate limit / service message
#         raise RuntimeError(f"AlphaVantage note: {j['Note']}")
#     return j

# # yfinance fallback (no key)
# def _yfinance_last(ticker: str) -> Dict:
#     try:
#         import yfinance as yf
#     except Exception as e:
#         raise RuntimeError("yfinance not installed") from e
#     tk = ticker
#     t = yf.Ticker(tk)
#     # Try fast_info, then history, then info
#     try:
#         if hasattr(t, "fast_info") and t.fast_info and t.fast_info.get("last_price") is not None:
#             last_price = t.fast_info["last_price"]
#         else:
#             hist = t.history(period="1d", interval="1m")
#             if hist is None or hist.empty:
#                 last_price = t.info.get("regularMarketPrice") or t.info.get("previousClose")
#             else:
#                 last_price = hist["Close"].iloc[-1]
#         return {"provider": "yfinance", "status": "success", "symbol": ticker, "last": {"price": float(last_price)}}
#     except Exception as e:
#         raise RuntimeError(f"yfinance failed for {ticker}: {e}") from e

# def get_latest_price(ticker: str) -> Dict:
#     """
#     Primary: AlphaVantage (GLOBAL_QUOTE). If that fails due to missing key or rate-limit/permission, fallback to yfinance.
#     """
#     # 1) Try AlphaVantage
#     if ALPHAVANTAGE_KEY:
#         try:
#             return _alphavantage_global_quote(ticker)
#         except Exception as e:
#             # If the error reflects rate-limit / note / missing data, fallback to yfinance
#             msg = str(e).lower()
#             if "note" in msg or "rate" in msg or "no quote" in msg or "alpha vantage" in msg or "returned no quote" in msg:
#                 # fall through to yfinance fallback
#                 pass
#             else:
#                 # For unexpected errors, still fallback but include message
#                 pass
#     # 2) Fallback: yfinance
#     return _yfinance_last(ticker)


# src/agents/price_agent.py
"""
Robust price provider with multiple fallbacks:
  1) AlphaVantage (if key present and symbol looks like equity)
  2) yfinance (for equities and crypto using symbol mapping)
  3) CoinGecko (public, reliable for crypto)
  4) (Optional) Polygon — left as placeholder

Returns a dict:
  {"provider": "yfinance"|"alphavantage"|"coingecko"|"polygon", "status":"success"|"error", "symbol": ticker, "last": {"price": float}}
"""

import os
import requests
from typing import Dict, Optional

# config
try:
    from src.utils.config import ALPHAVANTAGE_KEY, POLYGON_KEY
except Exception:
    # fallback if config missing
    ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY")
    POLYGON_KEY = os.getenv("POLYGON_KEY")

# small mapping for crypto tickers to CoinGecko ids and yfinance tickers
_CRYPTO_MAP = {
    "BTCUSD": {"coingecko": "bitcoin", "yfinance": "BTC-USD"},
    "ETHUSD": {"coingecko": "ethereum", "yfinance": "ETH-USD"},
    "LTCUSD": {"coingecko": "litecoin", "yfinance": "LTC-USD"},
    # add more if you need
}

ALPHA_BASE = "https://www.alphavantage.co/query"
COINGECKO_SIMPLE = "https://api.coingecko.com/api/v3/simple/price"


def _is_crypto_symbol(ticker: str) -> bool:
    return ticker.upper() in _CRYPTO_MAP


def _alphavantage_global_quote(ticker: str) -> Dict:
    """
    Try AlphaVantage GLOBAL_QUOTE (for equities). For cryptos AlphaVantage support is limited,
    so we avoid it for tickers in _CRYPTO_MAP.
    """
    if not ALPHAVANTAGE_KEY:
        raise RuntimeError("ALPHAVANTAGE_KEY not set")
    params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": ALPHAVANTAGE_KEY}
    resp = requests.get(ALPHA_BASE, params=params, timeout=15)
    resp.raise_for_status()
    j = resp.json()
    if "Global Quote" in j and j["Global Quote"]:
        g = j["Global Quote"]
        price_str = g.get("05. price") or g.get("05. Price") or None
        if price_str:
            return {"provider": "alphavantage", "status": "success", "symbol": ticker, "last": {"price": float(price_str)}}
    raise RuntimeError(f"AlphaVantage returned no quote for {ticker}: {j}")


def _yfinance_last(ticker: str) -> Dict:
    """
    Use yfinance. For crypto, convert BTCUSD -> BTC-USD etc using mapping.
    """
    try:
        import yfinance as yf
    except Exception as e:
        raise RuntimeError("yfinance not installed") from e

    tk = ticker
    if _is_crypto_symbol(ticker):
        tk = _CRYPTO_MAP[ticker.upper()]["yfinance"]

    t = yf.Ticker(tk)
    # try fast_info, then history, then info
    try:
        if hasattr(t, "fast_info") and t.fast_info and t.fast_info.get("last_price") is not None:
            last_price = t.fast_info["last_price"]
        else:
            hist = t.history(period="1d", interval="1m")
            if hist is None or hist.empty:
                # try market price in info
                last_price = t.info.get("regularMarketPrice") or t.info.get("previousClose")
            else:
                last_price = hist["Close"].iloc[-1]
        return {"provider": "yfinance", "status": "success", "symbol": ticker, "last": {"price": float(last_price)}}
    except Exception as e:
        raise RuntimeError(f"yfinance failed for {ticker}: {e}") from e


def _coingecko_price(ticker: str) -> Dict:
    """
    Use CoinGecko simple price endpoint for crypto tickers.
    """
    if not _is_crypto_symbol(ticker):
        raise RuntimeError("CoinGecko path only for crypto symbols")
    cg_id = _CRYPTO_MAP[ticker.upper()]["coingecko"]
    params = {"ids": cg_id, "vs_currencies": "usd"}
    resp = requests.get(COINGECKO_SIMPLE, params=params, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    if cg_id in j and "usd" in j[cg_id]:
        return {"provider": "coingecko", "status": "success", "symbol": ticker, "last": {"price": float(j[cg_id]["usd"])}}
    raise RuntimeError(f"CoinGecko returned no price for {ticker}: {j}")


def get_latest_price(ticker: str) -> Dict:
    """
    Try multiple providers and return the first successful price result.
    Order:
      - If crypto ticker (BTCUSD/ETHUSD): try yfinance -> coingecko
      - If non-crypto: try AlphaVantage (if key) -> yfinance
    """
    t = (ticker or "").upper().strip()
    # 1) crypto path
    if _is_crypto_symbol(t):
        # prefer yfinance if installed (gives minute-level), else coingecko
        try:
            return _yfinance_last(t)
        except Exception as e:
            # fall back to coingecko
            try:
                return _coingecko_price(t)
            except Exception as e2:
                raise RuntimeError(f"Crypto price lookups failed for {t}: yfinance error: {e}; coingecko error: {e2}")
    else:
        # equity / forex path
        # try AlphaVantage first if key present
        if ALPHAVANTAGE_KEY:
            try:
                return _alphavantage_global_quote(t)
            except Exception:
                # fallthrough to yfinance
                pass
        # fallback to yfinance
        try:
            return _yfinance_last(t)
        except Exception as e:
            raise RuntimeError(f"No price found for {t}: {e}")

