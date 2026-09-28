"""Accounts + settings CRUD on top of campaign_store's SQLite db."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import campaign_store

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = _DATA_DIR / "app.db"

ACCOUNT_FIELDS = (
    "name", "cookie", "page_id", "proxy", "profile_dir",
    "comment_list", "use_profile", "created_at", "updated_at",
)


def connect(path=None):
    db = campaign_store.connect(path or DB_PATH)
    db.execute("PRAGMA busy_timeout=10000")
    _migrate(db)
    return db


def _ensure_column(db, table, column, ddl):
    cols = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migrate(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS accounts (
            name TEXT PRIMARY KEY,
            cookie TEXT DEFAULT '',
            page_id TEXT DEFAULT '',
            proxy TEXT DEFAULT '',
            profile_dir TEXT DEFAULT '',
            comment_list TEXT DEFAULT '',
            use_profile INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    db.execute("CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT)")
    _ensure_column(db, "posts", "account_name", "account_name TEXT DEFAULT ''")
    _ensure_column(db, "comment_history", "account_name", "account_name TEXT DEFAULT ''")
    db.commit()


def list_accounts(db):
    rows = db.execute("SELECT * FROM accounts ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_account(db, name):
    row = db.execute("SELECT * FROM accounts WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def upsert_account(db, account):
    now = datetime.now(timezone.utc).isoformat()
    existing = get_account(db, account["name"])
    created = existing["created_at"] if existing else now
    db.execute(
        """INSERT INTO accounts (name, cookie, page_id, proxy, profile_dir,
                                 comment_list, use_profile, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
               cookie=excluded.cookie, page_id=excluded.page_id,
               proxy=excluded.proxy, profile_dir=excluded.profile_dir,
               comment_list=excluded.comment_list,
               use_profile=excluded.use_profile, updated_at=excluded.updated_at""",
        (
            account["name"],
            account.get("cookie", ""),
            account.get("page_id", ""),
            account.get("proxy", ""),
            account.get("profile_dir", ""),
            account.get("comment_list", ""),
            1 if account.get("use_profile") else 0,
            created,
            now,
        ),
    )
    db.commit()
    return get_account(db, account["name"])


def delete_account(db, name):
    db.execute("DELETE FROM accounts WHERE name = ?", (name,))
    db.commit()


def get_settings(db):
    return {r["k"]: r["v"] for r in db.execute("SELECT k, v FROM settings")}


def set_settings(db, values):
    for k, v in values.items():
        db.execute(
            "INSERT INTO settings (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (str(k), str(v)),
        )
    db.commit()
