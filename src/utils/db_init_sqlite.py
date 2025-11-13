# # src/utils/db_init_sqlite.py
# import sqlite3
# from pathlib import Path

# PROJECT_ROOT = Path(__file__).resolve().parents[2]
# DATA_DIR = PROJECT_ROOT / "src" / "data"
# DATA_DIR.mkdir(parents=True, exist_ok=True)
# DB_PATH = DATA_DIR / "trades.db"

# SCHEMA = """
# BEGIN;
# CREATE TABLE IF NOT EXISTS trades (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     timestamp TEXT NOT NULL,
#     symbol TEXT NOT NULL,
#     side TEXT NOT NULL,
#     qty REAL NOT NULL,
#     price REAL NOT NULL,
#     pnl REAL,
#     exec_id TEXT,
#     notes TEXT
# );

# CREATE TABLE IF NOT EXISTS events (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     timestamp TEXT NOT NULL,
#     kind TEXT NOT NULL,        -- e.g., "news", "sentiment", "decision", "error"
#     source TEXT,
#     payload TEXT
# );
# COMMIT;
# """

# def init_db():
#     print(f"Initializing SQLite DB at: {DB_PATH}")
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.executescript(SCHEMA)
#     conn.commit()
#     conn.close()
#     print("DB initialized.")

# if __name__ == "__main__":
#     init_db()


# src/utils/db_init_sqlite.py
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "trades.db"

SCHEMA = """
BEGIN;

-- ---------- TRADES TABLE ----------
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

-- ---------- EVENTS TABLE ----------
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT,
    payload TEXT
);

-- ---------- PORTFOLIO TABLE ----------
CREATE TABLE IF NOT EXISTS portfolio (
    symbol TEXT PRIMARY KEY,
    qty REAL NOT NULL,
    avg_price REAL,
    realized_pnl REAL DEFAULT 0.0,
    updated_at TEXT NOT NULL
);

-- ---------- ACCOUNT TABLE ----------
-- Stores available cash per currency
CREATE TABLE IF NOT EXISTS account (
    currency TEXT PRIMARY KEY,
    cash REAL NOT NULL
);

COMMIT;
"""


def init_db():
    print(f"Initializing SQLite DB at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("DB initialized successfully.")

if __name__ == "__main__":
    init_db()
