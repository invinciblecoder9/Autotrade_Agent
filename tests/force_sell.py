# tests/force_sell.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.agents.execution_agent import place_order
from src.utils.db_utils_sqlite import get_position, fetch_trades

# find a position to sell
pos = get_position("BTCUSD")
if not pos or pos["qty"] == 0:
    print("No holdings to sell. Run a buy first.")
else:
    qty = min(0.001, pos["qty"])
    resp = place_order("BTCUSD", "sell", qty, price=None)
    print("Sell resp:", resp)
