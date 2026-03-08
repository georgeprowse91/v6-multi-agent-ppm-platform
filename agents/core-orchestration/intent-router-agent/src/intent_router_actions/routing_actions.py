"""Intent routing action handlers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from intent_router_models import (
    IntentPrediction,
    IntentRouterLLMResponse,
    IntentRouterRequest,
    IntentRouterResponse,
    RoutingDecision,
)
from observability.tracing import get_trace_id
from prompt_registry import enforce_redaction

from agents.runtime.src.audit import build_audit_event, emit_audit_event

if TYPE_CHECKING:
    from intent_router_agent import IntentRouterAgent


async def process_query(
    agent: IntentRouterAgent,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Route a user query to appropriate domain agents."""
    request = IntentRouterRequest.model_validate(input_data)
    query = request.query
    context = request.context or {}
    tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
    correlation_id = (
        context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
    )

    agent.logger.info(
        "Classifying query",
        extra={"query": query, "tenant_id": tenant_id, "correlation_id": correlation_id},
    )

    llm_payload = {
        "request": {"text": query, "context": context},
    }
    if not agent.prompt_text:
        raise ValueError("Prompt registry not initialized")
    redacted_payload = enforce_redaction(llm_payload)
    prompt_templates = agent._extract_prompt_templates(agent.prompt_text)
    system_prompt = agent._render_prompt(prompt_templates["system"], redacted_payload)
    user_prompt = agent._render_prompt(prompt_templates["user"], redacted_payload)

    fallback_reason: str | None = None
    fallback_used = False

    llm_response = await agent.llm_client.complete(system_prompt, user_prompt)
    llm_data: IntentRouterLLMResponse | None = None
    try:
        llm_data = agent._parse_llm_response(llm_response.content)
        intents = agent._normalize_intents(llm_data.intents)
        if not intents:
            fallback_reason = "llm_low_confidence"
    except ValueError as exc:
        fallback_reason = "llm_parse_error"
        agent.logger.warning(
            "LLM response invalid, using fallback classifier",
            extra={"error": str(exc)},
        )

    if fallback_reason:
        fallback_used = True
        intents = await agent._classify_intent(query)
        parameters: dict[str, Any] = {}
        dependencies = None
    else:
        parameters = llm_data.parameters or {}
        dependencies = llm_data.dependencies

    if not parameters:
        parameters = await agent._extract_parameters(query, intents)
    agents = await agent._determine_agents(intents, dependencies)

    audit_event = build_audit_event(
        tenant_id=tenant_id,
        action="intent.classified",
        outcome="success",
        actor_id=agent.agent_id,
        actor_type="service",
        actor_roles=[],
        resource_id=query[:64] or "query",
        resource_type="intent_classification",
        metadata={
            "intents": intents,
            "routing": agents,
            "parameters": parameters,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
        trace_id=get_trace_id(),
        correlation_id=correlation_id,
    )
    emit_audit_event(audit_event)
    if fallback_used:
        fallback_audit = build_audit_event(
            tenant_id=tenant_id,
            action="intent.fallback",
            outcome="success",
            actor_id=agent.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=query[:64] or "query",
            resource_type="intent_classification",
            metadata={
                "fallback_reason": fallback_reason,
                "intents": intents,
            },
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(fallback_audit)

    response = IntentRouterResponse(
        intents=[IntentPrediction(**intent) for intent in intents],
        routing=[RoutingDecision(**agent_entry) for agent_entry in agents],
        parameters=parameters,
        query=query,
        context=context,
        prompt_version=agent.prompt_version,
    )
    return response.model_dump()
