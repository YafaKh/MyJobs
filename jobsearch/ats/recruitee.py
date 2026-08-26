"""Recruitee public offers API adapter.

https://{company}.recruitee.com/api/offers/
"""

import httpx
from bs4 import BeautifulSoup

API_URL = "https://{company}.recruitee.com/api/offers/"


def _description(j: dict) -> str:
    html_parts = [j.get("description") or "", j.get("requirements") or ""]
    return BeautifulSoup("\n".join(html_parts), "html.parser").get_text("\n").strip()


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL.format(company=identifier), timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("offers", []):
        jobs.append(
            {
                "external_id": str(j["id"]),
                "title": (j.get("title") or "").strip(),
                "company": company_name,
                "url": j.get("careers_url") or "",
                "description_raw": _description(j),
                "posted_at": (j.get("published_at") or "")[:10] or None,
            }
        )
    return jobs
