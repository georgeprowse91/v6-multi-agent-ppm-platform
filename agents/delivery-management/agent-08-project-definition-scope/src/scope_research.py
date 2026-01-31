from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from llm.client import LLMClient, LLMProviderError  # noqa: E402

logger = logging.getLogger(__name__)


def _merge_unique(base: Iterable[str], updates: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in list(base) + list(updates):
        cleaned = str(item).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        merged.append(cleaned)
    return merged


def _coerce_scope(value: Any, fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return fallback
    return {
        "in_scope": _merge_unique(fallback.get("in_scope", []), value.get("in_scope", [])),
        "out_of_scope": _merge_unique(
            fallback.get("out_of_scope", []), value.get("out_of_scope", [])
        ),
        "deliverables": _merge_unique(
            fallback.get("deliverables", []), value.get("deliverables", [])
        ),
    }


async def summarize_snippets(snippets: list[str], llm_client: LLMClient | None = None) -> str:
    if not snippets:
        return ""

    llm = llm_client or LLMClient()
    system_prompt = (
        "You are a PMO analyst. Summarize the external research snippets into concise "
        "bullet points that can inform scope definition. Keep it under 6 bullets."  # noqa: E501
    )
    user_prompt = "\n".join(f"- {snippet}" for snippet in snippets)

    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        summary = response.content.strip()
        if summary:
            return summary
    except (LLMProviderError, ValueError) as exc:
        logger.warning("LLM summary failed", extra={"error": str(exc)})
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Unexpected summarization error", extra={"error": str(exc)})

    return "\n".join(snippets[:3])


async def generate_scope_from_search(
    objective: str,
    snippets: list[str],
    template_scope: dict[str, list[str]],
    template_requirements: list[str],
    template_wbs: list[str],
    *,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    fallback = {
        "scope": template_scope,
        "requirements": template_requirements,
        "wbs": template_wbs,
        "summary": "",
    }

    if not snippets:
        return fallback

    llm = llm_client or LLMClient()
    summary = await summarize_snippets(snippets, llm_client=llm)

    system_prompt = (
        "You are a PMO scope analyst. Combine organizational templates with external insights "
        "to propose scope statements, requirements, and WBS items. "
        "Respond ONLY with JSON in the following format: "
        "{\"scope\": {\"in_scope\": [], \"out_of_scope\": [], \"deliverables\": []}, "
        "\"requirements\": [], \"wbs\": []}."
    )
    user_prompt = json.dumps(
        {
            "objective": objective,
            "template_scope": template_scope,
            "template_requirements": template_requirements,
            "template_wbs": template_wbs,
            "external_summary": summary,
            "snippets": snippets,
        },
        indent=2,
    )

    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = json.loads(response.content)
    except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("LLM scope generation failed", extra={"error": str(exc)})
        return {
            **fallback,
            "summary": summary,
        }

    scope = _coerce_scope(data.get("scope"), template_scope)
    requirements = _merge_unique(template_requirements, data.get("requirements", []))
    wbs = _merge_unique(template_wbs, data.get("wbs", []))

    return {
        "scope": scope,
        "requirements": requirements,
        "wbs": wbs,
        "summary": summary,
    }
