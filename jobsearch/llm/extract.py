"""extract_fields(text, config, corrections) -> dict

Provider-agnostic: which API gets called is picked from config["llm"]["provider"],
so switching providers is a one-line change to config.yaml, not to this code.
"""

import json
import os
import re

from jobsearch.llm import claude, gemini, prompts

PROVIDER_CALLS = {
    "gemini": lambda prompt, config: gemini.call(prompt, os.environ["GEMINI_API_KEY"], config["llm"]["model"]),
    "claude": lambda prompt, config: claude.call(prompt, os.environ["ANTHROPIC_API_KEY"], config["llm"]["claude_model"]),
}


def _parse_json_response(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw[:200]!r}")
    return json.loads(match.group(0))


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _normalize_sponsorship(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower() if value is not None else "unknown"


def _normalize(result: dict) -> dict:
    result = dict(result)
    result["eligible_for_me"] = _to_bool(result.get("eligible_for_me"))
    result["sponsorship"] = _normalize_sponsorship(result.get("sponsorship"))
    return result


def extract_fields(text: str, config: dict, corrections: list[dict]) -> dict:
    provider = config["llm"]["provider"]
    if provider not in PROVIDER_CALLS:
        raise ValueError(f"Unknown llm provider: {provider!r} (expected 'gemini' or 'claude')")

    prompt = prompts.build_prompt(text, config, corrections)
    raw = PROVIDER_CALLS[provider](prompt, config)
    return _normalize(_parse_json_response(raw))
