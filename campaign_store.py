import sqlite3
from datetime import datetime, timezone

from post_rules import fold


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=10000")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            post_url TEXT PRIMARY KEY,
            group_url TEXT,
            author_id TEXT,
            content TEXT,
            status TEXT,
            jev_label TEXT,
            jev_confidence REAL,
            seen_at TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS comment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT,
            comment_text TEXT,
            success INTEGER,
            commented_at TEXT
        )
        """
    )
    _ensure_column(db, "posts", "account_name", "account_name TEXT DEFAULT ''")
    _ensure_column(db, "comment_history", "account_name", "account_name TEXT DEFAULT ''")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS account_seen (
            account_name TEXT NOT NULL DEFAULT '',
            post_url TEXT NOT NULL,
            content TEXT,
            status TEXT,
            PRIMARY KEY (account_name, post_url)
        )
        """
    )
    db.commit()
    return db


def _ensure_column(db, table, column, ddl):
    cols = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def post_status(db, post_url):
    row = db.execute("SELECT status FROM posts WHERE post_url = ?", (post_url,)).fetchone()
    return row["status"] if row else ""


def _owned(account_name):
    return account_name or ""


def story_already_commented(db, text, account_name=""):
    """A comment by one account does not count for another account."""
    folded = fold(text or "")[:200]
    if len(folded) < 30:
        return False
    owner = _owned(account_name)
    rows = db.execute(
        """
        SELECT content FROM posts
        WHERE status = 'commented' AND ifnull(account_name, '') = ?
        UNION ALL
        SELECT content FROM account_seen
        WHERE status = 'commented' AND ifnull(account_name, '') = ?
        """,
        (owner, owner),
    )
    for row in rows:
        old = fold(row["content"] or "")[:200]
        if len(old) >= 30 and (folded in old or old in folded):
            return True
    return False


def already_commented(db, post_url, account_name=""):
    row = db.execute(
        """
        SELECT 1 FROM comment_history
        WHERE post_url = ? AND success = 1 AND ifnull(account_name, '') = ?
        """,
        (post_url, _owned(account_name)),
    ).fetchone()
    return row is not None


def _remember_account(db, account_name, post, status):
    db.execute(
        """
        INSERT INTO account_seen (account_name, post_url, content, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(account_name, post_url) DO UPDATE SET
            content = excluded.content,
            status = excluded.status
        """,
        (_owned(account_name), post["post_url"], post.get("text", ""), status),
    )


def save_post(db, post, status, label=None, confidence=None, account_name=""):
    owner = _owned(account_name)
    existing = db.execute(
        "SELECT ifnull(account_name, '') AS account_name FROM posts WHERE post_url = ?",
        (post["post_url"],),
    ).fetchone()
    # One URL can be commented by several accounts. Do not replace the other account's row.
    if existing and existing["account_name"] and owner and existing["account_name"] != owner:
        _remember_account(db, owner, post, status)
        db.commit()
        return
    db.execute(
        """
        INSERT INTO posts (post_url, group_url, author_id, content, status, jev_label, jev_confidence, seen_at, account_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_url) DO UPDATE SET
            status = excluded.status,
            jev_label = excluded.jev_label,
            jev_confidence = excluded.jev_confidence,
            account_name = excluded.account_name
        """,
        (
            post["post_url"],
            post.get("group_url", ""),
            post.get("author_id", ""),
            post.get("text", ""),
            status,
            label,
            confidence,
            datetime.now(timezone.utc).isoformat(),
            owner,
        ),
    )
    if status == "commented":
        _remember_account(db, owner, post, status)
    db.commit()


def save_comment(db, post_url, comment, success, account_name=""):
    db.execute(
        "INSERT INTO comment_history (post_url, comment_text, success, commented_at, account_name) VALUES (?, ?, ?, ?, ?)",
        (post_url, comment, 1 if success else 0, datetime.now(timezone.utc).isoformat(), account_name),
    )
    db.commit()
