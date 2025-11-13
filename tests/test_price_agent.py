# tests/test_price_agent.py
import os, sys
from dotenv import load_dotenv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from src.agents.price_agent import get_latest_price, get_intraday_bars

print("Getting latest price (AlphaVantage primary)...")
resp = get_latest_price("AAPL")
print("Response:", resp)
if resp and resp.get("last"):
    print("Last price:", resp["last"].get("price"))

print("\nFetching 5min intraday bars (AlphaVantage TIME_SERIES_INTRADAY)...")
try:
    bars = get_intraday_bars("AAPL", interval="5min", outputsize="compact")
    print("Intraday keys sample:", list(bars.keys())[:3])
except Exception as e:
    print("Intraday fetch failed (likely rate limit or no key):", e)
