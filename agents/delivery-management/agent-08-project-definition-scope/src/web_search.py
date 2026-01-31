from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchRateLimiter:
    min_interval_s: float
    _last_call: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            remaining = self.min_interval_s - (now - self._last_call)
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_call = time.monotonic()


_rate_limiter = SearchRateLimiter(min_interval_s=float(os.getenv("SEARCH_API_MIN_INTERVAL", "1.0")))


def _is_secure_endpoint(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    return parsed.scheme == "https"


async def search_web(query: str, *, result_limit: int | None = None) -> list[str]:
    endpoint = os.getenv("SEARCH_API_ENDPOINT", "").strip()
    api_key = os.getenv("SEARCH_API_KEY", "").strip()
    if not endpoint or not api_key:
        logger.warning("Search API not configured; skipping external search")
        return []

    if not _is_secure_endpoint(endpoint):
        logger.error("Search API endpoint must use HTTPS")
        return []

    if result_limit is None:
        result_limit = int(os.getenv("SEARCH_RESULT_LIMIT", "5"))
    result_limit = max(1, min(result_limit, 10))

    await _rate_limiter.wait()

    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": result_limit, "textDecorations": False, "textFormat": "Raw"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Search API request failed", extra={"error": str(exc)})
        return []

    items = payload.get("webPages", {}).get("value", [])
    snippets: list[str] = []
    for item in items[:result_limit]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        url = str(item.get("url", "")).strip()
        if not name and not snippet:
            continue
        summary = " - ".join(part for part in (name, snippet) if part)
        if url:
            summary = f"{summary} ({url})"
        snippets.append(summary)

    return snippets
