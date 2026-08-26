"""Builds the extraction prompt: schema instructions, the user's eligibility
rules, recent corrections as few-shot guidance, and the job posting text.
"""

SCHEMA_INSTRUCTIONS = """You extract structured fields from a job posting for someone deciding whether \
they are eligible to apply. Read the posting and respond with ONLY a single JSON object \
(no markdown fences, no commentary) with exactly these keys:

- location_requirement: string, e.g. "United States", "Anywhere", "MENA" - the location or region the posting requires or names, or "none" if not stated
- work_authorization: string describing what work authorization is required, or "none" if not stated
- arrangement: one of "remote", "hybrid", "onsite"
- sponsorship: true, false, or "unknown" - whether the employer offers visa/work sponsorship
- timezone_overlap: string, e.g. "EST overlap required", or "none" if not stated
- eligible_for_me: true or false - see eligibility rules below
- reason: one sentence explaining the eligible_for_me verdict
"""


def _eligibility_rules_block(eligibility: dict) -> str:
    regions = ", ".join(eligibility["eligible_regions"])
    timezones = ", ".join(eligibility["eligible_timezones"])
    blocked = ", ".join(eligibility["blocked_requirements"])
    return f"""The candidate is based in Palestine. Determine eligible_for_me using these rules:

- ELIGIBLE if the posting is local to Palestine, or is remote/open to any of these regions: {regions}.
- ELIGIBLE if the posting only names a timezone requirement (no region) and that timezone is one of: {timezones}.
- NOT ELIGIBLE if the posting requires any of: {blocked}.
- If the posting requires a region or timezone that overlaps none of the above and isn't Palestine, NOT ELIGIBLE.
- If nothing about location/authorization is stated at all, ELIGIBLE (no stated blocker).
"""


def _corrections_block(corrections: list[dict]) -> str:
    if not corrections:
        return ""
    lines = ["Corrections from past extraction mistakes - apply this judgment:"]
    for c in corrections:
        lines.append(
            f'- For a posting like: "{c["text_snippet"]}" - '
            f'the field "{c["field_name"]}" should be "{c["right_value"]}", not "{c["wrong_value"]}".'
        )
    return "\n".join(lines) + "\n"


def build_prompt(text: str, config: dict, corrections: list[dict]) -> str:
    parts = [
        SCHEMA_INSTRUCTIONS,
        _eligibility_rules_block(config["eligibility"]),
        _corrections_block(corrections),
        f"Job posting:\n{text}",
    ]
    return "\n".join(p for p in parts if p)
