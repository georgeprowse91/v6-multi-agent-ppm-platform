"""Summarization utilities for lifecycle gate decisions."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


Summarizer = Callable[[dict[str, Any]], Awaitable[str] | str]


class CognitiveSummarizer:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def summarize_payload(self, payload: dict[str, Any]) -> str:
        if callable(self.client):
            result = self.client(payload)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        summarize = getattr(self.client, "summarize", None)
        if callable(summarize):
            result = summarize(payload)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        generate = getattr(self.client, "generate", None)
        if callable(generate):
            result = generate(payload)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        return ""


class GateSummarizer:
    def __init__(self, summarizer: Summarizer | None = None) -> None:
        self._summarizer = summarizer

    async def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._summarizer:
            return {
                "summary": self._rule_based_summary(payload),
                "provider": "heuristic",
            }
        result = self._summarizer(payload)
        if asyncio.iscoroutine(result):
            result = await result
        return {"summary": result, "provider": "custom"}

    def _rule_based_summary(self, payload: dict[str, Any]) -> str:
        gate = payload.get("gate_name", "gate")
        recommendation = payload.get("recommendation", "Review")
        readiness = payload.get("readiness_score")
        readiness_text = f" Readiness score: {readiness:.2f}." if readiness is not None else ""
        missing = payload.get("missing_criteria", [])
        missing_text = (
            f" Missing criteria: {', '.join(item.get('criterion') for item in missing)}."
            if missing
            else ""
        )
        return f"{gate} evaluation: {recommendation}.{readiness_text}{missing_text}"
