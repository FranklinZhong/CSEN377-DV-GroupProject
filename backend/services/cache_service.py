"""
api_cache table operations.

All external API results (FDA Drug Label, FAERS API, Claude) are cached here
so that repeated requests for the same drug are instant.
"""

import json
from datetime import datetime, timedelta
import sqlite3


def get_cached(key: str, conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT response_json, expires_at FROM api_cache WHERE cache_key = ?",
        (key,)
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
        return None
    return json.loads(row["response_json"])


def set_cached(key: str, data: dict, conn: sqlite3.Connection, ttl_days: int = 7):
    now = datetime.utcnow()
    expires = now + timedelta(days=ttl_days)
    conn.execute(
        """
        INSERT INTO api_cache (cache_key, response_json, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            response_json = excluded.response_json,
            created_at    = excluded.created_at,
            expires_at    = excluded.expires_at
        """,
        (key, json.dumps(data), now.isoformat(), expires.isoformat()),
    )
    conn.commit()


def invalidate_all(conn: sqlite3.Connection):
    """Called after pipeline re-run to clear stale data."""
    conn.execute("DELETE FROM api_cache")
