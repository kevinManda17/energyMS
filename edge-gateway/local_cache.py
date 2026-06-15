"""
Local SQLite cache for the Edge Gateway.

Stores incoming measurements locally so the gateway keeps working when the
cloud backend is unreachable, and tracks which rows still need syncing.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("EDGE_DB_PATH", "edge_cache.db")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                house_id INTEGER,
                payload TEXT NOT NULL,
                synced INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_measurement(house_id, payload_json):
    with _conn() as c:
        c.execute(
            "INSERT INTO measurements (house_id, payload) VALUES (?, ?)",
            (house_id, payload_json),
        )


def pending(limit=100):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM measurements WHERE synced = 0 ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_synced(ids):
    if not ids:
        return
    with _conn() as c:
        c.executemany(
            "UPDATE measurements SET synced = 1 WHERE id = ?",
            [(i,) for i in ids],
        )


def latest(limit=20):
    """Most recent cached measurements — served by the local API."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM measurements ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
