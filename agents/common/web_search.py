from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from llm.client import LLMGateway, LLMProviderError  # noqa: E402

logger = logging.getLogger(__name__)

SearchPurpose = Literal["risk", "vendor", "compliance", "scope", "general"]

_PURPOSE_KEYWORDS: dict[SearchPurpose, list[str]] = {
    "risk": ["risk", "failure", "incident", "outage"],
    "vendor": ["vendor", "supplier", "performance", "financial health", "dispute"],
    "compliance": ["laws", "regulation", "standard", "legal update"],
    "scope": ["requirements", "best practices", "project scope"],
    "general": [],
}

_SUMMARY_PROMPTS: dict[SearchPurpose, str] = {
    "risk": (
        "You are a risk analyst. Summarize the external snippets into concise bullet points "
        "highlighting emerging risks, incidents, or warnings. Keep it under 6 bullets."
    ),
    "vendor": (
        "You are a procurement analyst. Summarize the snippets into concise bullet points about "
        "supplier performance, financial stability, disputes, or ratings. Keep it under 6 bullets."
    ),
    "compliance": (
        "You are a compliance analyst. Summarize the snippets into concise bullet points about "
        "new regulations, standards, or legal changes. Keep it under 6 bullets."
    ),
    "scope": (
        "You are a PMO analyst. Summarize the external research snippets into concise bullet points "
        "that can inform scope definition. Keep it under 6 bullets."
    ),
    "general": (
        "Summarize the external snippets into concise bullet points. Keep it under 6 bullets."
    ),
}


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


def build_search_query(
    context: str,
    purpose: SearchPurpose,
    extra_keywords: Iterable[str] | None = None,
) -> str:
    """Build a search query with purpose-specific keywords.

    Args:
        context: High-level, non-sensitive context for the query.
        purpose: The research purpose (risk, vendor, compliance, scope, general).
        extra_keywords: Optional extra keywords to append for tuning.

    Returns:
        A search query string with purpose-specific keywords prepended.
    """
    keywords = list(_PURPOSE_KEYWORDS.get(purpose, []))
    if extra_keywords:
        keywords.extend(str(item).strip() for item in extra_keywords if str(item).strip())
    cleaned_context = " ".join(str(context).split())
    prefix = " ".join(item for item in keywords if item)
    query = f"{prefix} {cleaned_context}".strip()
    return " ".join(query.split())


async def search_web(query: str, *, result_limit: int | None = None) -> list[str]:
    """Search the configured external web search API and return snippet strings.

    Args:
        query: Search query string (do not include confidential or personal data).
        result_limit: Optional max number of results (1-10).

    Returns:
        List of human-readable snippet strings including the source URL when available.
    """
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


async def summarize_snippets(
    snippets: list[str],
    *,
    llm_client: LLMGateway | None = None,
    purpose: SearchPurpose = "general",
) -> str:
    """Summarize web search snippets using the LLM.

    Args:
        snippets: List of snippet strings.
        llm_client: Optional LLM client to reuse.
        purpose: The research purpose to guide summarization.

    Returns:
        A bullet-point summary or a fallback concatenation of snippets.
    """
    if not snippets:
        return ""

    llm = llm_client or LLMGateway()
    system_prompt = _SUMMARY_PROMPTS.get(purpose, _SUMMARY_PROMPTS["general"])
    user_prompt = "\n".join(f"- {snippet}" for snippet in snippets)

    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        summary = response.content.strip()
        if summary:
            return summary
    except (LLMProviderError, ValueError) as exc:
        logger.warning("LLM summary failed", extra={"error": str(exc)})
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - defensive
        logger.warning("Unexpected summarization error", extra={"error": str(exc)})

    return "\n".join(snippets[:3])
