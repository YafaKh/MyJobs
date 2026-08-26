"""Lever public postings API adapter.

https://api.lever.co/v0/postings/{company}?mode=json
"""

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

API_URL = "https://api.lever.co/v0/postings/{company}"


def _full_description(j: dict) -> str:
    # Lever splits a posting into an intro (descriptionPlain), structured
    # bullet sections (lists, HTML only), and a closing section (additionalPlain).
    parts = [j.get("descriptionPlain") or ""]
    for item in j.get("lists") or []:
        header = item.get("text") or ""
        body = BeautifulSoup(item.get("content") or "", "html.parser").get_text("\n").strip()
        parts.append(f"{header}\n{body}")
    parts.append(j.get("additionalPlain") or "")
    return "\n\n".join(p for p in parts if p)


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL.format(company=identifier), params={"mode": "json"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data:
        posted_at = None
        created_at_ms = j.get("createdAt")
        if created_at_ms:
            posted_at = datetime.fromtimestamp(created_at_ms / 1000, tz=timezone.utc).date().isoformat()
        jobs.append(
            {
                "external_id": j["id"],
                "title": (j.get("text") or "").strip(),
                "company": company_name,
                "url": j.get("hostedUrl") or "",
                "description_raw": _full_description(j),
                "posted_at": posted_at,
            }
        )
    return jobs
