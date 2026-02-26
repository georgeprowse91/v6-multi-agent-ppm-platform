"""Assistant / suggestion routes (from legacy_main.py)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from routes._deps import (
    _demo_mode_enabled,
    _load_demo_assistant_payload,
    _load_demo_conversation_payload,
    _random_token_hex,
    _require_session,
    _resolve_llm_selection,
    _tenant_id_from_request,
    evaluate_prompt,
    get_methodology_map,
    logger,
    workspace_state_store,
    workflow_definition_store,
)
from routes._deps import LLMGateway, LLMProviderError, build_forward_headers, httpx
from routes._deps import _orchestrator_client

# Helpers used only in assistant
from routes._deps import _load_projects, _approval_payload
from routes._models import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantSendRequest,
    AssistantSuggestion,
    AssistantSuggestionRequest,
    AssistantSuggestionResponse,
    DemoConversationMessage,
    DemoConversationResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assistant_context(tenant_id: str, project_id: str | None, correlation_id: str) -> dict[str, Any]:
    return {"tenant_id": tenant_id, "project_id": project_id, "correlation_id": correlation_id}


def _fallback_suggestions(payload: AssistantSuggestionRequest, state: Any, methodology_map: dict[str, Any]) -> list[AssistantSuggestion]:
    suggestions: list[AssistantSuggestion] = []
    if payload.activity_status == "not_started":
        suggestions.append(AssistantSuggestion(id="sug-start", label="Begin this activity", category="workflow", priority="high", action_type="navigate", payload={"target": "canvas"}))
    if payload.incomplete_prerequisites:
        for prereq in payload.incomplete_prerequisites[:3]:
            suggestions.append(AssistantSuggestion(id=f"sug-prereq-{prereq.activity_id}", label=f"Complete prerequisite: {prereq.activity_name}", category="prerequisite", priority="high", action_type="navigate", payload={"target_activity_id": prereq.activity_id, "stage_id": prereq.stage_id}))
    if not suggestions:
        suggestions.append(AssistantSuggestion(id="sug-default", label="Review workspace status", category="general", priority="medium", action_type="navigate", payload={"target": "dashboard"}))
    return suggestions


async def _llm_suggestions(payload: AssistantSuggestionRequest, context: dict[str, Any], methodology_map: dict[str, Any], *, tenant_id: str, user_id: str | None) -> list[AssistantSuggestion]:
    provider, model_id = (
        (payload.provider, payload.model_id)
        if payload.provider and payload.model_id
        else _resolve_llm_selection(tenant_id, payload.project_id, user_id)
    )
    llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
    system_prompt = "You are a PMO assistant. Return a JSON array of suggestion objects with keys: id, label, category, priority, action_type, payload."
    user_prompt = json.dumps({"context": context, "activity_id": payload.activity_id, "stage_id": payload.stage_id, "activity_name": payload.activity_name, "incomplete_prerequisites": [p.model_dump() for p in payload.incomplete_prerequisites]})
    response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt, provider=provider, model_id=model_id, json_mode=True)
    data = json.loads(response.content)
    if isinstance(data, list):
        return [AssistantSuggestion.model_validate(item) for item in data[:10]]
    return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/assistant/send")
async def send_assistant_message(payload: AssistantSendRequest, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    prompt_result = evaluate_prompt(payload.message)
    if prompt_result.decision == "deny":
        logger.warning("assistant_prompt_blocked", extra={"tenant_id": tenant_id, "reasons": prompt_result.reasons})
        return JSONResponse(status_code=400, content={"detail": "Prompt rejected due to unsafe content.", "reasons": prompt_result.reasons})
    correlation_id = f"corr-{_random_token_hex(8)}"
    context = _assistant_context(tenant_id, payload.project_id, correlation_id)
    headers = build_forward_headers(request, session)
    headers["X-Tenant-ID"] = tenant_id
    prompt_payload = None
    if payload.prompt_id or payload.prompt_description or payload.prompt_tags:
        prompt_payload = {"id": payload.prompt_id, "description": payload.prompt_description, "tags": payload.prompt_tags}
    try:
        response = await _orchestrator_client().send_query(query=prompt_result.sanitized_text, context=context, headers=headers, prompt=prompt_payload)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"detail": "upstream timeout", "correlation_id": correlation_id})
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            return JSONResponse(status_code=response.status_code, content={"detail": response.text, "correlation_id": correlation_id})
        if isinstance(detail, dict):
            detail["correlation_id"] = correlation_id
            return JSONResponse(status_code=response.status_code, content=detail)
        return JSONResponse(status_code=response.status_code, content={"detail": detail, "correlation_id": correlation_id})
    try:
        response_payload: Any = response.json()
    except ValueError:
        response_payload = response.text
    warnings = prompt_result.reasons if prompt_result.decision == "allow_with_warning" else []
    return JSONResponse(status_code=200, content={"tenant_id": tenant_id, "project_id": payload.project_id, "correlation_id": correlation_id, "response": response_payload, "prompt_safety_warning": warnings, "received_at": datetime.now(timezone.utc).isoformat()})


@router.post("/api/assistant", response_model=AssistantQueryResponse)
async def assistant_query(payload: AssistantQueryRequest, request: Request) -> AssistantQueryResponse:
    _require_session(request)
    query_text = payload.query.strip()
    if _demo_mode_enabled():
        demo_payload = _load_demo_assistant_payload("assistant-responses.json")
        if demo_payload:
            lowered = query_text.lower()
            for entry in demo_payload.get("responses", []):
                matches = entry.get("match") or []
                if any(match.lower() in lowered for match in matches):
                    return AssistantQueryResponse(query=query_text, summary=str(entry.get("summary", "")), items=list(entry.get("items") or []))
            default_payload = demo_payload.get("default", {})
            return AssistantQueryResponse(query=query_text, summary=str(default_payload.get("summary", "")), items=list(default_payload.get("items") or []))
    if payload.project_id:
        session = _require_session(request)
        tenant_id = _tenant_id_from_request(request, session)
        if tenant_id:
            provider, model_id = ((payload.provider, payload.model_id) if payload.provider and payload.model_id else _resolve_llm_selection(tenant_id, payload.project_id, session.get("subject")))
            llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
            try:
                system_prompt = "You are a PMO portfolio assistant. Return concise JSON with keys summary and items (array of strings)."
                user_prompt = json.dumps({"query": query_text, "project_id": payload.project_id})
                response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt, provider=provider, model_id=model_id, json_mode=True)
                data = json.loads(response.content)
                if isinstance(data, dict):
                    return AssistantQueryResponse(query=query_text, summary=str(data.get("summary", "")), items=[str(item) for item in data.get("items", []) if isinstance(item, (str, int, float))])
            except Exception:
                logger.exception("LLM assistant query failed for query: %s", query_text[:100])
    lowered = query_text.lower()
    if "risk" in lowered:
        approvals = _approval_payload().get("items", [])
        items = [f"{i.get('project', 'Unknown')} \u2014 {i.get('risk', 'Risk')} ({i.get('title', '')})" for i in approvals if i.get("project")]
        return AssistantQueryResponse(query=query_text, summary="Projects with elevated risk exposure:", items=items)
    if "workflow" in lowered or "automation" in lowered:
        workflows = workflow_definition_store.list_summaries()
        items = [f"{w.name} \u2014 {w.description or 'Workflow definition'}" for w in workflows]
        return AssistantQueryResponse(query=query_text, summary="Workflow health summary:", items=items)
    if "approval" in lowered:
        approvals = _approval_payload().get("items", [])
        items = [i.get("title", "Approval review") for i in approvals]
        return AssistantQueryResponse(query=query_text, summary="Pending approvals to review:", items=items)
    projects = _load_projects()
    summary = f"Tracking {len(projects)} active projects. Ask about risks, approvals, or workflows for details."
    return AssistantQueryResponse(query=query_text, summary=summary, items=[])


@router.get("/api/assistant/demo-conversations/{scenario}", response_model=DemoConversationResponse)
async def assistant_demo_conversation(scenario: str, request: Request) -> DemoConversationResponse:
    _require_session(request)
    safe_scenario = (scenario or "").strip().lower()
    if safe_scenario not in {"project_intake", "resource_request", "vendor_procurement"}:
        raise HTTPException(status_code=404, detail="Scenario not found")
    messages = _load_demo_conversation_payload(f"{safe_scenario}.json")
    if messages is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return DemoConversationResponse(scenario=safe_scenario, messages=[DemoConversationMessage(**e) for e in messages])


@router.post("/api/assistant/suggestions", response_model=AssistantSuggestionResponse)
async def generate_assistant_suggestions(payload: AssistantSuggestionRequest, request: Request) -> AssistantSuggestionResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    state = workspace_state_store.get_or_create(tenant_id, payload.project_id)
    methodology_map = get_methodology_map(state.methodology)
    correlation_id = f"corr-{_random_token_hex(8)}"
    context = _assistant_context(tenant_id, payload.project_id, correlation_id)
    context.update({"activity_id": payload.activity_id, "stage_id": payload.stage_id, "activity_name": payload.activity_name, "stage_name": payload.stage_name, "activity_status": payload.activity_status, "canvas_type": payload.canvas_type, "incomplete_prerequisites": [p.model_dump() for p in payload.incomplete_prerequisites]})
    suggestions: list[AssistantSuggestion] = []
    generated_by = "heuristic"
    try:
        suggestions = await _llm_suggestions(payload, context, methodology_map, tenant_id=tenant_id, user_id=session.get("subject"))
        if suggestions:
            generated_by = "llm"
    except (LLMProviderError, ValueError):
        suggestions = []
    if not suggestions:
        suggestions = _fallback_suggestions(payload, state, methodology_map)
    return AssistantSuggestionResponse(context=context, suggestions=suggestions, generated_by=generated_by)
