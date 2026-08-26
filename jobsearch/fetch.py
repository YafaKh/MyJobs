"""Fetch raw jobs for every active saved source and store them.

One bad source never kills the run: each source is fetched inside its own
try/except, and failures are recorded on the source's health columns instead
of raised.
"""

import hashlib
import sqlite3

import httpx

from jobsearch.ats import ashby, detect, generic_html, greenhouse, lever, recruitee, smartrecruiters, workable

ADAPTERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workable": workable.fetch_jobs,
    "recruitee": recruitee.fetch_jobs,
    "smartrecruiters": smartrecruiters.fetch_jobs,
}


def job_hash_for(ats_type: str, external_id: str | None, url: str) -> str:
    key = f"{ats_type}:{external_id}" if external_id else url
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def upsert_job(conn: sqlite3.Connection, source_id: int, source_kind: str, job_hash: str, raw: dict) -> None:
    conn.execute("INSERT OR IGNORE INTO seen_ledger (job_hash) VALUES (?)", (job_hash,))
    conn.execute(
        """
        INSERT INTO jobs (job_hash, source_id, source_kind, title, company, url, description_raw, posted_at)
        VALUES (:job_hash, :source_id, :source_kind, :title, :company, :url, :description_raw, :posted_at)
        ON CONFLICT(job_hash) DO UPDATE SET
            title = excluded.title,
            company = excluded.company,
            url = excluded.url,
            description_raw = excluded.description_raw,
            posted_at = excluded.posted_at
        """,
        {
            "job_hash": job_hash,
            "source_id": source_id,
            "source_kind": source_kind,
            "title": raw["title"],
            "company": raw["company"],
            "url": raw["url"],
            "description_raw": raw["description_raw"],
            "posted_at": raw.get("posted_at"),
        },
    )


def fetch_source(conn: sqlite3.Connection, client: httpx.Client, source: dict, scraping_config: dict) -> int:
    """Fetch, normalize, and store one source's jobs. Returns the job count. Raises on failure."""
    ats_type = source["ats_type"]
    identifier = source["ats_identifier"]

    if not ats_type:
        ats_type, identifier = detect.detect_ats(source["careers_url"], client)
        conn.execute(
            "UPDATE sources SET ats_type = ?, ats_identifier = ? WHERE id = ?",
            (ats_type, identifier, source["id"]),
        )

    if ats_type == "generic_html":
        raw_jobs = generic_html.fetch_jobs(
            source["careers_url"],
            source["name"],
            client,
            user_agent=scraping_config["user_agent"],
            max_detail_pages=scraping_config["generic_html_max_detail_pages"],
            request_delay_seconds=scraping_config["generic_html_request_delay_seconds"],
        )
    else:
        raw_jobs = ADAPTERS[ats_type](identifier, source["name"], client)

    for raw in raw_jobs:
        jhash = job_hash_for(ats_type, raw.get("external_id"), raw["url"])
        upsert_job(conn, source["id"], source["source_kind"], jhash, raw)

    return len(raw_jobs)


def run(conn: sqlite3.Connection, scraping_config: dict) -> None:
    client = httpx.Client(headers={"User-Agent": scraping_config["user_agent"]}, follow_redirects=True)
    sources = conn.execute("SELECT * FROM sources WHERE is_active = 1").fetchall()
    try:
        for source in sources:
            source = dict(source)
            try:
                count = fetch_source(conn, client, source, scraping_config)
                conn.execute(
                    """
                    UPDATE sources
                    SET last_checked_at = datetime('now'),
                        last_success_at = datetime('now'),
                        last_error = NULL,
                        consecutive_failures = 0
                    WHERE id = ?
                    """,
                    (source["id"],),
                )
                conn.commit()
                print(f"[ok] {source['name']}: {count} jobs")
            except Exception as e:
                conn.execute(
                    """
                    UPDATE sources
                    SET last_checked_at = datetime('now'),
                        last_error = ?,
                        consecutive_failures = consecutive_failures + 1
                    WHERE id = ?
                    """,
                    (str(e), source["id"]),
                )
                conn.commit()
                print(f"[fail] {source['name']}: {e}")
    finally:
        client.close()
