# # src/utils/db_utils_sqlite.py
# import sqlite3
# from pathlib import Path
# from datetime import datetime, timezone
# from typing import Optional, List, Dict

# PROJECT_ROOT = Path(__file__).resolve().parents[2]
# DB_PATH = PROJECT_ROOT / "src" / "data" / "trades.db"

# def _get_conn():
#     conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
#                            check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     try:
#         conn.execute("PRAGMA journal_mode=WAL;")
#     except Exception:
#         pass
#     return conn

# def init_db():
#     """Create missing tables (safe to run repeatedly)."""
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.executescript("""
#     CREATE TABLE IF NOT EXISTS trades (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         timestamp TEXT NOT NULL,
#         symbol TEXT NOT NULL,
#         side TEXT NOT NULL,
#         qty REAL NOT NULL,
#         price REAL NOT NULL,
#         pnl REAL,
#         exec_id TEXT,
#         notes TEXT
#     );

#     CREATE TABLE IF NOT EXISTS events (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         timestamp TEXT NOT NULL,
#         kind TEXT NOT NULL,
#         source TEXT,
#         payload TEXT
#     );

#     CREATE TABLE IF NOT EXISTS portfolio (
#         symbol TEXT PRIMARY KEY,
#         qty REAL NOT NULL,
#         avg_price REAL,
#         realized_pnl REAL DEFAULT 0.0,
#         updated_at TEXT
#     );

#     CREATE TABLE IF NOT EXISTS meta (
#         key TEXT PRIMARY KEY,
#         value TEXT
#     );
#     """)
#     conn.commit()
#     conn.close()

# # --- trades / events helpers
# def insert_trade(symbol, side, qty, price, pnl=None, exec_id=None, notes=None, timestamp=None):
#     ts = timestamp or datetime.now(timezone.utc).isoformat()
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute(
#         "INSERT INTO trades (timestamp, symbol, side, qty, price, pnl, exec_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
#         (ts, symbol, side, qty, price, pnl, exec_id, notes)
#     )
#     conn.commit()
#     last_id = cur.lastrowid
#     conn.close()
#     return last_id

# def update_trade_pnl(trade_id: int, pnl: float):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("UPDATE trades SET pnl = ? WHERE id = ?", (pnl, trade_id))
#     conn.commit()
#     conn.close()

# def insert_event(kind, source=None, payload=None, timestamp=None):
#     ts = timestamp or datetime.now(timezone.utc).isoformat()
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute(
#         "INSERT INTO events (timestamp, kind, source, payload) VALUES (?, ?, ?, ?)",
#         (ts, kind, source, payload)
#     )
#     conn.commit()
#     last_id = cur.lastrowid
#     conn.close()
#     return last_id

# def fetch_trades(limit=200):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,))
#     rows = cur.fetchall()
#     conn.close()
#     return [dict(r) for r in rows]

# def fetch_events(limit=200):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
#     rows = cur.fetchall()
#     conn.close()
#     return [dict(r) for r in rows]

# # --- portfolio helpers
# def get_portfolio() -> Dict[str, Dict]:
#     """
#     Returns a dict keyed by symbol: {symbol: {qty, avg_price, realized_pnl, updated_at}}
#     """
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM portfolio")
#     rows = cur.fetchall()
#     conn.close()
#     return {r["symbol"]: {"qty": r["qty"], "avg_price": r["avg_price"], "realized_pnl": r["realized_pnl"], "updated_at": r["updated_at"]} for r in rows}

# def get_position(symbol: str) -> Optional[Dict]:
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM portfolio WHERE symbol = ?", (symbol,))
#     row = cur.fetchone()
#     conn.close()
#     return dict(row) if row else None

# def upsert_position(symbol: str, qty: float, avg_price: Optional[float], realized_pnl_delta: float = 0.0):
#     """
#     Insert or update position. qty may be zero (to clear).
#     realized_pnl_delta adds to existing realized pnl.
#     """
#     now = datetime.now(timezone.utc).isoformat()
#     conn = _get_conn()
#     cur = conn.cursor()
#     # check existing
#     cur.execute("SELECT qty, avg_price, realized_pnl FROM portfolio WHERE symbol = ?", (symbol,))
#     row = cur.fetchone()
#     if row:
#         prev_qty = row["qty"]
#         prev_avg = row["avg_price"] or 0.0
#         prev_realized = row["realized_pnl"] or 0.0
#         new_realized = prev_realized + realized_pnl_delta
#         # If qty becomes zero, keep avg_price as NULL
#         new_avg = avg_price if qty != 0 else None
#         cur.execute("UPDATE portfolio SET qty = ?, avg_price = ?, realized_pnl = ?, updated_at = ? WHERE symbol = ?",
#                     (qty, new_avg, new_realized, now, symbol))
#     else:
#         cur.execute("INSERT INTO portfolio (symbol, qty, avg_price, realized_pnl, updated_at) VALUES (?, ?, ?, ?, ?)",
#                     (symbol, qty, avg_price, realized_pnl_delta, now))
#     conn.commit()
#     conn.close()

# def compute_unrealized_pnl(symbol: str, market_price: float) -> float:
#     pos = get_position(symbol)
#     if not pos or pos["qty"] == 0 or pos["avg_price"] is None:
#         return 0.0
#     qty = pos["qty"]
#     avg = pos["avg_price"]
#     return (market_price - avg) * qty

# def get_equity_snapshot() -> Dict:
#     """
#     Return overall portfolio summary: total_realized, total_unrealized, positions list
#     """
#     portfolio = get_portfolio()
#     # compute unrealized using latest market price - this requires caller to supply prices;
#     # For the dashboard we'll compute per-symbol market price separately.
#     total_realized = sum(p["realized_pnl"] or 0.0 for p in portfolio.values())
#     return {"positions": portfolio, "total_realized": total_realized}

# src/utils/db_utils_sqlite.py
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "src" / "data" / "trades.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def init_db():
    """Create missing tables (safe to run repeatedly)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        qty REAL NOT NULL,
        price REAL NOT NULL,
        pnl REAL,
        exec_id TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        kind TEXT NOT NULL,
        source TEXT,
        payload TEXT
    );

    CREATE TABLE IF NOT EXISTS portfolio (
        symbol TEXT PRIMARY KEY,
        qty REAL NOT NULL,
        avg_price REAL,
        realized_pnl REAL DEFAULT 0.0,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS account (
        currency TEXT PRIMARY KEY,
        cash REAL NOT NULL,
        updated_at TEXT
    );
    """)
    conn.commit()
    conn.close()

    # ensure default USD account exists (10000 USD)
    ensure_account_initialized("USD", 10000.0)


# --- trades / events helpers
def insert_trade(symbol, side, qty, price, pnl=None, exec_id=None, notes=None, timestamp=None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trades (timestamp, symbol, side, qty, price, pnl, exec_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, symbol, side, qty, price, pnl, exec_id, notes)
    )
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def update_trade_pnl(trade_id: int, pnl: float):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE trades SET pnl = ? WHERE id = ?", (pnl, trade_id))
    conn.commit()
    conn.close()

def insert_event(kind, source=None, payload=None, timestamp=None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (timestamp, kind, source, payload) VALUES (?, ?, ?, ?)",
        (ts, kind, source, payload)
    )
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def fetch_trades(limit=200):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_events(limit=200):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- portfolio helpers
def get_portfolio() -> Dict[str, Dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM portfolio")
    rows = cur.fetchall()
    conn.close()
    return {r["symbol"]: {"qty": r["qty"], "avg_price": r["avg_price"], "realized_pnl": r["realized_pnl"], "updated_at": r["updated_at"]} for r in rows}

def get_position(symbol: str) -> Optional[Dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM portfolio WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_position(symbol: str, qty: float, avg_price: Optional[float], realized_pnl_delta: float = 0.0):
    """
    Insert or update position. qty may be zero (to clear).
    realized_pnl_delta adds to existing realized pnl.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    # check existing
    cur.execute("SELECT qty, avg_price, realized_pnl FROM portfolio WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    if row:
        prev_qty = row["qty"]
        prev_avg = row["avg_price"] or 0.0
        prev_realized = row["realized_pnl"] or 0.0
        new_realized = prev_realized + realized_pnl_delta
        # If qty becomes zero, keep avg_price as NULL
        new_avg = avg_price if qty != 0 else None
        cur.execute("UPDATE portfolio SET qty = ?, avg_price = ?, realized_pnl = ?, updated_at = ? WHERE symbol = ?",
                    (qty, new_avg, new_realized, now, symbol))
    else:
        cur.execute("INSERT INTO portfolio (symbol, qty, avg_price, realized_pnl, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (symbol, qty, avg_price, realized_pnl_delta, now))
    conn.commit()
    conn.close()

def compute_unrealized_pnl(symbol: str, market_price: float) -> float:
    pos = get_position(symbol)
    if not pos or pos["qty"] == 0 or pos["avg_price"] is None:
        return 0.0
    qty = pos["qty"]
    avg = pos["avg_price"]
    return (market_price - avg) * qty

def get_equity_snapshot() -> Dict:
    portfolio = get_portfolio()
    total_realized = sum(p["realized_pnl"] or 0.0 for p in portfolio.values())
    return {"positions": portfolio, "total_realized": total_realized}


# --- account helpers (NEW)
def ensure_account_initialized(currency: str = "USD", initial_cash: float = 10000.0):
    """Create account row if missing."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT cash FROM account WHERE currency = ?", (currency,))
    row = cur.fetchone()
    if not row:
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("INSERT INTO account (currency, cash, updated_at) VALUES (?, ?, ?)", (currency, initial_cash, now))
        conn.commit()
    conn.close()

def get_account_balance(currency: str = "USD") -> float:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT cash FROM account WHERE currency = ?", (currency,))
    row = cur.fetchone()
    conn.close()
    return float(row["cash"]) if row else 0.0

def set_account_balance(amount: float, currency: str = "USD"):
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO account(currency, cash, updated_at) VALUES (?, ?, ?) ON CONFLICT(currency) DO UPDATE SET cash = excluded.cash, updated_at = excluded.updated_at", (currency, amount, now))
    conn.commit()
    conn.close()

def update_account_balance(delta: float, currency: str = "USD") -> float:
    """
    Add delta to cash (delta can be negative to debit). Returns new balance.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT cash FROM account WHERE currency = ?", (currency,))
    row = cur.fetchone()
    if row:
        new = float(row["cash"]) + float(delta)
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE account SET cash = ?, updated_at = ? WHERE currency = ?", (new, now, currency))
    else:
        # create account row
        new = float(delta)
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("INSERT INTO account (currency, cash, updated_at) VALUES (?, ?, ?)", (currency, new, now))
    conn.commit()
    conn.close()
    return new
