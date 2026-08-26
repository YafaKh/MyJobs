"""Jobicy free remote jobs feed.

https://jobicy.com/api/v2/remote-jobs
"""

import httpx
from bs4 import BeautifulSoup

API_URL = "https://jobicy.com/api/v2/remote-jobs"


def _description(j: dict) -> str:
    geo = j.get("jobGeo") or "none stated"
    body = BeautifulSoup(j.get("jobDescription") or "", "html.parser").get_text("\n").strip()
    return f"Location: {geo}\n\n{body}"


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        jobs.append(
            {
                "external_id": str(j.get("id")),
                "title": (j.get("jobTitle") or "").strip(),
                "company": j.get("companyName") or "",
                "url": j.get("url") or "",
                "description_raw": _description(j),
                "posted_at": (j.get("pubDate") or "")[:10] or None,
            }
        )
    return jobs
