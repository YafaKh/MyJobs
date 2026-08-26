"""Gemini generateContent REST call. No SDK - just httpx, like the rest of
this project's HTTP calls, so the actual request/response shape stays visible.
"""

import httpx

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def call(prompt: str, api_key: str, model: str) -> str:
    resp = httpx.post(
        API_URL.format(model=model),
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
