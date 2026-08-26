"""Arbeitnow free job board feed.

https://www.arbeitnow.com/api/job-board-api
"""

import html as html_module
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def _description(j: dict) -> str:
    remote = "remote" if j.get("remote") else "not marked remote"
    location = j.get("location") or "none stated"
    body = BeautifulSoup(html_module.unescape(j.get("description") or ""), "html.parser").get_text("\n").strip()
    return f"Location: {location} ({remote})\n\n{body}"


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("data", []):
        posted_at = None
        if j.get("created_at"):
            posted_at = datetime.fromtimestamp(j["created_at"], tz=timezone.utc).date().isoformat()
        jobs.append(
            {
                "external_id": j.get("slug"),
                "title": (j.get("title") or "").strip(),
                "company": j.get("company_name") or "",
                "url": j.get("url") or "",
                "description_raw": _description(j),
                "posted_at": posted_at,
            }
        )
    return jobs
