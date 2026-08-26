"""Fallback scraper for companies with no detected ATS.

Heuristic: fetch the careers page, find anchor tags that look like links to
individual job postings (same domain, href/text mentions job-ish words), then
fetch each candidate page for a description. Respects robots.txt on every
request and identifies itself with a distinct User-Agent.
"""

import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from protego import Protego

JOB_LINK_HINTS = ("job", "career", "position", "opening", "vacan", "role")
MIN_LINK_TEXT_LEN = 4
MAX_LINK_TEXT_LEN = 120
DESCRIPTION_CHAR_LIMIT = 8000


def _robots_allowed(url: str, user_agent: str, client: httpx.Client) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = client.get(robots_url, timeout=10)
    except httpx.HTTPError:
        return True  # can't check robots.txt -> assume allowed
    if resp.status_code != 200:
        return True  # no robots.txt -> assume allowed
    rp = Protego.parse(resp.text)
    return rp.can_fetch(url, user_agent)


def _looks_like_job_link(href: str, text: str) -> bool:
    text = text.strip()
    if not (MIN_LINK_TEXT_LEN <= len(text) <= MAX_LINK_TEXT_LEN):
        return False
    href_lower = href.lower()
    return any(hint in href_lower for hint in JOB_LINK_HINTS)


def _find_candidate_links(careers_url: str, html_text: str) -> dict[str, str]:
    soup = BeautifulSoup(html_text, "html.parser")
    domain = urlparse(careers_url).netloc
    careers_url_stripped = careers_url.rstrip("/")
    candidates: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not _looks_like_job_link(href, text):
            continue
        abs_url = urljoin(careers_url, href)
        if urlparse(abs_url).netloc != domain:
            continue
        if abs_url.rstrip("/") == careers_url_stripped:
            continue  # nav link back to the listing page itself, not a job
        candidates[abs_url] = text
    return candidates


def fetch_jobs(
    careers_url: str,
    company_name: str,
    client: httpx.Client,
    user_agent: str,
    max_detail_pages: int,
    request_delay_seconds: float,
) -> list[dict]:
    if not _robots_allowed(careers_url, user_agent, client):
        raise PermissionError(f"robots.txt disallows fetching {careers_url}")

    resp = client.get(careers_url, timeout=20)
    resp.raise_for_status()

    candidates = _find_candidate_links(careers_url, resp.text)

    jobs = []
    for url, title in list(candidates.items())[:max_detail_pages]:
        if not _robots_allowed(url, user_agent, client):
            continue
        try:
            detail_resp = client.get(url, timeout=20)
            detail_resp.raise_for_status()
        except httpx.HTTPError:
            continue

        description = BeautifulSoup(detail_resp.text, "html.parser").get_text("\n", strip=True)
        jobs.append(
            {
                "external_id": None,
                "title": title,
                "company": company_name,
                "url": url,
                "description_raw": description[:DESCRIPTION_CHAR_LIMIT],
                "posted_at": None,
            }
        )
        time.sleep(request_delay_seconds)

    return jobs
