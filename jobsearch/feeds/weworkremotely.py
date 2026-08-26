"""We Work Remotely RSS feed (programming category).

https://weworkremotely.com/categories/remote-programming-jobs.rss
"""

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def _split_title(raw_title: str) -> tuple[str, str]:
    # WWR titles are formatted "Company: Job Title".
    if ": " in raw_title:
        company, title = raw_title.split(": ", 1)
        return company.strip(), title.strip()
    return "", raw_title.strip()


def _posted_at(pub_date: str | None) -> str | None:
    if not pub_date:
        return None
    try:
        return parsedate_to_datetime(pub_date).date().isoformat()
    except (TypeError, ValueError):
        return None


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(FEED_URL, timeout=20)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.text)

    jobs = []
    for item in root.findall("./channel/item"):
        raw_title = (item.findtext("title") or "").strip()
        company, title = _split_title(raw_title)
        region = (item.findtext("region") or "").strip() or "none stated"
        description_html = item.findtext("description") or ""
        body = BeautifulSoup(description_html, "html.parser").get_text("\n").strip()

        jobs.append(
            {
                "external_id": item.findtext("guid"),
                "title": title,
                "company": company,
                "url": item.findtext("link") or "",
                "description_raw": f"Region: {region}\n\n{body}",
                "posted_at": _posted_at(item.findtext("pubDate")),
            }
        )
    return jobs
