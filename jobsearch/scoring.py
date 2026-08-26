"""Scores jobs that survive the eligibility hard-filter, for sorting only.

Title match and keyword hits count toward the score; more recent postings
score higher. This never affects eligibility - only display order.
"""

from datetime import date, datetime

TITLE_MATCH_POINTS = 10
KEYWORD_POINTS_PER_HIT = 3
MAX_KEYWORD_HITS_COUNTED = 5
RECENCY_WINDOW_DAYS = 14


def score_job(title_matched: bool, keyword_hits: int, posted_at: str | None, first_seen_at: str | None) -> float:
    score = 0.0
    if title_matched:
        score += TITLE_MATCH_POINTS
    score += min(keyword_hits, MAX_KEYWORD_HITS_COUNTED) * KEYWORD_POINTS_PER_HIT

    reference_date = posted_at or first_seen_at
    if reference_date:
        try:
            days_old = (date.today() - datetime.fromisoformat(reference_date[:10]).date()).days
            score += max(0, RECENCY_WINDOW_DAYS - days_old)
        except ValueError:
            pass

    return score
