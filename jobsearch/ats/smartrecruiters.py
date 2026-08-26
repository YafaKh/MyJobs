"""SmartRecruiters public postings API adapter.

Two-step: list postings, then fetch each posting's detail for description
text and the public posting URL (not present in the list response).

https://api.smartrecruiters.com/v1/companies/{company}/postings
https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}
"""

import httpx
from bs4 import BeautifulSoup

LIST_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
DETAIL_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}"
PAGE_LIMIT = 100
DESCRIPTION_SECTIONS = ("jobDescription", "qualifications", "additionalInformation")


def _list_postings(identifier: str, client: httpx.Client) -> list[dict]:
    postings = []
    offset = 0
    while True:
        resp = client.get(
            LIST_URL.format(company=identifier),
            params={"limit": PAGE_LIMIT, "offset": offset},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        page = data.get("content", [])
        postings.extend(page)
        offset += len(page)
        if offset >= data.get("totalFound", 0) or not page:
            break
    return postings


def _description(detail: dict) -> str:
    sections = detail.get("jobAd", {}).get("sections", {})
    parts = [sections.get(key, {}).get("text", "") for key in DESCRIPTION_SECTIONS]
    html_blob = "\n".join(p for p in parts if p)
    return BeautifulSoup(html_blob, "html.parser").get_text("\n").strip()


def fetch_jobs(identifier: str, company_name: str, client: httpx.Client) -> list[dict]:
    jobs = []
    for item in _list_postings(identifier, client):
        posting_id = item["id"]
        detail_resp = client.get(
            DETAIL_URL.format(company=identifier, posting_id=posting_id), timeout=20
        )
        if detail_resp.status_code != 200:
            continue
        detail = detail_resp.json()
        jobs.append(
            {
                "external_id": str(posting_id),
                "title": (item.get("name") or "").strip(),
                "company": company_name,
                "url": detail.get("postingUrl") or "",
                "description_raw": _description(detail),
                "posted_at": (item.get("releasedDate") or "")[:10] or None,
            }
        )
    return jobs
