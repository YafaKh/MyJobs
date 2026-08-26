"""Hacker News "Who is hiring?" thread, via the Algolia HN Search API.

HN posts are unstructured free text, not separate title/company fields, so
title/company here are a best-effort first-line guess - the full text is
kept in description_raw for the LLM to read either way.

https://hn.algolia.com/api/v1/search_by_date
https://hn.algolia.com/api/v1/items/{id}
"""

from datetime import date

import httpx
from bs4 import BeautifulSoup

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"
PERMALINK = "https://news.ycombinator.com/item?id={id}"


def _find_latest_thread_id(client: httpx.Client) -> str | None:
    resp = client.get(SEARCH_URL, params={"tags": "story,author_whoishiring", "query": "Who is hiring"}, timeout=20)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    for hit in hits:
        title = hit.get("title") or ""
        if title.startswith("Ask HN: Who is hiring?"):
            return hit["objectID"]
    return None


def _guess_title(flat_text: str) -> tuple[str, str]:
    # flat_text must be space-joined (not "\n"-joined): BeautifulSoup's get_text
    # inserts its separator at every tag boundary, including inline ones like
    # <a>, so a "\n"-joined first line breaks whenever it contains a link.
    prefix = flat_text[:300]
    for sep in (" | ", " - "):
        if sep in prefix:
            company, rest = prefix.split(sep, 1)
            title = rest.split(sep, 1)[0] if sep in rest else rest
            return company.strip()[:200], title.strip()[:200]
    return "", prefix.strip()[:200]


def fetch_jobs(client: httpx.Client) -> list[dict]:
    thread_id = _find_latest_thread_id(client)
    if not thread_id:
        return []

    resp = client.get(ITEM_URL.format(id=thread_id), timeout=30)
    resp.raise_for_status()
    thread = resp.json()

    jobs = []
    for comment in thread.get("children", []):
        if not comment.get("text") or comment.get("dead") or comment.get("deleted"):
            continue
        soup = BeautifulSoup(comment["text"], "html.parser")
        body = soup.get_text("\n").strip()
        company, title = _guess_title(soup.get_text(" ", strip=True))
        jobs.append(
            {
                "external_id": str(comment["id"]),
                "title": title or "HN hiring post",
                "company": company or "(see posting)",
                "url": PERMALINK.format(id=comment["id"]),
                "description_raw": body,
                "posted_at": (comment.get("created_at") or "")[:10] or date.today().isoformat(),
            }
        )
    return jobs
