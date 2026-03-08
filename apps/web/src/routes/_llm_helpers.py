"""Shared LLM helpers for feature routes.

Production-grade wrapper around LLMGateway with:
- Retry with exponential backoff for transient failures
- Structured JSON completion with schema validation
- Timeout enforcement
- Semantic caching (in-process + optional Redis)
- Graceful degradation when no provider configured
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger("routes._llm_helpers")

# Lazy-init singleton — avoids import-time failures if deps are missing.
_gateway_instance = None

# Configuration from environment
_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "15"))
_LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
_LLM_BACKOFF_BASE = float(os.getenv("LLM_BACKOFF_BASE", "0.5"))
_LLM_CACHE_TTL = int(os.getenv("LLM_CACHE_TTL", "300"))


def _get_llm_gateway():
    """Return a shared LLMGateway instance, created on first call."""
    global _gateway_instance
    if _gateway_instance is not None:
        return _gateway_instance

    try:
        from llm.client import LLMGateway

        provider = os.getenv("LLM_PROVIDER", "mock")
        config: dict[str, Any] = {
            "semantic_cache": {"ttl_seconds": _LLM_CACHE_TTL},
            "retry_policy": {
                "max_attempts": _LLM_MAX_RETRIES,
                "initial_backoff_s": _LLM_BACKOFF_BASE,
            },
        }
        if provider == "mock":
            config["demo_mode"] = True
        _gateway_instance = LLMGateway(provider=provider, config=config)
        return _gateway_instance
    except Exception as exc:
        logger.warning("LLMGateway init failed, using fallback: %s", exc)
        return None


async def llm_complete(
    system_prompt: str,
    user_prompt: str,
    *,
    tenant_id: str = "default",
    json_mode: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> str:
    """Call the LLM and return the response content string.

    Features:
    - Timeout enforcement (default 15s, configurable via LLM_TIMEOUT env)
    - Retry with exponential backoff for transient errors
    - Graceful degradation: returns empty string on any failure
    """
    gateway = _get_llm_gateway()
    if gateway is None:
        return ""

    effective_timeout = timeout or _LLM_TIMEOUT
    last_error: Exception | None = None

    for attempt in range(_LLM_MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(
                gateway.complete(
                    system_prompt,
                    user_prompt,
                    tenant_id=tenant_id,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=effective_timeout,
            )
            return response.content
        except TimeoutError:
            last_error = TimeoutError(f"LLM call timed out after {effective_timeout}s")
            logger.warning(
                "llm_complete timeout (attempt %d/%d)", attempt + 1, _LLM_MAX_RETRIES + 1
            )
        except Exception as exc:
            last_error = exc
            # Check if retryable
            retryable = getattr(exc, "retryable", False)
            if not retryable or attempt >= _LLM_MAX_RETRIES:
                break
            logger.warning(
                "llm_complete transient error (attempt %d/%d): %s",
                attempt + 1,
                _LLM_MAX_RETRIES + 1,
                exc,
            )

        if attempt < _LLM_MAX_RETRIES:
            await asyncio.sleep(_LLM_BACKOFF_BASE * (2**attempt))

    logger.warning("llm_complete failed after %d attempts: %s", _LLM_MAX_RETRIES + 1, last_error)
    return ""


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM responses."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return cleaned


def _try_parse_json(text: str) -> dict[str, Any] | list | None:
    """Attempt to parse JSON, handling common LLM response quirks."""
    cleaned = _strip_markdown_fences(text)
    if not cleaned:
        return None

    # Try direct parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, (dict, list)):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON object/array within the text
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = cleaned.find(start_char)
        end = cleaned.rfind(end_char)
        if start >= 0 and end > start:
            try:
                result = json.loads(cleaned[start : end + 1])
                if isinstance(result, (dict, list)):
                    return result
            except json.JSONDecodeError:
                continue

    return None


async def llm_complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    tenant_id: str = "default",
    temperature: float | None = None,
    timeout: float | None = None,
    correction_attempts: int = 1,
) -> dict[str, Any] | list:
    """Call the LLM expecting a JSON response.

    Features:
    - Automatic markdown fence stripping
    - JSON extraction from mixed text/JSON responses
    - Optional self-correction: if first parse fails, sends error back to LLM
    - Returns parsed dict/list or empty dict on failure
    """
    raw = await llm_complete(
        system_prompt,
        user_prompt,
        tenant_id=tenant_id,
        json_mode=True,
        temperature=temperature,
        timeout=timeout,
    )
    if not raw:
        return {}

    result = _try_parse_json(raw)
    if result is not None:
        return result

    # Self-correction: ask LLM to fix its output
    for _ in range(correction_attempts):
        correction_prompt = (
            f"Your previous response was not valid JSON. "
            f"Here is what you returned:\n{raw[:500]}\n\n"
            f"Please return ONLY valid JSON, no markdown formatting or extra text."
        )
        raw = await llm_complete(
            system_prompt,
            correction_prompt,
            tenant_id=tenant_id,
            json_mode=True,
            temperature=0.0,
            timeout=timeout,
        )
        if raw:
            result = _try_parse_json(raw)
            if result is not None:
                return result

    logger.warning("llm_complete_json: could not parse response as JSON after correction attempts")
    return {}


async def llm_complete_structured(
    system_prompt: str,
    user_prompt: str,
    *,
    schema: dict[str, Any],
    tenant_id: str = "default",
    temperature: float | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Call LLM with JSON schema validation.

    Uses LLMGateway.complete_structured() when available for schema-aware
    generation with automatic correction. Falls back to llm_complete_json.
    """
    gateway = _get_llm_gateway()
    if gateway is None:
        return {}

    try:
        if hasattr(gateway, "complete_structured"):
            result = await asyncio.wait_for(
                gateway.complete_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    tenant_id=tenant_id,
                ),
                timeout=timeout or _LLM_TIMEOUT,
            )
            return result
    except Exception as exc:
        logger.debug("complete_structured unavailable, falling back: %s", exc)

    # Fallback to regular JSON completion
    return await llm_complete_json(
        system_prompt,
        user_prompt,
        tenant_id=tenant_id,
        temperature=temperature,
        timeout=timeout,
    )
