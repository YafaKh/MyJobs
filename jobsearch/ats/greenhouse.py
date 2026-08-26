"""Greenhouse public job board API adapter.

https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
"""

import html as html_module

import httpx
from bs4 import BeautifulSoup

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL.format(token=identifier), params={"content": "true"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        # content is HTML with entities double-escaped (e.g. "&lt;p&gt;").
        raw_content = html_module.unescape(j.get("content") or "")
        description = BeautifulSoup(raw_content, "html.parser").get_text("\n").strip()
        jobs.append(
            {
                "external_id": str(j["id"]),
                "title": (j.get("title") or "").strip(),
                "company": company_name,
                "url": j.get("absolute_url") or "",
                "description_raw": description,
                "posted_at": (j.get("first_published") or "")[:10] or None,
            }
        )
    return jobs
