"""Runs the extraction agent over jobs that haven't been extracted yet.

For saved sources, every non-blocked job gets extracted (the point of a
saved source is to see everything a chosen company posts). For open web
jobs, only ones that pass the title/keyword prefilter get extracted, since
open web volume would otherwise burn the daily LLM quota.

One bad extraction never kills the run - it's logged and skipped like a
bad scrape source in Phase 2.
"""

import sqlite3
import time
from datetime import date

from jobsearch import prefilter, quota, scoring
from jobsearch.llm.corrections import recent_corrections
from jobsearch.llm.extract import extract_fields


def _select_candidates(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM jobs WHERE extracted_at IS NULL ORDER BY first_seen_at").fetchall()


def _mark_blocked(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute(
        """
        UPDATE jobs
        SET eligible_for_me = 0, eligibility_reason = ?, extracted_at = datetime('now')
        WHERE id = ?
        """,
        ("Title matches a blocked title in config.yaml", job_id),
    )


def _apply_extraction(conn: sqlite3.Connection, job_id: int, result: dict, score: float) -> None:
    conn.execute(
        """
        UPDATE jobs SET
            location_requirement = ?,
            work_authorization = ?,
            arrangement = ?,
            sponsorship = ?,
            timezone_overlap = ?,
            eligible_for_me = ?,
            eligibility_reason = ?,
            score = ?,
            extracted_at = datetime('now')
        WHERE id = ?
        """,
        (
            result.get("location_requirement"),
            result.get("work_authorization"),
            result.get("arrangement"),
            result.get("sponsorship"),
            result.get("timezone_overlap"),
            1 if result.get("eligible_for_me") else 0,
            result.get("reason"),
            score,
            job_id,
        ),
    )


def run(conn: sqlite3.Connection, config: dict) -> None:
    today = date.today().isoformat()
    daily_cap = config["llm"]["daily_quota_cap"]
    sleep_seconds = 60 / config["llm"]["requests_per_minute"]
    used = quota.get_today_usage(conn, today)

    corrections = recent_corrections(conn, config["llm"]["corrections_few_shot_count"])

    extracted = blocked_count = prefilter_skipped = failed = 0
    quota_exhausted = False

    for row in _select_candidates(conn):
        job = dict(row)
        flags = prefilter.evaluate(job["title"], job["description_raw"] or "", config)

        conn.execute(
            "UPDATE jobs SET title_matched = ?, keyword_matched = ? WHERE id = ?",
            (int(flags["title_matched"]), int(flags["keyword_matched"]), job["id"]),
        )

        if flags["blocked"]:
            _mark_blocked(conn, job["id"])
            blocked_count += 1
            conn.commit()
            continue

        needs_prefilter = job["source_kind"] != "saved"
        if needs_prefilter and not (flags["title_matched"] or flags["keyword_matched"]):
            prefilter_skipped += 1
            conn.commit()
            continue

        if used >= daily_cap:
            quota_exhausted = True
            conn.commit()
            break

        text = f"Title: {job['title']}\nCompany: {job['company']}\n\n{job['description_raw'] or ''}"
        try:
            result = extract_fields(text, config, corrections)
            score = scoring.score_job(flags["title_matched"], flags["keyword_hits"], job["posted_at"], job["first_seen_at"])
            _apply_extraction(conn, job["id"], result, score)
            used += 1
            extracted += 1
            quota.increment_usage(conn, today)
            print(f"[extracted] {job['company']} - {job['title']}: eligible={result.get('eligible_for_me')}")
        except Exception as e:
            failed += 1
            print(f"[fail] {job['company']} - {job['title']}: {e}")

        conn.commit()
        time.sleep(sleep_seconds)

    if quota_exhausted:
        print(f"Daily LLM quota cap ({daily_cap}) reached - remaining jobs left for next run.")
    print(
        f"Done. extracted={extracted} blocked={blocked_count} "
        f"prefilter_skipped={prefilter_skipped} failed={failed} quota_used_today={used}/{daily_cap}"
    )
