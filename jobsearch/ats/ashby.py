"""Ashby public job board API adapter.

https://api.ashbyhq.com/posting-api/job-board/{org}
"""

import httpx

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{org}"


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL.format(org=identifier), timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        jobs.append(
            {
                "external_id": j["id"],
                "title": (j.get("title") or "").strip(),
                "company": company_name,
                "url": j.get("jobUrl") or "",
                "description_raw": j.get("descriptionPlain") or "",
                "posted_at": (j.get("publishedAt") or "")[:10] or None,
            }
        )
    return jobs
