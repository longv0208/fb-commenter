import sqlite3
from datetime import datetime, timezone


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
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
    db.commit()
    return db


def already_commented(db, post_url):
    row = db.execute(
        "SELECT 1 FROM comment_history WHERE post_url = ? AND success = 1",
        (post_url,),
    ).fetchone()
    return row is not None


def save_post(db, post, status, label=None, confidence=None):
    db.execute(
        """
        INSERT INTO posts (post_url, group_url, author_id, content, status, jev_label, jev_confidence, seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_url) DO UPDATE SET
            status = excluded.status,
            jev_label = excluded.jev_label,
            jev_confidence = excluded.jev_confidence
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
        ),
    )
    db.commit()


def save_comment(db, post_url, comment, success):
    db.execute(
        "INSERT INTO comment_history (post_url, comment_text, success, commented_at) VALUES (?, ?, ?, ?)",
        (post_url, comment, 1 if success else 0, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
