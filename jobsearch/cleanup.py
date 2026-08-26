"""Deletes unstarred jobs older than the retention window.

seen_ledger is untouched - it's permanent by design, so a deleted job's hash
is still remembered and won't reappear as "new" on a later fetch.
"""

import sqlite3


def cleanup_unstarred(conn: sqlite3.Connection, retention_days: int) -> int:
    cursor = conn.execute(
        "DELETE FROM jobs WHERE starred = 0 AND first_seen_at < datetime('now', ?)",
        (f"-{retention_days} days",),
    )
    conn.commit()
    return cursor.rowcount
