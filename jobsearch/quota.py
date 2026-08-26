"""Tracks LLM extraction calls made per calendar day, in the llm_usage table."""

import sqlite3


def get_today_usage(conn: sqlite3.Connection, today: str) -> int:
    row = conn.execute("SELECT calls_made FROM llm_usage WHERE usage_date = ?", (today,)).fetchone()
    return row["calls_made"] if row else 0


def increment_usage(conn: sqlite3.Connection, today: str) -> None:
    conn.execute(
        """
        INSERT INTO llm_usage (usage_date, calls_made) VALUES (?, 1)
        ON CONFLICT(usage_date) DO UPDATE SET calls_made = calls_made + 1
        """,
        (today,),
    )
