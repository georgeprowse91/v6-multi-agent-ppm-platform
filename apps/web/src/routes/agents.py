"""Agent gallery routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from routes._deps import (
    _is_agent_admin,
    _require_session,
    _tenant_id_from_request,
    agent_settings_store,
    load_agent_registry,
    load_methodology_node_runtime_registry,
    load_template_mappings,
    logger,
)
from routes._deps import AgentConfigUpdate, AgentProjectEntry
from routes._models import (
    AgentPreviewRunRequest,
    AgentPreviewRunResponse,
    AgentProfileResponse,
    AgentProfileTemplateMapping,
)
from routes.methodology import run_methodology_node_action

router = APIRouter()


@router.get("/api/agent-gallery/agents")
async def list_agent_registry(request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    logger.info("agent_gallery.registry.list", extra={"tenant_id": tenant_id, "project_id": None, "agent_id": None})
    return JSONResponse(status_code=200, content=[entry.model_dump() for entry in registry])


@router.get("/api/agent-gallery/agents/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_profile(agent_id: str, request: Request) -> AgentProfileResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    entry = next((c for c in registry if c.agent_id == agent_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Agent not found")
    mappings = load_template_mappings().templates
    runtime_registry = load_methodology_node_runtime_registry()
    template_rows: dict[str, AgentProfileTemplateMapping] = {}
    connector_rows: dict[tuple[str, str], dict[str, Any]] = {}
    methodology_nodes: set[tuple[str, str, str | None, str | None, str]] = set()
    run_modes: set[str] = set()
    for mapping in mappings:
        binding = mapping.agent_bindings
        lifecycle_events = [event for event in ("generate", "update", "review", "approve", "publish") if agent_id in getattr(binding, event)]
        if not lifecycle_events and agent_id not in binding.orchestration.produces_artifacts:
            continue
        template_rows[mapping.template_id] = AgentProfileTemplateMapping(
            template_id=mapping.template_id, template_name=mapping.name, lifecycle_events=lifecycle_events, run_modes=["dag", "demo-safe"],
            methodology_nodes=[{"methodology_id": n.methodology_id, "stage_id": n.stage_id, "activity_id": n.activity_id, "task_id": n.task_id} for n in mapping.methodology_bindings],
        )
        for endpoint in [*mapping.connector_binding.sources, *mapping.connector_binding.destinations]:
            key = (endpoint.connector_type, endpoint.system)
            connector_rows[key] = {"connector_type": endpoint.connector_type, "system": endpoint.system, "objects": endpoint.objects, "category": mapping.connector_binding.category}
    for rm in runtime_registry.mappings:
        workflow = rm.resolution.agent_workflow
        if agent_id not in workflow.agent_ids:
            continue
        methodology_nodes.add((rm.key.methodology_id, rm.key.stage_id, rm.key.activity_id, rm.key.task_id, rm.key.lifecycle_event))
        run_modes.add(workflow.mode)
    run_modes.add("demo-safe")
    logger.info("agent_gallery.profile.get", extra={"tenant_id": tenant_id, "project_id": None, "agent_id": agent_id})
    return AgentProfileResponse(
        agent_id=entry.agent_id, name=entry.name, purpose=entry.description,
        capabilities=[f"{entry.name} capability"], inputs=["workspace_context", "template_context", "user_input"], outputs=entry.outputs,
        templates_touched=list(template_rows.values()),
        connectors_used=sorted(connector_rows.values(), key=lambda i: f"{i['connector_type']}::{i['system']}"),
        methodology_nodes_supported=[{"methodology_id": m, "stage_id": s, "activity_id": a, "task_id": t, "lifecycle_event": e} for m, s, a, t, e in sorted(methodology_nodes)],
        run_modes=sorted(run_modes),
    )


@router.post("/api/agent-gallery/agents/{agent_id}/run-preview", response_model=AgentPreviewRunResponse)
async def run_agent_preview(agent_id: str, payload: AgentPreviewRunRequest, request: Request) -> AgentPreviewRunResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    if not any(e.agent_id == agent_id for e in registry):
        raise HTTPException(status_code=404, detail="Agent not found")
    runtime_registry = load_methodology_node_runtime_registry()
    matching = next((m for m in runtime_registry.mappings if agent_id in m.resolution.agent_workflow.agent_ids and m.key.lifecycle_event in {"generate", "update", "review", "approve", "publish"}), None)
    if not matching:
        raise HTTPException(status_code=422, detail="No runtime mapping found for agent")
    methodology_id = payload.methodology_id or matching.key.methodology_id
    stage_id = payload.stage_id or matching.key.stage_id
    activity_id = payload.activity_id if payload.activity_id is not None else matching.key.activity_id
    task_id = payload.task_id if payload.task_id is not None else matching.key.task_id
    user_input = dict(payload.user_input)
    user_input["demo_safe"] = True
    user_input["preview_only"] = True
    user_input.setdefault("human_review_approved", True)
    result = await run_methodology_node_action(workspace_id=f"demo-preview-{agent_id}", methodology_id=methodology_id, stage_id=stage_id, activity_id=activity_id, task_id=task_id, lifecycle_event=payload.lifecycle_event, user_input=user_input)
    logger.info("agent_gallery.preview.run", extra={"tenant_id": tenant_id, "project_id": None, "agent_id": agent_id})
    return AgentPreviewRunResponse(agent_id=agent_id, demo_safe=True, run_trace=result.get("workflow_trace", {}), artifacts=[*result.get("artifacts_created", []), *result.get("artifacts_updated", [])], connector_operations=result.get("connector_operations", []), status=result.get("status", "completed"))


@router.get("/api/agent-gallery/{project_id}")
async def get_project_agent_settings(project_id: str, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    registry = load_agent_registry()
    settings = agent_settings_store.ensure_project_settings(tenant_id, project_id, registry)
    logger.info("agent_gallery.project.get", extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": None})
    response_agents = []
    for entry in registry:
        stored = settings.agents.get(entry.agent_id)
        if not stored:
            continue
        response_agents.append(AgentProjectEntry(agent_id=entry.agent_id, name=entry.name, category=entry.category, description=entry.description, outputs=entry.outputs, required=entry.required, enabled=stored.enabled, config=stored.config).model_dump())
    return JSONResponse(status_code=200, content={"project_id": project_id, "tenant_id": tenant_id, "agents": response_agents})


@router.patch("/api/agent-gallery/{project_id}/agents/{agent_id}")
async def update_project_agent_settings(project_id: str, agent_id: str, payload: AgentConfigUpdate, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if not _is_agent_admin(request, session):
        raise HTTPException(status_code=403, detail="Agent gallery is read-only")
    registry = load_agent_registry()
    registry_entry = next((e for e in registry if e.agent_id == agent_id), None)
    if not registry_entry:
        raise HTTPException(status_code=404, detail="Agent not found")
    if payload.enabled is False and registry_entry.required:
        raise HTTPException(status_code=422, detail="Required agents cannot be disabled")
    settings = agent_settings_store.ensure_project_settings(tenant_id, project_id, registry)
    if agent_id not in settings.agents:
        raise HTTPException(status_code=404, detail="Agent not configured")
    try:
        updated = agent_settings_store.update_agent_settings(tenant_id, project_id, agent_id, enabled=payload.enabled, config=payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("agent_gallery.project.patch", extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": agent_id})
    response = AgentProjectEntry(agent_id=registry_entry.agent_id, name=registry_entry.name, category=registry_entry.category, description=registry_entry.description, outputs=registry_entry.outputs, required=registry_entry.required, enabled=updated.enabled, config=updated.config)
    return JSONResponse(status_code=200, content=response.model_dump())


@router.post("/api/agent-gallery/{project_id}/reset-defaults")
async def reset_project_agent_settings(project_id: str, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if not _is_agent_admin(request, session):
        raise HTTPException(status_code=403, detail="Agent gallery is read-only")
    registry = load_agent_registry()
    settings = agent_settings_store.reset_project_defaults(tenant_id, project_id, registry)
    logger.info("agent_gallery.project.reset", extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": None})
    response_agents = []
    for entry in registry:
        stored = settings.agents.get(entry.agent_id)
        if not stored:
            continue
        response_agents.append(AgentProjectEntry(agent_id=entry.agent_id, name=entry.name, category=entry.category, description=entry.description, outputs=entry.outputs, required=entry.required, enabled=stored.enabled, config=stored.config).model_dump())
    return JSONResponse(status_code=200, content={"project_id": project_id, "tenant_id": tenant_id, "agents": response_agents})
