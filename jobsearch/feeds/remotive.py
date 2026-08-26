"""Remotive free remote jobs feed.

Per Remotive's terms: link back and credit Remotive as source, and don't
poll more than ~4x/day - this project checks once a day, well within that.

https://remotive.com/api/remote-jobs
"""

import httpx
from bs4 import BeautifulSoup

API_URL = "https://remotive.com/api/remote-jobs"


def _description(j: dict) -> str:
    location = j.get("candidate_required_location") or "none stated"
    body = BeautifulSoup(j.get("description") or "", "html.parser").get_text("\n").strip()
    return f"Candidate required location: {location}\n\n{body}"


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        jobs.append(
            {
                "external_id": str(j.get("id")),
                "title": (j.get("title") or "").strip(),
                "company": j.get("company_name") or "",
                "url": j.get("url") or "",
                "description_raw": _description(j),
                "posted_at": (j.get("publication_date") or "")[:10] or None,
            }
        )
    return jobs
