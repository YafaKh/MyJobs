"""Workable public job board widget API adapter.

https://apply.workable.com/api/v1/widget/accounts/{account}?details=true
"""

import httpx
from bs4 import BeautifulSoup

API_URL = "https://apply.workable.com/api/v1/widget/accounts/{account}"


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL.format(account=identifier), params={"details": "true"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        description = BeautifulSoup(j.get("description") or "", "html.parser").get_text("\n").strip()
        jobs.append(
            {
                "external_id": j.get("shortcode") or j.get("url") or "",
                "title": (j.get("title") or "").strip(),
                "company": company_name,
                "url": j.get("url") or "",
                "description_raw": description,
                "posted_at": j.get("published_on"),
            }
        )
    return jobs
