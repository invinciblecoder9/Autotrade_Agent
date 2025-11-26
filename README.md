# Autonomous AI Trading Agent

**News-aware • Sentiment-driven • Autonomous execution • Streamlit dashboard**

A compact, end-to-end autonomous trading project that demonstrates multi-agent orchestration (news → sentiment → prices → decision → execution), portfolio & account accounting, Telegram notifications, and a production-style Streamlit dashboard. The repo supports mock execution, Gemini sandbox (HMAC signed), and can be switched to live exchange keys after thorough sandbox testing.

---

## Table of Contents

- [What this project does](#what-this-project-does)
- [Architecture (high level)](#architecture-high-level)
- [Key features (quick)](#key-features-quick)
- [Tech stack & APIs used](#tech-stack--apis-used)
- [Repository layout](#repository-layout)
- [Prerequisites (Windows)](#prerequisites-windows)
- [Install & setup (PowerShell)](#install--setup-powershell)
- [Environment variables (.env) — example](#environment-variables-env--example)
- [DB initialization](#db-initialization)
- [How to run (commands)](#how-to-run-commands)
  - [Run one cycle (safe test)](#run-one-cycle-safe-test)
  - [Run long-running agent](#run-long-running-agent)
  - [Open the dashboard (Streamlit)](#open-the-dashboard-streamlit)
  - [Force tests (mock buy/sell)](#force-tests-mock-buysell)
  - [Quick status & DB inspection](#quick-status--db-inspection)
- [Important safety notes (read before live)](#important-safety-notes-read-before-live)
- [Recommended next steps / improvements](#recommended-next-steps--improvements)
- [Tests included (and how to run)](#tests-included-and-how-to-run)
- [Resume bullets (copy/paste)](#resume-bullets-copypaste)
- [License & credits](#license--credits)

---

## What this project does

- Continuously collects finance-related news (ddgs) for configured tickers.
- Scores articles with VADER sentiment and aggregates the signals.
- Fetches market prices (AlphaVantage primary; yfinance / CoinGecko fallback).
- Applies a rule-based decision engine (`decision_agent.py`) to BUY / SELL / HOLD.
- Places orders using `execution_agent.py` — supports mock (local), Gemini sandbox with HMAC signing, or live Gemini.
- Tracks all executions and state in SQLite (`src/data/trades.db`) with tables: `trades`, `events`, `portfolio`, `account`.
- Updates portfolio (qty, avg_price, realized PnL) and account cash (debit on buy / credit on sell).
- Notifies trade/exceptions via Telegram.
- Visualizes trade log, portfolio, realized/unrealized PnL and cumulative PnL using Streamlit + Plotly.

---

## Architecture (high level)
```
DuckDuckGo (ddgs)  AlphaVantage / yfinance / CoinGecko
       │                   │
    news_agent  ───────────┴───────► price_agent
       │                              ▲
       ▼                              │
  sentiment_agent                     │
       │                              │
       └─────► decision_agent ─────► execution_agent (mock / Gemini)
                         │                  │
                         │                  ▼
                         │             db_utils_sqlite  (trades, events, portfolio, account)
                         ▼                  │
                  notifier_agent ◄──────────┘
                         │
                         ▼
                  Streamlit Dashboard
```

---

## Key features (quick)

- Modular multi-agent design (news, sentiment, price, decision, execution, notifier).
- Execution agent supports mock + Gemini Sandbox (HMAC signature logic implemented).
- Persistent accounting: `account` table for USD cash and `portfolio` table for positions (qty, avg_price, realized_pnl).
- Realized PnL updated at sell time; unrealized computed in the dashboard.
- Streamlit dashboard with refresh, trade log, portfolio and cumulative realized PnL.
- Test helpers: `run_once.py`, `tests/force_trade.py`, `tests/force_sell.py`, small tests for agents.

---

## Tech stack & APIs used

- **Python 3.12** (recommended)
- **ddgs** (DuckDuckGo search) — news agent
- **vaderSentiment** — sentiment scoring
- **AlphaVantage** (`ALPHAVANTAGE_KEY`) — primary quote provider
- **yfinance** — fallback quote provider (good for crypto via mapping)
- **CoinGecko** — fallback crypto price provider
- **Gemini API** — sandbox/live order execution (HMAC-signed)
- **SQLite** — persistence (local file `src/data/trades.db`)
- **Streamlit + Plotly** — dashboard
- **requests, python-dotenv, pandas** etc.

---

## Repository layout
```
autotrade-agent/
├─ src/
│  ├─ main.py                    # runner & loop
│  ├─ agents/
│  │  ├─ news_agent.py
│  │  ├─ sentiment_agent.py
│  │  ├─ price_agent.py
│  │  ├─ decision_agent.py
│  │  ├─ execution_agent.py
│  │  └─ notifier_agent.py
│  ├─ utils/
│  │  ├─ db_init_sqlite.py
│  │  └─ db_utils_sqlite.py
│  └─ dashboard/
│     └─ app.py
├─ tests/
│  ├─ force_trade.py
│  ├─ force_sell.py
│  └─ test_*.py
├─ run_once.py
├─ check_status.py
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## Prerequisites (Windows)

- **Python 3.12** (recommended for best wheel compatibility)
- **PowerShell** (Windows)
- **Optional**: Git, Visual Studio Build Tools (only if a package requires building)

---

## Install & setup (PowerShell)

1. **Clone and enter project root:**
```powershell
git clone https://github.com/<your-username>/autotrade-agent.git
cd autotrade-agent
```

2. **Create & activate virtualenv (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Upgrade packaging tools and install requirements:**
```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

> If you face wheel/compilation errors on some packages (e.g., `pyarrow`), prefer Python 3.12 or remove the optional package from `requirements.txt`.

---

## Environment variables (.env) — example

Create a `.env` in project root (do not commit this file):
```env
# News / search
DDGS_REGION=us-en

# Price APIs
ALPHAVANTAGE_KEY=your_alpha_vantage_key
POLYGON_KEY=your_polygon_key   # optional

# Execution (Gemini)
GEMINI_BASE=https://api.sandbox.gemini.com
GEMINI_API_KEY=your_sandbox_key
GEMINI_API_SECRET=your_sandbox_secret
MOCK_EXECUTION=true      # "true" uses mock; set to "false" to use GEMINI_BASE

# Notifications
TELEGRAM_BOT_TOKEN=bot123:ABC...
TELEGRAM_CHAT_ID=987654321
```

> The code also supports reading the same variables from `src.utils.config` if you prefer to centralize config there.

---

## DB initialization

Run once to create the DB and tables (`src/data/trades.db`):
```powershell
python src/utils/db_init_sqlite.py
```

This will create `trades`, `events`, `portfolio`, and `account` tables and initialize the USD account if missing.

---

## How to run (commands)

> **Tip**: prefer running as a module / from project root so imports resolve correctly.

### Run one cycle (safe test)

`run_once.py` sets `sys.path` so imports work reliably:
```powershell
python run_once.py
```

**Expected outcome**: console logs for each ticker (aggregate sentiment, price, decision) and a single run. Good for smoke testing.

### Run long-running agent (loop every ~15 minutes)
```powershell
python -m src.main
```

The agent will initialize DB (if needed) and run continuously until stopped (Ctrl+C). It fetches news, scores sentiment, fetches price, decides, executes (mock or Gemini) and notifies.

### Open the dashboard (Streamlit)

In a separate terminal (venv active):
```powershell
python -m streamlit run src/dashboard/app.py
```

Open the URL shown by Streamlit (usually `http://localhost:8501`). Click 🔄 **Refresh trades** to reload.

### Force tests (mock buy/sell)

**Mock buy** (demo helper):
```powershell
python tests/force_trade.py
```

**Mock sell**:
```powershell
python tests/force_sell.py
```

These use `execution_agent.place_order` and notify via Telegram. They are safe if `MOCK_EXECUTION=true`.

### Quick status & DB inspection

From PowerShell one-liner:
```powershell
python -c "from src.utils.db_utils_sqlite import get_account_balance, get_position, fetch_trades; print('balance:', get_account_balance('USD')); print('pos:', get_position('BTCUSD')); print('recent trades:', fetch_trades(5))"
```

Or run the included script:
```powershell
python check_status.py
```

---

## Important safety notes (read before live)

- **Default mode should be mock or sandbox**. Keep `MOCK_EXECUTION=true` while testing. Use Gemini sandbox (`GEMINI_BASE=https://api.sandbox.gemini.com`) for authenticated tests.
- **Circuit-breakers**: add limits for `max_daily_loss`, `max_position_size`, `max_trades_per_day` before live trading. (You can add simple checks in `src/main.py` before calling `place_order`.)
- **Rate limits**: AlphaVantage allows 5 requests/min — design caching/TTL or use Polygon/yfinance to avoid hitting limits.
- **Idempotency**: avoid duplicate orders on restarts. Consider a `client_order_id` per decision and check `events`.
- **Backups**: back up `src/data/trades.db` regularly.
- **Never commit `.env` or API keys**.

---

## Tests included (and how to run)

- `run_once.py` — run a single pipeline cycle
- `tests/force_trade.py` — mock buy helper
- `tests/force_sell.py` — mock sell helper
- `tests/test_news_agent.py`, `tests/test_price_agent.py`, `tests/test_sentiment_agent.py` — small smoke tests

Run tests by executing the scripts directly (PowerShell), e.g.:
```powershell
python tests/test_sentiment_agent.py
python tests/test_price_agent.py
```

> (If tests need env keys for AlphaVantage, set `ALPHAVANTAGE_KEY` in `.env` or your session.)
