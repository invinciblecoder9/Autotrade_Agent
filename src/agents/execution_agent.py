# # # src/agents/execution_agent.py
# # """
# # Execution agent: places orders either in MOCK mode or via Gemini sandbox.
# # Provides:
# #   - place_order(symbol, side, amount, price=None) -> Dict[str, Any]
# # The function persists trades/events to the DB via src.utils.db_utils_sqlite helpers.
# # """

# import os
# import time
# import json
# import hmac
# import base64
# import hashlib
# import requests
# from typing import Optional, Dict, Any

# # config (ensure src is in sys.path or run from project root with -m)
# from src.utils.config import GEMINI_API_KEY, GEMINI_API_SECRET, MOCK_EXECUTION

# # Gemini sandbox base URL
# GEMINI_SANDBOX_BASE = "https://api.sandbox.gemini.com"
# GEMINI_BASE = os.getenv("GEMINI_BASE_URL", GEMINI_SANDBOX_BASE)


# def _call_gemini_api_mock(payload: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Return a plausible mock response for testing / sandbox mode.
#     """
#     # Simulate a slight delay
#     time.sleep(0.1)
#     ts = int(time.time() * 1000)
#     # Create a fake response similar to what Gemini returns
#     resp = {
#         "order_id": f"mock-{ts}",
#         "client_order_id": f"mock_client_{ts}",
#         "symbol": payload.get("symbol"),
#         "amount": payload.get("amount"),
#         "side": payload.get("side"),
#         "type": payload.get("type"),
#         "price": payload.get("price", None),
#         "status": "filled",
#         "filled_size": payload.get("amount"),
#         "avg_execution_price": payload.get("price") or 0.0,
#         "created_at": ts,
#         "raw_payload": payload,
#     }
#     return resp


# def _call_gemini_api(payload: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Call Gemini v1 new order endpoint with HMAC signing.
#     NOTE: This is a minimal implementation for sandbox/testing.
#     Make sure GEMINI_API_KEY and GEMINI_API_SECRET are set (sandbox keys).
#     """
#     if not GEMINI_API_KEY or not GEMINI_API_SECRET:
#         raise RuntimeError("Gemini API key/secret not configured (GEMINI_API_KEY / GEMINI_API_SECRET).")

#     # Build payload as required by Gemini v1
#     payload["request"] = "/v1/order/new"
#     payload["nonce"] = str(int(time.time() * 1000))

#     # Encode payload and sign
#     j = json.dumps(payload)
#     b64 = base64.b64encode(j.encode())
#     signature = hmac.new(GEMINI_API_SECRET.encode(), b64, hashlib.sha384).hexdigest()

#     headers = {
#         "Content-Type": "application/json",
#         "X-GEMINI-APIKEY": GEMINI_API_KEY,
#         "X-GEMINI-PAYLOAD": b64.decode(),
#         "X-GEMINI-SIGNATURE": signature,
#     }

#     url = GEMINI_BASE + "/v1/order/new"
#     r = requests.post(url, headers=headers, timeout=15)
#     # will raise requests.HTTPError for 4xx/5xx
#     r.raise_for_status()
#     return r.json()


# def _safe_get_order_id(resp: Dict[str, Any]) -> Optional[str]:
#     """
#     Safely extract an order id from the response.
#     """
#     for k in ("order_id", "id", "client_order_id", "exec_id"):
#         if isinstance(resp, dict) and k in resp and resp.get(k):
#             return str(resp.get(k))
#     # try nested structures
#     if isinstance(resp, dict):
#         for v in resp.values():
#             if isinstance(v, dict) and "order_id" in v:
#                 return str(v.get("order_id"))
#     return None


# def _safe_get_price(resp: Dict[str, Any]) -> Optional[float]:
#     """
#     Safely extract a price/fill price from the response.
#     """
#     if not isinstance(resp, dict):
#         return None
#     # Common Gemini fields
#     for k in ("avg_execution_price", "price", "filled_avg_price", "execution_price"):
#         if k in resp and resp.get(k) is not None:
#             try:
#                 return float(resp.get(k))
#             except Exception:
#                 continue
#     # filled price can be computed from 'filled_size'/'amount' fields in some mocks
#     try:
#         if "avg_execution_price" in resp and resp.get("avg_execution_price") is not None:
#             return float(resp["avg_execution_price"])
#     except Exception:
#         pass
#     return None


# # def place_order(symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
# #     """
# #     Place an order via Gemini sandbox (or mock).
# #     This version updates portfolio and computes realized pnl when SELL closes a position.
# #     Returns the raw API response or an error dict: {"error": True, "message": "..."}
# #     """
# #     # import DB helpers here to avoid circular imports at module import time
# #     try:
# #         from src.utils.db_utils_sqlite import (
# #             insert_trade,
# #             insert_event,
# #             upsert_position,
# #             get_position,
# #             update_trade_pnl,
# #         )
# #     except Exception:
# #         # If DB utilities are missing, proceed but record events to stdout
# #         insert_trade = insert_event = upsert_position = get_position = update_trade_pnl = None

# #     # Build the payload
# #     payload: Dict[str, Any] = {
# #         "symbol": symbol,
# #         "amount": str(amount),
# #         "side": side,
# #         "type": "exchange limit" if price is not None else "exchange market",
# #     }
# #     if price is not None:
# #         payload["price"] = str(price)

# #     # Call API (mock or real)
# #     try:
# #         if MOCK_EXECUTION:
# #             resp = _call_gemini_api_mock(payload)
# #         else:
# #             resp = _call_gemini_api(payload)
# #     except requests.HTTPError as e:
# #         err_text = f"HTTPError placing order: {e} - response: {getattr(e.response, 'text', None)}"
# #         try:
# #             if insert_event:
# #                 insert_event(kind="error", source="execution_agent", payload=err_text)
# #         except Exception:
# #             print("[execution_agent] failed to insert error event to DB")
# #         return {"error": True, "message": err_text}
# #     except Exception as e:
# #         err_text = f"Exception placing order: {e}"
# #         try:
# #             if insert_event:
# #                 insert_event(kind="error", source="execution_agent", payload=err_text)
# #         except Exception:
# #             print("[execution_agent] failed to insert error event to DB")
# #         return {"error": True, "message": err_text}

# #     # parse response
# #     try:
# #         exec_id = _safe_get_order_id(resp)
# #         fill_price = _safe_get_price(resp) or (float(price) if price is not None else 0.0)
# #         try:
# #             qty = float(resp.get("filled_size") or resp.get("amount") or amount)
# #         except Exception:
# #             qty = float(amount)
# #     except Exception as e:
# #         try:
# #             if insert_event:
# #                 insert_event(kind="error", source="execution_agent", payload=f"Post-exec parsing failed: {e}")
# #         except Exception:
# #             print("[execution_agent] failed to insert parsing error to DB")
# #         return {"error": True, "message": str(e)}

# #     # Persist trade record (pnl may be computed below)
# #     trade_id = None
# #     try:
# #         notes = json.dumps(resp, default=str)[:4000]
# #         if insert_trade:
# #             trade_id = insert_trade(symbol=symbol, side=side, qty=qty, price=fill_price, pnl=None, exec_id=exec_id, notes=notes)
# #     except Exception as e:
# #         try:
# #             if insert_event:
# #                 insert_event(kind="error", source="execution_agent", payload=f"DB insert_trade failed: {e}")
# #         except Exception:
# #             print("[execution_agent] failed to insert DB error event")

# #     # Update portfolio and compute realized pnl if selling
# #     try:
# #         pos = get_position(symbol) if get_position else None
# #         if side.lower() == "buy":
# #             # New avg_price = (old_qty*old_avg + qty*price) / (old_qty + qty)
# #             if pos and pos.get("qty") and pos.get("avg_price") is not None:
# #                 old_qty = float(pos["qty"])
# #                 old_avg = float(pos["avg_price"])
# #                 new_qty = old_qty + qty
# #                 new_avg = ((old_qty * old_avg) + (qty * fill_price)) / new_qty
# #             else:
# #                 old_qty = float(pos["qty"]) if pos and pos.get("qty") else 0.0
# #                 new_qty = old_qty + qty
# #                 new_avg = fill_price if new_qty > 0 else None
# #             if upsert_position:
# #                 upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=0.0)
# #         elif side.lower() == "sell":
# #             if not pos or not pos.get("qty"):
# #                 # No existing position: warn and set to zero
# #                 try:
# #                     if insert_event:
# #                         insert_event(kind="warning", source="execution_agent", payload=f"Sell executed but no existing position for {symbol}")
# #                 except Exception:
# #                     print("[execution_agent] failed to insert warning event")
# #                 if upsert_position:
# #                     upsert_position(symbol=symbol, qty=0, avg_price=None, realized_pnl_delta=0.0)
# #             else:
# #                 old_qty = float(pos["qty"])
# #                 old_avg = float(pos["avg_price"]) if pos.get("avg_price") is not None else 0.0
# #                 sell_qty = qty
# #                 if sell_qty > old_qty:
# #                     sell_qty = old_qty
# #                     try:
# #                         if insert_event:
# #                             insert_event(kind="warning", source="execution_agent", payload=f"Trying to sell more than holdings for {symbol}; capped to {sell_qty}")
# #                     except Exception:
# #                         print("[execution_agent] failed to insert warning event")
# #                 realized = (fill_price - old_avg) * sell_qty
# #                 new_qty = old_qty - sell_qty
# #                 new_avg = old_avg if new_qty > 0 else None
# #                 if upsert_position:
# #                     upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=realized)
# #                 # update the trade's pnl field to realized amount (for the sell trade)
# #                 if trade_id and update_trade_pnl:
# #                     try:
# #                         update_trade_pnl(trade_id, realized)
# #                     except Exception:
# #                         try:
# #                             if insert_event:
# #                                 insert_event(kind="error", source="execution_agent", payload=f"Failed to update trade pnl for id {trade_id}")
# #                         except Exception:
# #                             print("[execution_agent] failed to insert update_trade_pnl error")
# #     except Exception as e:
# #         try:
# #             if insert_event:
# #                 insert_event(kind="error", source="execution_agent", payload=f"Portfolio update failed: {e}")
# #         except Exception:
# #             print("[execution_agent] failed to insert portfolio update error")

# #     # Store raw execution event
# #     try:
# #         if insert_event:
# #             insert_event(kind="execution", source="execution_agent", payload=str(resp))
# #     except Exception:
# #         print("[execution_agent] failed to insert execution event to DB")

# #     return resp


# def place_order(symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
#     """
#     Place an order via Gemini sandbox (or mock).
#     This version updates portfolio and computes realized pnl when SELL closes a position,
#     AND updates the account cash balance (debit on buy, credit on sell).
#     """
#     # local import to avoid circular issues
#     from src.utils.db_utils_sqlite import (
#         insert_trade,
#         insert_event,
#         upsert_position,
#         get_position,
#         update_trade_pnl,
#         get_account_balance,
#         update_account_balance,
#     )


#     payload = {
#         "request": "/v1/order/new",
#         "nonce": str(int(time.time() * 1000)),
#         "symbol": symbol,
#         "amount": str(amount),
#         "side": side,
#         "type": "exchange limit" if price else "exchange market",
#     }
#     if price is not None:
#         payload["price"] = str(price)

#     # call API or mock
#     try:
#         if MOCK_EXECUTION:
#             resp = _call_gemini_api_mock(payload)
#         else:
#             resp = _call_gemini_api(payload)
#     except requests.HTTPError as e:
#         err_text = f"HTTPError placing order: {e} - response: {getattr(e.response, 'text', None)}"
#         try:
#             insert_event(kind="error", source="execution_agent", payload=err_text)
#         except Exception:
#             print("[execution_agent] failed to insert error event to DB")
#         return {"error": True, "message": err_text}
#     except Exception as e:
#         err_text = f"Exception placing order: {e}"
#         try:
#             insert_event(kind="error", source="execution_agent", payload=err_text)
#         except Exception:
#             print("[execution_agent] failed to insert error event to DB")
#         return {"error": True, "message": err_text}

#     # parse response
#     try:
#         exec_id = _safe_get_order_id(resp)
#         fill_price = _safe_get_price(resp) or (price if price is not None else 0.0)
#         try:
#             qty = float(resp.get("filled_size") or resp.get("amount") or amount)
#         except Exception:
#             qty = float(amount)
#     except Exception as e:
#         insert_event(kind="error", source="execution_agent", payload=f"Post-exec parsing failed: {e}")
#         return {"error": True, "message": str(e)}

#     # Persist trade record (pnl may be computed below)
#     trade_id = None
#     try:
#         notes = json.dumps(resp, default=str)[:4000]
#         trade_id = insert_trade(symbol=symbol, side=side, qty=qty, price=fill_price, pnl=None, exec_id=exec_id, notes=notes)
#     except Exception as e:
#         insert_event(kind="error", source="execution_agent", payload=f"DB insert_trade failed: {e}")

#     # --- ACCOUNT & PORTFOLIO UPDATES ---
#     try:
#         # Get account balance in USD
#         cash_bal = get_account_balance("USD")
#         # BUY: debit cash, update position
#         if side.lower() == "buy":
#             cost = qty * fill_price
#             if cost > cash_bal:
#                 # cap purchase to available cash
#                 if cash_bal <= 0:
#                     insert_event(kind="warning", source="execution_agent", payload=f"Insufficient cash for buy {symbol}: needed {cost}, have {cash_bal}")
#                     # rollback? trade already recorded as mock; mark pnl as 0 and return structured error
#                     try:
#                         update_trade_pnl(trade_id, 0.0)
#                     except Exception:
#                         pass
#                     return {"error": True, "message": "insufficient_cash"}
#                 # adjust qty to affordable amount (floor to 8 decimals)
#                 affordable_qty = (cash_bal / fill_price)
#                 affordable_qty = float(f"{affordable_qty:.8f}")
#                 # Update trade row qty and notes to reflect capped qty
#                 try:
#                     # update trades table to new qty (best-effort)
#                     conn = _get_conn()
#                     cur = conn.cursor()
#                     cur.execute("UPDATE trades SET qty = ? WHERE id = ?", (affordable_qty, trade_id))
#                     conn.commit()
#                     conn.close()
#                     qty = affordable_qty
#                     cost = qty * fill_price
#                     insert_event(kind="info", source="execution_agent", payload=f"Buy capped to affordable qty {qty} for {symbol}, cost {cost}")
#                 except Exception as e:
#                     insert_event(kind="error", source="execution_agent", payload=f"Failed to adjust trade qty on cap: {e}")

#             # update portfolio avg and qty
#             pos = get_position(symbol)
#             if pos and pos["qty"] > 0 and pos["avg_price"] is not None:
#                 old_qty = float(pos["qty"])
#                 old_avg = float(pos["avg_price"])
#                 new_qty = old_qty + qty
#                 new_avg = ((old_qty * old_avg) + (qty * fill_price)) / new_qty
#             else:
#                 new_qty = qty if not pos else (pos["qty"] + qty if pos["qty"] else qty)
#                 new_avg = fill_price
#             upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=0.0)
#             # debit cash
#             try:
#                 new_bal = update_account_balance(-cost, "USD")
#                 insert_event(kind="info", source="execution_agent", payload=f"Debited {cost} USD for buy {symbol}; new_balance={new_bal}")
#             except Exception as e:
#                 insert_event(kind="error", source="execution_agent", payload=f"Failed to debit account: {e}")

#         # SELL: credit cash, update position and compute realized pnl
#         elif side.lower() == "sell":
#             pos = get_position(symbol)
#             if not pos or pos["qty"] is None or pos["qty"] <= 0:
#                 insert_event(kind="warning", source="execution_agent", payload=f"Sell executed but no existing position for {symbol}")
#                 upsert_position(symbol=symbol, qty=0, avg_price=None, realized_pnl_delta=0.0)
#             else:
#                 old_qty = float(pos["qty"])
#                 old_avg = float(pos["avg_price"]) if pos["avg_price"] is not None else 0.0
#                 sell_qty = qty
#                 if sell_qty > old_qty:
#                     sell_qty = old_qty
#                     insert_event(kind="warning", source="execution_agent", payload=f"Trying to sell more than holdings for {symbol}; capped to {sell_qty}")
#                 realized = (fill_price - old_avg) * sell_qty
#                 new_qty = old_qty - sell_qty
#                 new_avg = old_avg if new_qty > 0 else None
#                 upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=realized)

#                 # update the trade's pnl field to realized amount (for the sell trade)
#                 if trade_id:
#                     try:
#                         update_trade_pnl(trade_id, realized)
#                     except Exception:
#                         insert_event(kind="error", source="execution_agent", payload=f"Failed to update trade pnl for id {trade_id}")

#                 # credit cash: proceeds = sell_qty * fill_price
#                 proceeds = sell_qty * fill_price
#                 try:
#                     new_bal = update_account_balance(proceeds, "USD")
#                     insert_event(kind="info", source="execution_agent", payload=f"Credited {proceeds} USD for sell {symbol}; realized={realized}; new_balance={new_bal}")
#                 except Exception as e:
#                     insert_event(kind="error", source="execution_agent", payload=f"Failed to credit account: {e}")

#     except Exception as e:
#         insert_event(kind="error", source="execution_agent", payload=f"Portfolio/account update failed: {e}")

#     # Store raw execution event
#     try:
#         insert_event(kind="execution", source="execution_agent", payload=str(resp))
#     except Exception:
#         print("[execution_agent] failed to insert execution event to DB")

#     return resp



# src/agents/execution_agent.py
"""
Execution agent: places orders either in MOCK mode or via Gemini sandbox.
Provides:
  - place_order(symbol, side, amount, price=None) -> Dict[str, Any]

This version:
 - supplies a realistic mock fill price for local testing,
 - falls back to market price if broker response contains no fill price,
 - updates trades, portfolio and account via src.utils.db_utils_sqlite helpers,
 - computes realized PnL on sell and updates trade.pnl,
 - caps buy quantity if insufficient cash and updates trade row accordingly.
"""

import os
import time
import json
import hmac
import base64
import hashlib
import requests
from typing import Optional, Dict, Any

# config (ensure src is in sys.path or run from project root with -m)
from src.utils.config import GEMINI_API_KEY, GEMINI_API_SECRET, MOCK_EXECUTION

# Gemini sandbox base URL (can be overridden by env var)
GEMINI_SANDBOX_BASE = "https://api.sandbox.gemini.com"
GEMINI_BASE = os.getenv("GEMINI_BASE", GEMINI_SANDBOX_BASE)


def _call_gemini_api_mock(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide a plausible mock response for testing / sandbox mode with a non-zero price.
    """
    # small simulated latency
    time.sleep(0.05)
    now_ms = int(time.time() * 1000)
    symbol = payload.get("symbol")
    amount = payload.get("amount")
    side = payload.get("side")
    # produce a plausible mock price (e.g. 100 + ms%1000 / 100)
    price = round(100.0 + (now_ms % 1000) / 100.0, 2)
    resp = {
        "order_id": f"mock-{now_ms}",
        "client_order_id": f"mock_client_{now_ms}",
        "symbol": symbol,
        "amount": amount,
        "side": side,
        "type": payload.get("type"),
        "status": "filled",
        "price": str(price),
        "avg_execution_price": price,
        "filled_size": amount,
        "timestamp": now_ms,
        "raw_payload": payload,
    }
    return resp


def _call_gemini_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Gemini v1 new order endpoint with HMAC signing.
    Requires GEMINI_API_KEY and GEMINI_API_SECRET to be set (sandbox or production keys).
    """
    if not GEMINI_API_KEY or not GEMINI_API_SECRET:
        raise RuntimeError("Gemini API key/secret not configured (GEMINI_API_KEY / GEMINI_API_SECRET).")

    # Build payload as required by Gemini v1
    payload = dict(payload)  # copy to avoid mutating caller
    payload["request"] = "/v1/order/new"
    payload["nonce"] = str(int(time.time() * 1000))

    j = json.dumps(payload)
    b64 = base64.b64encode(j.encode())
    signature = hmac.new(GEMINI_API_SECRET.encode(), b64, hashlib.sha384).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-GEMINI-APIKEY": GEMINI_API_KEY,
        "X-GEMINI-PAYLOAD": b64.decode(),
        "X-GEMINI-SIGNATURE": signature,
    }

    url = GEMINI_BASE + "/v1/order/new"
    r = requests.post(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def _safe_get_order_id(resp: Dict[str, Any]) -> Optional[str]:
    """
    Safely extract an order id from the response.
    """
    if not isinstance(resp, dict):
        return None
    for k in ("order_id", "id", "client_order_id", "exec_id"):
        v = resp.get(k)
        if v:
            return str(v)
    # nested search
    for v in resp.values():
        if isinstance(v, dict):
            for k2 in ("order_id", "id"):
                if k2 in v and v[k2]:
                    return str(v[k2])
    return None


def _safe_get_price(resp: Dict[str, Any]) -> Optional[float]:
    """
    Safely extract a price/avg execution price from the response.
    """
    if not isinstance(resp, dict):
        return None
    # Try common fields
    for k in ("avg_execution_price", "avg_price", "price", "filled_avg_price", "execution_price"):
        if k in resp and resp.get(k) is not None:
            try:
                return float(resp.get(k))
            except Exception:
                # sometimes numeric string
                try:
                    return float(str(resp.get(k)))
                except Exception:
                    continue
    # try nested dicts
    for v in resp.values():
        if isinstance(v, dict):
            for k2 in ("avg_execution_price", "price"):
                if k2 in v and v[k2] is not None:
                    try:
                        return float(v[k2])
                    except Exception:
                        continue
    return None


def place_order(symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """
    Place an order via Gemini sandbox (or mock) and update DB/account/portfolio.
    Returns the broker response dict or an error dict {"error": True, "message": "..."}.
    """
    # local imports to avoid circular imports at module import time
    from src.utils.db_utils_sqlite import (
        insert_trade,
        insert_event,
        upsert_position,
        get_position,
        update_trade_pnl,
        get_account_balance,
        update_account_balance,
        _get_conn,
    )

    # Build payload (Gemini v1 new order style)
    payload: Dict[str, Any] = {
        "symbol": symbol,
        "amount": str(amount),
        "side": side,
        "type": "exchange limit" if price is not None else "exchange market",
    }
    if price is not None:
        payload["price"] = str(price)

    # Call API (mock or real)
    try:
        if MOCK_EXECUTION:
            resp = _call_gemini_api_mock(payload)
        else:
            resp = _call_gemini_api(payload)
    except requests.HTTPError as e:
        err_text = f"HTTPError placing order: {e} - response: {getattr(e.response, 'text', None)}"
        try:
            insert_event(kind="error", source="execution_agent", payload=err_text)
        except Exception:
            print("[execution_agent] failed to insert error event to DB")
        return {"error": True, "message": err_text}
    except Exception as e:
        err_text = f"Exception placing order: {e}"
        try:
            insert_event(kind="error", source="execution_agent", payload=err_text)
        except Exception:
            print("[execution_agent] failed to insert error event to DB")
        return {"error": True, "message": err_text}

    # Parse response, with robust fill_price fallback
    try:
        exec_id = _safe_get_order_id(resp)
        fill_price = _safe_get_price(resp)
        # fallback order: API price -> given price -> market price via price_agent -> safe 1.0
        if fill_price is None or fill_price == 0.0:
            if price is not None:
                try:
                    fill_price = float(price)
                except Exception:
                    fill_price = None
        if fill_price is None or float(fill_price) == 0.0:
            # best-effort: ask price agent for market price
            try:
                from src.agents.price_agent import get_latest_price
                pr = get_latest_price(symbol)
                if isinstance(pr, dict):
                    last = pr.get("last") or {}
                    candidate = last.get("price") or last.get("last_price") or None
                    if candidate is not None:
                        fill_price = float(candidate)
            except Exception:
                # ignore and fallback later
                pass
        # final safety default (avoid zero division / zero costs)
        try:
            fill_price = float(fill_price) if fill_price is not None else 1.0
            if fill_price == 0.0:
                fill_price = 1.0
        except Exception:
            fill_price = 1.0

        try:
            qty = float(resp.get("filled_size") or resp.get("amount") or amount)
        except Exception:
            qty = float(amount)
    except Exception as e:
        try:
            insert_event(kind="error", source="execution_agent", payload=f"Post-exec parsing failed: {e}")
        except Exception:
            print("[execution_agent] failed to insert parsing error")
        return {"error": True, "message": str(e)}

    # Persist trade record (pnl may be computed below)
    trade_id = None
    try:
        notes = json.dumps(resp, default=str)[:4000]
        trade_id = insert_trade(symbol=symbol, side=side, qty=qty, price=fill_price, pnl=None, exec_id=exec_id, notes=notes)
    except Exception as e:
        try:
            insert_event(kind="error", source="execution_agent", payload=f"DB insert_trade failed: {e}")
        except Exception:
            print("[execution_agent] failed to insert DB error event")

    # --- ACCOUNT & PORTFOLIO UPDATES ---
    try:
        cash_bal = get_account_balance("USD")

        # BUY: debit cash, update position
        if side.lower() == "buy":
            cost = qty * fill_price
            if cost > cash_bal:
                # no funds: cap purchase (if possible) or return insufficient
                if cash_bal <= 0:
                    insert_event(kind="warning", source="execution_agent", payload=f"Insufficient cash for buy {symbol}: needed {cost}, have {cash_bal}")
                    try:
                        if trade_id:
                            update_trade_pnl(trade_id, 0.0)
                    except Exception:
                        pass
                    return {"error": True, "message": "insufficient_cash"}
                # cap to affordable qty
                affordable_qty = (cash_bal / fill_price)
                # round to safe precision
                affordable_qty = float(f"{affordable_qty:.8f}")
                try:
                    # update trades table qty to reflect cap
                    conn = _get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE trades SET qty = ? WHERE id = ?", (affordable_qty, trade_id))
                    conn.commit()
                    conn.close()
                    qty = affordable_qty
                    cost = qty * fill_price
                    insert_event(kind="info", source="execution_agent", payload=f"Buy capped to affordable qty {qty} for {symbol}, cost {cost}")
                except Exception as e:
                    insert_event(kind="error", source="execution_agent", payload=f"Failed to adjust trade qty on cap: {e}")

            # update portfolio avg and qty
            pos = get_position(symbol)
            if pos and pos.get("qty") and pos.get("avg_price") is not None:
                old_qty = float(pos["qty"])
                old_avg = float(pos["avg_price"])
                new_qty = old_qty + qty
                new_avg = ((old_qty * old_avg) + (qty * fill_price)) / new_qty
            else:
                old_qty = float(pos["qty"]) if pos and pos.get("qty") else 0.0
                new_qty = old_qty + qty
                new_avg = fill_price if new_qty > 0 else None

            upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=0.0)

            # debit cash
            try:
                new_bal = update_account_balance(-cost, "USD")
                insert_event(kind="info", source="execution_agent", payload=f"Debited {cost} USD for buy {symbol}; new_balance={new_bal}")
            except Exception as e:
                insert_event(kind="error", source="execution_agent", payload=f"Failed to debit account: {e}")

        # SELL: credit cash, update position and compute realized pnl
        elif side.lower() == "sell":
            pos = get_position(symbol)
            if not pos or not pos.get("qty"):
                insert_event(kind="warning", source="execution_agent", payload=f"Sell executed but no existing position for {symbol}")
                upsert_position(symbol=symbol, qty=0, avg_price=None, realized_pnl_delta=0.0)
            else:
                old_qty = float(pos["qty"])
                old_avg = float(pos["avg_price"]) if pos.get("avg_price") is not None else 0.0
                sell_qty = qty
                if sell_qty > old_qty:
                    sell_qty = old_qty
                    insert_event(kind="warning", source="execution_agent", payload=f"Trying to sell more than holdings for {symbol}; capped to {sell_qty}")

                realized = (fill_price - old_avg) * sell_qty
                new_qty = old_qty - sell_qty
                new_avg = old_avg if new_qty > 0 else None
                upsert_position(symbol=symbol, qty=new_qty, avg_price=new_avg, realized_pnl_delta=realized)

                # update the trade's pnl field to realized amount (for the sell trade)
                if trade_id:
                    try:
                        update_trade_pnl(trade_id, realized)
                    except Exception:
                        insert_event(kind="error", source="execution_agent", payload=f"Failed to update trade pnl for id {trade_id}")

                # credit cash: proceeds = sell_qty * fill_price
                proceeds = sell_qty * fill_price
                try:
                    new_bal = update_account_balance(proceeds, "USD")
                    insert_event(kind="info", source="execution_agent", payload=f"Credited {proceeds} USD for sell {symbol}; realized={realized}; new_balance={new_bal}")
                except Exception as e:
                    insert_event(kind="error", source="execution_agent", payload=f"Failed to credit account: {e}")

    except Exception as e:
        try:
            insert_event(kind="error", source="execution_agent", payload=f"Portfolio/account update failed: {e}")
        except Exception:
            print("[execution_agent] portfolio/account update failed:", e)

    # Store raw execution event
    try:
        insert_event(kind="execution", source="execution_agent", payload=str(resp))
    except Exception:
        print("[execution_agent] failed to insert execution event to DB")

    return resp
