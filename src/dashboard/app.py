# src/dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
import os

from src.utils.db_utils_sqlite import fetch_trades, get_portfolio, compute_unrealized_pnl

st.set_page_config(page_title="Autotrade Agent Dashboard", layout="wide")
st.title("Autotrade Agent Dashboard")

col_control_1, col_control_2 = st.columns([1, 4])
with col_control_1:
    if st.button("🔄 Refresh trades"):
        st.rerun()
with col_control_2:
    st.markdown(f"**Last loaded:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Fetch trades
try:
    trades = fetch_trades(limit=1000)
    if trades:
        df = pd.DataFrame(trades)
    else:
        df = pd.DataFrame(columns=["id", "timestamp", "symbol", "side", "qty", "price", "pnl", "exec_id", "notes"])
except Exception as e:
    st.error(f"Failed to read trades DB: {e}")
    df = pd.DataFrame()

# Portfolio
portfolio = get_portfolio()  # dict symbol -> {qty, avg_price, realized_pnl, updated_at}
portfolio_rows = []
total_unrealized = 0.0
for symbol, p in portfolio.items():
    qty = p.get("qty", 0.0)
    avg = p.get("avg_price", None)
    realized = p.get("realized_pnl", 0.0) or 0.0
    # get current market price (best-effort)
    try:
        from src.agents.price_agent import get_latest_price
        price_resp = get_latest_price(symbol)
        market_price = (price_resp.get("last") or {}).get("price") if isinstance(price_resp, dict) else None
        market_price = float(market_price) if market_price else None
    except Exception:
        market_price = None
    unreal = compute_unrealized_pnl(symbol, market_price) if market_price else 0.0
    total_unrealized += unreal
    portfolio_rows.append({"symbol": symbol, "qty": qty, "avg_price": avg, "market_price": market_price, "unrealized": unreal, "realized": realized})

# Layout
col1, col2 = st.columns((2,1))
with col1:
    st.subheader("Trade Log")
    st.dataframe(df, height=300)

with col2:
    st.subheader("Key Metrics")
    total_realized = sum(p["realized_pnl"] or 0.0 for p in portfolio.values())
    st.metric("Total Realized PnL", f"${total_realized:.2f}")
    st.metric("Total Unrealized PnL", f"${total_unrealized:.2f}")
    st.metric("Positions", len(portfolio_rows))

# Portfolio table
st.subheader("Portfolio")
if portfolio_rows:
    p_df = pd.DataFrame(portfolio_rows)
    st.dataframe(p_df)
else:
    st.info("No positions currently held.")

# PnL over time (use realized pnl by trade)
st.subheader("PNL over time")
if not df.empty and "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    # compute cumulative realized pnl over time (sum of trade.pnl where pnl not null)
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df_sorted = df.sort_values("timestamp")
    df_sorted["cumulative_pnl"] = df_sorted["pnl"].cumsum()
    fig = px.line(df_sorted, x="timestamp", y="cumulative_pnl", title="Cumulative Realized PnL")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No PnL data available yet.")
