"""DB reads/writes for the dashboard: job search, star/hide, and corrections."""

import sqlite3

CORRECTABLE_FIELDS = {
    "location_requirement",
    "work_authorization",
    "arrangement",
    "sponsorship",
    "timezone_overlap",
    "eligible_for_me",
    "reason",
}


def list_jobs(conn: sqlite3.Connection, source_kind: str, q: str = "") -> list[sqlite3.Row]:
    sql = """
        SELECT * FROM jobs
        WHERE source_kind = ?
          AND hidden = 0
          AND (eligible_for_me IS NULL OR eligible_for_me = 1)
    """
    params: list = [source_kind]

    query = q.strip()
    if query:
        like = f"%{query}%"
        sql += " AND (title LIKE ? OR company LIKE ? OR description_raw LIKE ?)"
        params += [like, like, like]

    sql += " ORDER BY starred DESC, score DESC NULLS LAST, first_seen_at DESC"
    return conn.execute(sql, params).fetchall()


def get_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row:
    return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def toggle_star(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute("UPDATE jobs SET starred = 1 - starred WHERE id = ?", (job_id,))
    conn.commit()


def set_hidden(conn: sqlite3.Connection, job_id: int, hidden: bool) -> None:
    conn.execute("UPDATE jobs SET hidden = ? WHERE id = ?", (1 if hidden else 0, job_id))
    conn.commit()


def apply_correction(conn: sqlite3.Connection, job_id: int, field_name: str, right_value: str) -> None:
    if field_name not in CORRECTABLE_FIELDS:
        raise ValueError(f"Field not correctable: {field_name!r}")

    job = get_job(conn, job_id)
    wrong_value = job[field_name]
    description = job["description_raw"] or ""
    text_snippet = f"{job['title']} at {job['company']}: {description[:300]}"

    conn.execute(
        """
        INSERT INTO corrections (job_hash, text_snippet, field_name, wrong_value, right_value)
        VALUES (?, ?, ?, ?, ?)
        """,
        (job["job_hash"], text_snippet, field_name, str(wrong_value) if wrong_value is not None else None, right_value),
    )

    if field_name == "eligible_for_me":
        stored_value: str | int = 1 if right_value.strip().lower() in ("true", "1", "yes") else 0
    else:
        stored_value = right_value

    conn.execute(f"UPDATE jobs SET {field_name} = ? WHERE id = ?", (stored_value, job_id))
    conn.commit()


def list_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
