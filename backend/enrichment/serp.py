"""SerpAPI client: rate-limited, one query at a time."""
from __future__ import annotations

import os
import time
from typing import Any

import requests


def serp_google(q: str, api_key: str | None = None) -> list[dict[str, Any]]:
    """
    Run a Google search via SerpAPI. Returns list of organic results:
    [{ "title", "snippet", "link", "position" }, ...]
    """
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        return []

    url = "https://serpapi.com/search"
    params = {"q": q, "api_key": key, "engine": "google", "num": 10}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        organic = data.get("organic_results") or []
        out = []
        for i, o in enumerate(organic):
            out.append({
                "title": o.get("title") or "",
                "snippet": o.get("snippet") or "",
                "link": o.get("link") or "",
                "position": i + 1,
            })
        return out
    except Exception:
        return []


def serp_google_with_delay(q: str, delay_seconds: float = 1.0) -> list[dict[str, Any]]:
    """Run SerpAPI then sleep to respect rate limit."""
    results = serp_google(q)
    time.sleep(delay_seconds)
    return results
