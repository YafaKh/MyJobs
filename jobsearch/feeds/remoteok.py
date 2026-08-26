"""RemoteOK free jobs feed.

Per RemoteOK's API terms: link back to the job's RemoteOK URL (which we
already do via the job's own url field) and credit RemoteOK as the source,
or they suspend API access.

https://remoteok.com/api
"""

import httpx
from bs4 import BeautifulSoup

API_URL = "https://remoteok.com/api"


def _description(j: dict) -> str:
    location = j.get("location") or "none stated"
    body = BeautifulSoup(j.get("description") or "", "html.parser").get_text("\n").strip()
    return f"Location: {location}\n\n{body}"


def fetch_jobs(client: httpx.Client) -> list[dict]:
    resp = client.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data:
        if "id" not in j:
            continue  # the first element is a metadata/legal-notice blob, not a job
        jobs.append(
            {
                "external_id": str(j["id"]),
                "title": (j.get("position") or "").strip(),
                "company": j.get("company") or "",
                "url": j.get("url") or "",
                "description_raw": _description(j),
                "posted_at": (j.get("date") or "")[:10] or None,
            }
        )
    return jobs
