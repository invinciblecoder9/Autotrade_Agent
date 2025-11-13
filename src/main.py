# src/main.py
"""
Lightweight runner for the autonomous trading agent.
This file intentionally keeps imports inside run_cycle() to avoid
circular import issues when imported by test utilities.
"""

import time
import signal
from typing import List, Optional

# list of tickers to process
TICKERS: List[str] = ["BTCUSD", "ETHUSD"]


# graceful shutdown flag
_SHUTDOWN = False
def _handle_signal(signum, frame):
    global _SHUTDOWN
    _SHUTDOWN = True
    print("Received shutdown signal, stopping after current cycle...")


def _extract_price_from_provider(resp: Optional[dict]) -> Optional[float]:
    """
    Accepts the get_latest_price() response and tries to reliably return a float price
    or None if no usable price is found.
    Expected resp examples:
      {"provider":"yfinance","status":"success","symbol":"AAPL","last":{"price":123.45}}
    or {"provider":"alphavantage", ... , "last":{"price": 123.45}}
    """
    if not resp or not isinstance(resp, dict):
        return None
    last = resp.get("last") or {}
    # common keys
    for key in ("price", "last_price", "lastPrice", "last"):
        if isinstance(last, dict) and key in last:
            try:
                return float(last[key])
            except Exception:
                pass
    # some providers might put price at top-level under 'price'
    for key in ("price", "last_price", "last"):
        if key in resp:
            try:
                return float(resp[key])
            except Exception:
                pass
    return None


def run_cycle():
    """
    Single run cycle over all tickers. Imports agents lazily to avoid
    import-time side effects / circular imports.
    """
    # Lazy imports (keep module import-time cheap)
    from src.agents.news_agent import fetch_news
    from src.agents.sentiment_agent import score_article
    from src.agents.price_agent import get_latest_price
    from src.agents.decision_agent import decide
    from src.agents.execution_agent import place_order
    from src.agents.notifier_agent import notify_trade, notify_error

    for t in TICKERS:
        try:
            print(f"\n[{t}] Starting cycle...")
            # 1) fetch and analyze news
            try:
                news = fetch_news(t, max_results=5) or []
            except Exception as e:
                news = []
                print(f"[{t}] Warning: fetch_news failed: {e}")
                # log / notify if desired
            scores = []
            for n in news:
                try:
                    text = (n.get("title") or "") + " " + (n.get("body") or "")
                    sc = score_article(text)
                    scores.append(sc.get("compound", 0.0))
                except Exception as e:
                    print(f"[{t}] warning scoring article: {e}")
            agg = sum(scores) / len(scores) if scores else 0.0
            print(f"[{t}] agg_sentiment={agg:.3f} (news_count={len(scores)})")

            # 2) Get latest price (use provider wrapper)
            last_price = None
            try:
                price_resp = get_latest_price(t)
                last_price = _extract_price_from_provider(price_resp)
            except Exception as e:
                print(f"[{t}] Warning: get_latest_price failed: {e}")
            print(f"[{t}] last_price={last_price}")

            # 3) Decision
            # portfolio_cash = 10000.0
            # current_qty = 0
            # decision = decide(agg, last_price or 0.0, portfolio_cash, current_qty)
            from src.utils.db_utils_sqlite import get_account_balance, get_position
            portfolio_cash = get_account_balance("USD")
            pos = get_position(t)
            current_qty = float(pos["qty"]) if pos and pos.get("qty") else 0.0
            decision = decide(agg, last_price or 0.0, portfolio_cash, current_qty)

            print(f"[{t}] decision={decision}")

            # 4) Execute and notify
            if decision.get("action") == "buy" and decision.get("qty", 0) > 0:
                resp = place_order(symbol=t, side="buy", amount=decision["qty"], price=None)
                try:
                    notify_trade(t, "buy", decision["qty"], last_price or 0.0)
                except Exception as e:
                    print(f"[{t}] notify_trade failed: {e}")
                print(f"[{t}] BUY executed: resp={resp}")
            elif decision.get("action") == "sell" and decision.get("qty", 0) > 0:
                resp = place_order(symbol=t, side="sell", amount=decision["qty"], price=None)
                try:
                    notify_trade(t, "sell", decision["qty"], last_price or 0.0)
                except Exception as e:
                    print(f"[{t}] notify_trade failed: {e}")
                print(f"[{t}] SELL executed: resp={resp}")
            else:
                print(f"[{t}] No trade (hold).")

        except Exception as e:
            # Notify and continue with next ticker
            try:
                notify_error(str(e))
            except Exception:
                print(f"[{t}] Failed to send error notification: {e}")
            print(f"[{t}] Exception in cycle: {e}")


if __name__ == "__main__":
    # Initialize signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Initialize DB lazily here so importing src.main in tests doesn't auto-create things
    try:
        from src.utils.db_init_sqlite import init_db
        init_db()
    except Exception as e:
        print("Warning: init_db() failed or not available:", e)

    print("🚀 Autonomous Trading Agent Started (Telegram notifications enabled)")
    try:
        while not _SHUTDOWN:
            run_cycle()
            # sleep in small increments so shutdown is responsive
            for _ in range(15):  # 15 * 60s = 15 minutes
                if _SHUTDOWN:
                    break
                time.sleep(60)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, shutting down.")
    print("Agent stopped.")
