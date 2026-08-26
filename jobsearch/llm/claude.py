"""Claude Messages API REST call, used as a fallback if Gemini turns out to
be unreachable. No SDK, same reasoning as jobsearch/llm/gemini.py.
"""

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def call(prompt: str, api_key: str, model: str) -> str:
    resp = httpx.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]
