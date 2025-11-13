# src/agents/decision_agent.py
from typing import Dict

# Simple rule parameters (tune as needed)
BUY_THRESHOLD = 0.20    # agg sentiment above this -> buy
SELL_THRESHOLD = -0.20  # agg sentiment below this -> sell
POSITION_FRACTION = 0.001  # fraction of capital to use per buy (0.001 -> 0.1%)

def decide(agg_sentiment: float, last_price: float, portfolio_cash: float, current_qty: float) -> Dict:
    """
    Returns a decision dict: {"action":"buy"/"sell"/"hold", "qty": <float>}
    - qty is asset units (not USD)
    - portfolio_cash: available cash in USD (virtual)
    - current_qty: current holding quantity (asset units)
    """
    # default
    action = "hold"
    qty = 0.0

    # If we have no price information, hold
    if last_price is None or last_price <= 0:
        return {"action": "hold", "qty": 0.0, "reason": "no_price"}

    # If sentiment strongly positive and we have cash, buy a small fraction
    if agg_sentiment >= BUY_THRESHOLD:
        usd_to_use = portfolio_cash * POSITION_FRACTION
        qty = usd_to_use / last_price
        if qty > 0:
            action = "buy"
            return {"action": action, "qty": round(qty, 8), "reason": f"agg_sentiment={agg_sentiment}"}

    # If sentiment strongly negative and we have position, sell some or all
    if agg_sentiment <= SELL_THRESHOLD and current_qty > 0:
        # Sell a fraction of holdings (e.g., 50%)
        sell_frac = 0.5
        qty = current_qty * sell_frac
        action = "sell"
        return {"action": action, "qty": round(qty, 8), "reason": f"agg_sentiment={agg_sentiment}"}

    return {"action": "hold", "qty": 0.0, "reason": "no_signal"}
