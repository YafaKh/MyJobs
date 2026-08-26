"""Cheap text prefilter: title/blocked-title/keyword matching, no LLM calls.

Case-insensitive substring matching against wanted_titles, blocked_titles,
and keywords in config.yaml.
"""


def _contains_any(haystack: str, needles: list[str]) -> bool:
    haystack_lower = haystack.lower()
    return any(needle.lower() in haystack_lower for needle in needles)


def _count_hits(haystack: str, needles: list[str]) -> int:
    haystack_lower = haystack.lower()
    return sum(1 for needle in needles if needle.lower() in haystack_lower)


def evaluate(title: str, description: str, config: dict) -> dict:
    keyword_hits = _count_hits(f"{title}\n{description}", config["keywords"])
    return {
        "blocked": _contains_any(title, config["blocked_titles"]),
        "title_matched": _contains_any(title, config["wanted_titles"]),
        "keyword_matched": keyword_hits > 0,
        "keyword_hits": keyword_hits,
    }
