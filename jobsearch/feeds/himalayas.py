"""Himalayas free jobs feed.

Per Himalayas' terms: linking back to the job's own Himalayas URL (which we
already do via applicationLink) and crediting Himalayas as the source is
required for personal use - no republishing elsewhere.

https://himalayas.app/jobs/api
"""

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

API_URL = "https://himalayas.app/jobs/api"


def _description(j: dict) -> str:
    locations = ", ".join(j.get("locationRestrictions") or []) or "none stated"
    timezones = ", ".join(str(t) for t in (j.get("timezoneRestrictions") or [])) or "none stated"
    body = BeautifulSoup(j.get("description") or "", "html.parser").get_text("\n").strip()
    return f"Location restrictions: {locations}\nTimezone restrictions (UTC offset): {timezones}\n\n{body}"


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        posted_at = None
        if j.get("pubDate"):
            posted_at = datetime.fromtimestamp(j["pubDate"], tz=timezone.utc).date().isoformat()
        jobs.append(
            {
                "external_id": j.get("guid") or j.get("applicationLink"),
                "title": (j.get("title") or "").strip(),
                "company": j.get("companyName") or "",
                "url": j.get("applicationLink") or j.get("guid") or "",
                "description_raw": _description(j),
                "posted_at": posted_at,
            }
        )
    return jobs
