"""Reads recent manual corrections to inject as few-shot guidance in the prompt.

Corrections are made from the dashboard (Phase 4) and stored in the
`corrections` table - that table is the single source of truth, so this
just reads the most recent rows rather than a separate file.
"""

import sqlite3


def recent_corrections(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT text_snippet, field_name, wrong_value, right_value
        FROM corrections
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
