"""Copilot streaming endpoints — SSE-based real-time agent orchestration visibility.

Wires copilot queries to the real orchestrator, routing through Intent Router
and domain agents, streaming execution events back via SSE.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.runtime.src.execution_events import (
    ExecutionEvent,
    ExecutionEventRegistry,
    ExecutionEventType,
)
from routes._llm_helpers import llm_complete, llm_complete_json

logger = logging.getLogger("routes.copilot_stream")
router = APIRouter(tags=["copilot"])

# Agent catalog for routing — maps intent categories to agent IDs
_INTENT_AGENT_MAP: dict[str, list[str]] = {
    "risk": ["risk-management"],
    "schedule": ["schedule-planning"],
    "budget": ["financial-management"],
    "resource": ["resource-management"],
    "portfolio": ["portfolio-optimisation"],
    "demand": ["demand-intake"],
    "vendor": ["vendor-procurement"],
    "compliance": ["compliance-governance"],
    "quality": ["quality-management"],
    "general": ["analytics-insights"],
}

_INTENT_ROUTER_PROMPT = """You are an intent classifier for a Project Portfolio Management system.
Classify the user query into one or more of these categories:
risk, schedule, budget, resource, portfolio, demand, vendor, compliance, quality, general

Return JSON: {"intents": ["category1", "category2"], "reasoning": "brief explanation"}
Only return the JSON, no other text."""

_AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    "risk-management": "You are a Risk Management agent. Analyze project risks, assess probability and impact, and recommend mitigations. Be specific and actionable.",
    "schedule-planning": "You are a Schedule Planning agent. Analyze project timelines, critical paths, and schedule health. Identify delays and recommend corrective actions.",
    "financial-management": "You are a Financial Management agent. Analyze budgets, cost performance, earned value metrics, and forecast financials.",
    "resource-management": "You are a Resource Management agent. Analyze resource allocation, capacity, utilization, and identify bottlenecks.",
    "portfolio-optimisation": "You are a Portfolio Optimization agent. Analyze portfolio health, strategic alignment, and recommend project prioritization.",
    "demand-intake": "You are a Demand Intake agent. Help classify, prioritize, and assess new project demands.",
    "vendor-procurement": "You are a Vendor Procurement agent. Analyze vendor performance, SLA compliance, and procurement decisions.",
    "compliance-governance": "You are a Compliance Governance agent. Assess regulatory compliance, audit readiness, and governance gaps.",
    "quality-management": "You are a Quality Management agent. Analyze quality metrics, defect trends, and recommend quality improvements.",
    "analytics-insights": "You are an Analytics Insights agent. Provide data-driven analysis and insights across the project portfolio.",
}


class CopilotQueryRequest(BaseModel):
    query: str
    context: dict[str, Any] = Field(default_factory=dict)


class CopilotQueryResponse(BaseModel):
    correlation_id: str
    status: str = "streaming"


async def _run_orchestration(
    correlation_id: str,
    query: str,
    context: dict[str, Any],
) -> None:
    """Background task: route query through agents and emit SSE events."""
    registry = ExecutionEventRegistry.get_instance()
    emitter = registry.get_emitter(correlation_id)
    if emitter is None:
        return

    tenant_id = context.get("tenant_id", "default")

    try:
        # Step 1: Intent classification via LLM
        await emitter.emit(ExecutionEvent(
            event_type=ExecutionEventType.agent_started,
            agent_id="intent-router",
            catalog_id="intent-router",
            data={"step": "classifying_intent", "query": query},
        ))

        intent_result = await llm_complete_json(
            _INTENT_ROUTER_PROMPT,
            query,
            tenant_id=tenant_id,
        )
        intents = intent_result.get("intents", ["general"])
        if not intents:
            intents = ["general"]

        await emitter.emit(ExecutionEvent(
            event_type=ExecutionEventType.agent_completed,
            agent_id="intent-router",
            catalog_id="intent-router",
            data={"intents": intents, "reasoning": intent_result.get("reasoning", "")},
            confidence_score=0.85,
        ))

        # Step 2: Route to domain agents based on classified intents
        aggregated_responses: list[dict[str, Any]] = []

        for intent in intents[:3]:  # Cap at 3 agents to avoid excessive latency
            agent_ids = _INTENT_AGENT_MAP.get(intent, ["analytics-insights"])
            for agent_id in agent_ids:
                await emitter.emit(ExecutionEvent(
                    event_type=ExecutionEventType.agent_started,
                    agent_id=agent_id,
                    catalog_id=agent_id,
                    data={"intent": intent},
                ))

                await emitter.emit(ExecutionEvent(
                    event_type=ExecutionEventType.agent_thinking,
                    agent_id=agent_id,
                    catalog_id=agent_id,
                    data={"status": "analyzing query and portfolio data"},
                ))

                # Real LLM call per agent
                system_prompt = _AGENT_SYSTEM_PROMPTS.get(
                    agent_id,
                    "You are a PPM assistant. Provide helpful analysis.",
                )
                agent_response = await llm_complete(
                    system_prompt,
                    f"User query: {query}\nContext: {json.dumps(context)}",
                    tenant_id=tenant_id,
                    temperature=0.3,
                )

                if not agent_response:
                    agent_response = f"[{agent_id}] Analysis complete. No LLM provider configured — enable one via LLM_PROVIDER env var for full AI responses."

                await emitter.emit(ExecutionEvent(
                    event_type=ExecutionEventType.agent_intermediate,
                    agent_id=agent_id,
                    catalog_id=agent_id,
                    data={"partial_response": agent_response[:200]},
                ))

                aggregated_responses.append({
                    "agent_id": agent_id,
                    "intent": intent,
                    "response": agent_response,
                })

                await emitter.emit(ExecutionEvent(
                    event_type=ExecutionEventType.agent_completed,
                    agent_id=agent_id,
                    catalog_id=agent_id,
                    data={"response": agent_response},
                    confidence_score=0.8,
                ))

        # Step 3: Response aggregation
        combined = "\n\n".join(
            f"**{r['agent_id']}** ({r['intent']}):\n{r['response']}"
            for r in aggregated_responses
        )

        await emitter.emit(ExecutionEvent(
            event_type=ExecutionEventType.orchestration_completed,
            data={
                "final_response": combined,
                "agents_invoked": [r["agent_id"] for r in aggregated_responses],
                "intents": intents,
            },
        ))

    except Exception as exc:
        logger.exception("Orchestration failed for %s", correlation_id)
        await emitter.emit(ExecutionEvent(
            event_type=ExecutionEventType.agent_error,
            agent_id="orchestrator",
            data={"error": str(exc)},
        ))
        await emitter.emit(ExecutionEvent(
            event_type=ExecutionEventType.orchestration_completed,
            data={"error": str(exc)},
        ))


@router.post("/api/copilot/query")
async def copilot_query(request: CopilotQueryRequest) -> CopilotQueryResponse:
    """Accept a copilot query, start real agent orchestration, return correlation_id."""
    correlation_id = str(uuid.uuid4())
    registry = ExecutionEventRegistry.get_instance()
    emitter = registry.create_emitter(correlation_id)

    await emitter.emit(ExecutionEvent(
        event_type=ExecutionEventType.orchestration_started,
        data={"query": request.query},
    ))

    # Launch orchestration as a background task so SSE stream sees events
    asyncio.create_task(_run_orchestration(
        correlation_id, request.query, request.context,
    ))

    return CopilotQueryResponse(correlation_id=correlation_id)


@router.get("/api/copilot/stream/{correlation_id}")
async def copilot_stream(correlation_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint streaming execution events for a given correlation_id."""
    registry = ExecutionEventRegistry.get_instance()
    emitter = registry.get_emitter(correlation_id)

    async def event_generator():
        if emitter is None:
            yield _sse_format("error", {"message": "Unknown correlation_id"})
            return

        try:
            while True:
                if await request.is_disconnected():
                    break

                event = await emitter.get(timeout=15.0)
                if event is None:
                    yield _sse_format("heartbeat", {"ts": "keep-alive"})
                    continue

                yield _sse_format(
                    event.event_type.value,
                    event.model_dump(mode="json"),
                )

                if event.event_type == ExecutionEventType.orchestration_completed:
                    break
        finally:
            registry.remove_emitter(correlation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_format(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
