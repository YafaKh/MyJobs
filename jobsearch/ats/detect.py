"""Detect which ATS a company's careers page uses.

Tries a fast URL-pattern match first (covers the common case where the
careers_url IS the ATS-hosted board). Falls back to fetching the page and
scanning its HTML for embedded links to a known ATS, which covers companies
that put an ATS-hosted board behind their own custom domain.
"""

import re

import httpx

# (ats_type, pattern) - pattern's first group is the identifier the adapter needs.
PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([\w-]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([\w-]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([\w-]+)")),
    ("workable", re.compile(r"apply\.workable\.com/([\w-]+)")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)")),
    ("recruitee", re.compile(r"([\w-]+)\.recruitee\.com")),
]


def detect_from_text(text: str) -> tuple[str, str] | None:
    for ats_type, pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            return ats_type, match.group(1)
    return None


def detect_ats(careers_url: str, client: httpx.Client) -> tuple[str, str | None]:
    direct = detect_from_text(careers_url)
    if direct:
        return direct

    try:
        resp = client.get(careers_url, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return "generic_html", None

    from_html = detect_from_text(resp.text)
    if from_html:
        return from_html

    return "generic_html", None
