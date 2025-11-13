# tests/force_trade.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))  # ensure imports resolve
from src.agents.execution_agent import place_order
from src.agents.notifier_agent import notify_trade
print("Forcing mock BUY for demo...")
resp = place_order("BTCUSD", "buy", 0.001, price=None)
print("Execution resp:", resp)
try:
    price = float(resp.get("price") or 0.0)
except Exception:
    price = 0.0
notify_trade("BTCUSD", "buy", 0.001, price)
print("Done — check dashboard and Telegram.")
