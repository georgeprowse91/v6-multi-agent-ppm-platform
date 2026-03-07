"""Methodology editor, runtime actions, SoR read/publish routes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, HTTPException, Request

from routes._deps import (
    METHODOLOGY_DOCS_ROOT,
    METHODOLOGY_STORAGE_PATH,
    SOR_FIXTURES_PATH,
    Orchestrator,
    _demo_mode_enabled,
    _load_json,
    _load_yaml,
    _require_session,
    _write_json,
    available_methodologies,
    build_event,
    demo_outbox,
    get_audit_log_store,
    get_default_methodology_map,
    get_methodology_map,
    list_runtime_actions_for_node,
    permission_required,
    resolve_runtime,
    runtime_lifecycle_store,
    workspace_state_store,
)
from methodologies import (
    analyse_methodology_change_impact,
    deprecate_tenant_methodology,
    get_tenant_methodologies,
    get_tenant_methodology,
    get_tenant_methodology_policy,
    publish_tenant_methodology,
    save_tenant_methodology,
    set_tenant_methodology_policy,
    validate_methodology_selection,
)
from routes._models import (
    MethodologyActivityEditor,
    MethodologyEditorPayload,
    MethodologyGateCriteriaEditor,
    MethodologyGateEditor,
    MethodologyNodeActionRequest,
    MethodologyNodeActionResponse,
    MethodologyRuntimeResolveResponse,
    MethodologyStageEditor,
    RuntimeApprovalDecisionRequest,
    SorPreviewRequest,
    SorPreviewResponse,
    SorPublishRequest,
    SorPublishResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_methodology_storage() -> dict[str, Any]:
    return _load_json(METHODOLOGY_STORAGE_PATH, {"methodologies": {}})


def _load_exit_criteria_from_yaml(methodology_id: str) -> list[list[str]]:
    payload = _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "map.yaml")
    stages = payload.get("stages", [])
    return [stage.get("exit_criteria", []) for stage in stages if isinstance(stage, dict)]


def _load_gates_from_yaml(methodology_id: str) -> list[dict[str, Any]]:
    payload = _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "gates.yaml")
    gates = payload.get("gates", [])
    return [gate for gate in gates if isinstance(gate, dict)]


def _build_methodology_editor_payload(methodology_id: str) -> MethodologyEditorPayload:
    storage = _load_methodology_storage()
    stored_entry = storage.get("methodologies", {}).get(methodology_id, {})
    stored_map = stored_entry.get("map") if isinstance(stored_entry, dict) else None
    stored_gates = stored_entry.get("gates") if isinstance(stored_entry, dict) else None
    methodology_map = stored_map or get_default_methodology_map(methodology_id)
    gates = stored_gates or _load_gates_from_yaml(methodology_id)
    exit_criteria_defaults = _load_exit_criteria_from_yaml(methodology_id)
    stages: list[MethodologyStageEditor] = []
    for index, stage in enumerate(methodology_map.get("stages", [])):
        exit_criteria = stage.get("exit_criteria")
        if exit_criteria is None:
            exit_criteria = exit_criteria_defaults[index] if index < len(exit_criteria_defaults) else []
        activities = [
            MethodologyActivityEditor(
                id=a.get("id", ""), name=a.get("name", ""), description=a.get("description", ""),
                prerequisites=a.get("prerequisites", []), category=a.get("category", "methodology"),
                recommended_canvas_tab=a.get("recommended_canvas_tab", "document"),
            ) for a in stage.get("activities", [])
        ]
        stages.append(MethodologyStageEditor(id=stage.get("id", ""), name=stage.get("name", ""), exit_criteria=exit_criteria, activities=activities))
    gates_payload = [
        MethodologyGateEditor(
            id=g.get("id", ""), name=g.get("name", ""), stage=g.get("stage", ""),
            criteria=[MethodologyGateCriteriaEditor(id=c.get("id", ""), description=c.get("description", ""), evidence=c.get("evidence"), check=c.get("check")) for c in g.get("criteria", []) if isinstance(c, dict)],
        ) for g in gates if isinstance(g, dict)
    ]
    return MethodologyEditorPayload(methodology_id=methodology_id, stages=stages, gates=gates_payload)


def _validate_methodology_prereqs(stages: list[MethodologyStageEditor]) -> None:
    activity_ids = {a.id for s in stages for a in s.activities if a.id}
    invalid = [f"{a.id}:{p}" for s in stages for a in s.activities for p in a.prerequisites if p not in activity_ids]
    if invalid:
        raise HTTPException(status_code=422, detail="Invalid prerequisites: " + ", ".join(sorted(invalid)))


def _load_sor_fixtures() -> dict[str, Any]:
    if SOR_FIXTURES_PATH.exists():
        return json.loads(SOR_FIXTURES_PATH.read_text(encoding="utf-8"))
    return {"records": []}


def _collect_sor_sources(resolution_contract: dict[str, Any]) -> list[dict[str, Any]]:
    return list(resolution_contract.get("connectors", {}).get("sources", []))


def _collect_sor_destinations(resolution_contract: dict[str, Any]) -> list[dict[str, Any]]:
    return list(resolution_contract.get("connectors", {}).get("destinations", []))


def _build_sor_preview_rows(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixtures = _load_sor_fixtures()
    records = fixtures.get("records", [])
    if not sources:
        return []
    source_types = {src.get("connector_type") for src in sources}
    return [item for item in records if item.get("connector_type") in source_types][:20]


async def run_methodology_node_action(
    workspace_id: str, methodology_id: str, stage_id: str,
    activity_id: str | None, task_id: str | None,
    lifecycle_event: str, user_input: dict[str, Any],
) -> dict[str, Any]:
    resolution_contract = resolve_runtime(methodology_id, stage_id, activity_id, task_id, lifecycle_event)
    correlation_basis = "::".join([workspace_id, methodology_id, stage_id, activity_id or "-", task_id or "-", lifecycle_event, ",".join(resolution_contract.get("template_ids", [])), str(user_input.get("request_id") or datetime.now(tz=timezone.utc).isoformat())])
    correlation_id = str(uuid5(NAMESPACE_URL, correlation_basis))
    workspace_state = workspace_state_store.get_or_create("default", workspace_id)
    actor_id = str(user_input.get("actor_id") or "ui-user")
    get_audit_log_store().record_event(build_event(tenant_id=workspace_state.tenant_id, actor_id=actor_id, actor_type="user", roles=["project_member"], action=f"methodology.lifecycle.{lifecycle_event}.requested", resource_type="workspace", resource_id=workspace_id, outcome="success", metadata={"stage_id": stage_id, "activity_id": activity_id, "correlation_id": correlation_id}))
    escalation_rules = resolution_contract.get("assistant", {}).get("response_contract", {}).get("escalation_rules", [])
    needs_human_review = (resolution_contract.get("agent_workflow", {}).get("human_review_required", False) or lifecycle_event in {"review", "approve", "publish"} or any("publish_external" in str(rule).lower() and "approve" in str(rule).lower() for rule in escalation_rules))
    if needs_human_review and not user_input.get("human_review_approved"):
        approval_id = f"apr-{uuid4().hex[:10]}"
        runtime_lifecycle_store.create_approval(tenant_id=workspace_state.tenant_id, workspace_id=workspace_id, approval={"approval_id": approval_id, "workspace_id": workspace_id, "methodology_id": methodology_id, "stage_id": stage_id, "activity_id": activity_id, "requested_event": lifecycle_event, "status": "pending", "requested_at": datetime.now(tz=timezone.utc).isoformat(), "requested_by": actor_id, "notes": user_input.get("notes"), "history": [{"action": "requested", "actor": actor_id, "timestamp": datetime.now(tz=timezone.utc).isoformat()}]})
        get_audit_log_store().record_event(build_event(tenant_id=workspace_state.tenant_id, actor_id=actor_id, actor_type="user", roles=["project_member"], action="methodology.lifecycle.review.queued", resource_type="approval", resource_id=approval_id, outcome="success", metadata={"requested_event": lifecycle_event, "correlation_id": correlation_id}))
        return {"workspace_id": workspace_id, "lifecycle_event": lifecycle_event, "resolution_contract": resolution_contract, "assistant_response": {"intent_id": resolution_contract["assistant"]["intent_id"], "output_format": resolution_contract["assistant"]["response_contract"]["output_format"], "validation_checklist": resolution_contract["assistant"]["response_contract"]["validation_checklist"], "content": "Human review is required before this lifecycle action can proceed."}, "artifacts_created": [], "artifacts_updated": [], "connector_operations": [], "workflow_trace": {"correlation_id": correlation_id, "agent_ids_executed": [], "started_at": datetime.now(tz=timezone.utc).isoformat(), "completed_at": datetime.now(tz=timezone.utc).isoformat()}, "human_review": {"status": "pending", "required": True, "approval_id": approval_id, "next_step": "Resolve in approval inbox then rerun with human_review_approved=true."}, "status": "review_required"}
    context_refs: dict[str, Any] = {"workspace_id": workspace_id, "project_id": workspace_id, "methodology_id": methodology_id, "stage_id": stage_id, "activity_id": activity_id, "task_id": task_id, "lifecycle_event": lifecycle_event, "connector_bindings": resolution_contract.get("connectors", {}), "selected_canvas": resolution_contract.get("canvas", {}), "workspace_context": workspace_state.model_dump(mode="json"), "user_input": user_input, "correlation_id": correlation_id}
    orchestrator = Orchestrator()
    started_at = datetime.now(tz=timezone.utc).isoformat()
    orchestration_result = await orchestrator.run_methodology_node_action(methodology_id=methodology_id, stage_id=stage_id, activity_id=activity_id, task_id=task_id, lifecycle_event=lifecycle_event, template_ids=resolution_contract.get("template_ids", []), context_refs=context_refs)
    completed_at = datetime.now(tz=timezone.utc).isoformat()
    connector_operations: list[dict[str, Any]] = []
    agent_ids_executed: list[str] = []
    for task_payload in orchestration_result.results.values():
        connector_operations.append({"connector_binding": task_payload.get("input", {}).get("connector_binding"), "side_effects": task_payload.get("input", {}).get("side_effects", [])})
        aid = task_payload.get("agent_id")
        if aid:
            agent_ids_executed.append(aid)
    canvas_type = resolution_contract.get("canvas", {}).get("canvas_type", "document")
    artifact_id = f"artifact::{workspace_id}::{methodology_id}::{stage_id}::{activity_id or 'activity'}::{canvas_type}"
    lifecycle_state = "published" if lifecycle_event == "publish" else "draft"
    artifact_ref = runtime_lifecycle_store.upsert_artifact(tenant_id=workspace_state.tenant_id, workspace_id=workspace_id, artifact_id=artifact_id, artifact={"workspace_id": workspace_id, "methodology_id": methodology_id, "stage_id": stage_id, "activity_id": activity_id, "canvas_type": canvas_type, "status": lifecycle_state, "title": (activity_id or stage_id).replace("-", " ").title(), "metadata": {"correlation_id": correlation_id, "lifecycle_event": lifecycle_event, "connector_operations": connector_operations}})
    if lifecycle_event == "publish":
        destinations = _collect_sor_destinations(resolution_contract)
        change_payload = {"artifact_id": artifact_id, "status": lifecycle_state, "metadata": artifact_ref.get("metadata", {})}
        if _demo_mode_enabled():
            demo_outbox.append("external_side_effects", {"workspace_id": workspace_id, "lifecycle_event": lifecycle_event, "destinations": destinations, "changes": change_payload, "status": "captured_in_demo_outbox", "captured_at": completed_at})
        else:
            connector_operations.append({"connector_binding": {"destinations": destinations}, "side_effects": ["publish_external"], "status": "submitted_to_sor"})
    output_format = resolution_contract["assistant"]["response_contract"]["output_format"]
    if output_format == "json":
        assistant_content: Any = {"templates": resolution_contract.get("template_ids", []), "results": orchestration_result.results, "artifact_reference": artifact_ref}
    else:
        assistant_content = f"Executed {lifecycle_event} and persisted artifact {artifact_id}."
    get_audit_log_store().record_event(build_event(tenant_id=workspace_state.tenant_id, actor_id=actor_id, actor_type="user", roles=["project_member"], action=f"methodology.lifecycle.{lifecycle_event}.completed", resource_type="artifact", resource_id=artifact_id, outcome="success", metadata={"correlation_id": correlation_id, "state": lifecycle_state}))
    sor_sources = _collect_sor_sources(resolution_contract)
    sor_preview = _build_sor_preview_rows(sor_sources)
    return {"workspace_id": workspace_id, "lifecycle_event": lifecycle_event, "resolution_contract": resolution_contract, "assistant_response": {"intent_id": resolution_contract["assistant"]["intent_id"], "output_format": output_format, "validation_checklist": resolution_contract["assistant"]["response_contract"]["validation_checklist"], "content": assistant_content}, "artifacts_created": [artifact_ref] if lifecycle_event == "generate" else [], "artifacts_updated": [artifact_ref] if lifecycle_event in {"update", "review", "approve", "publish"} else [], "connector_operations": connector_operations, "sor_preview": {"sources": sor_sources, "preview_rows": sor_preview}, "workflow_trace": {"correlation_id": correlation_id, "agent_ids_executed": agent_ids_executed, "started_at": started_at, "completed_at": completed_at}, "human_review": {"status": "approved" if user_input.get("human_review_approved") else "not_required", "required": needs_human_review}, "status": "completed"}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/methodology/editor", response_model=MethodologyEditorPayload)
@permission_required("methodology.edit")
async def get_methodology_editor(request: Request, methodology_id: str | None = None) -> MethodologyEditorPayload:
    avail = available_methodologies()
    if not methodology_id:
        methodology_id = "hybrid" if "hybrid" in avail else (avail[0] if avail else "adaptive")
    if methodology_id not in avail:
        raise HTTPException(status_code=404, detail="Methodology not found")
    return _build_methodology_editor_payload(methodology_id)


@router.post("/api/methodology/editor", response_model=MethodologyEditorPayload)
@permission_required("methodology.edit")
async def update_methodology_editor(payload: MethodologyEditorPayload, request: Request) -> MethodologyEditorPayload:
    _validate_methodology_prereqs(payload.stages)
    existing_map = get_methodology_map(payload.methodology_id)
    activity_lookup: dict[str, dict[str, Any]] = {}
    for stage in existing_map.get("stages", []):
        for activity in stage.get("activities", []):
            activity_lookup[activity.get("id")] = activity
    stages_payload: list[dict[str, Any]] = []
    for stage in payload.stages:
        stage_activities = [{"id": a.id, "name": a.name, "description": a.description, "assistant_prompts": activity_lookup.get(a.id, {}).get("assistant_prompts", []), "prerequisites": a.prerequisites, "category": a.category or "methodology", "recommended_canvas_tab": a.recommended_canvas_tab or "document"} for a in stage.activities]
        stages_payload.append({"id": stage.id, "name": stage.name, "activities": stage_activities, "exit_criteria": stage.exit_criteria})
    map_payload = {"id": existing_map.get("id", payload.methodology_id), "name": existing_map.get("name", payload.methodology_id), "description": existing_map.get("description", ""), "stages": stages_payload, "monitoring": existing_map.get("monitoring", [])}

    # Persist to global storage (backward compatibility)
    storage = _load_methodology_storage()
    storage.setdefault("methodologies", {})
    storage["methodologies"][payload.methodology_id] = {"map": map_payload, "gates": [g.model_dump() for g in payload.gates]}
    _write_json(METHODOLOGY_STORAGE_PATH, storage)

    # Also persist to tenant-scoped storage with versioning
    session = _require_session(request)
    tenant_id = session.get("tenant_id", "default")
    actor_id = session.get("subject", "ui-user")
    save_tenant_methodology(
        tenant_id=tenant_id,
        methodology_id=payload.methodology_id,
        map_payload=map_payload,
        gates=[g.model_dump() for g in payload.gates],
        created_by=actor_id,
    )

    return _build_methodology_editor_payload(payload.methodology_id)


@router.get("/api/methodology/runtime/approvals")
async def get_runtime_approvals(workspace_id: str, request: Request, status: str = "pending") -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    items = runtime_lifecycle_store.list_approvals(tenant_id=tenant_id, workspace_id=workspace_id, status=status)
    if _demo_mode_enabled() and not items and status == "pending":
        items = [{"approval_id": "demo-approval-1", "workspace_id": workspace_id, "methodology_id": "adaptive", "stage_id": "demo-stage", "activity_id": "demo-activity", "requested_event": "publish", "status": "pending", "requested_at": datetime.now(tz=timezone.utc).isoformat(), "requested_by": "demo-user", "notes": "Seeded approval for demo lifecycle walkthrough.", "history": []}]
    return {"items": items}


@router.post("/api/methodology/runtime/approvals/{approval_id}/decision")
async def decide_runtime_approval(approval_id: str, payload: RuntimeApprovalDecisionRequest, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    actor_id = session.get("subject") or "ui-user"
    decision = runtime_lifecycle_store.decide_approval(tenant_id=tenant_id, workspace_id=payload.workspace_id, approval_id=approval_id, decision=payload.decision, actor=actor_id, notes=payload.notes)
    if not decision:
        raise HTTPException(status_code=404, detail="Approval not found")
    get_audit_log_store().record_event(build_event(tenant_id=tenant_id, actor_id=actor_id, actor_type="user", roles=["approver"], action=f"methodology.lifecycle.approval.{payload.decision}", resource_type="approval", resource_id=approval_id, outcome="success", metadata={"workspace_id": payload.workspace_id, "notes": payload.notes}))
    return decision


@router.get("/api/methodology/runtime/actions")
async def get_methodology_runtime_actions(methodology_id: str, stage_id: str, activity_id: str | None = None, task_id: str | None = None) -> dict[str, Any]:
    return {"methodology_id": methodology_id, "stage_id": stage_id, "activity_id": activity_id, "task_id": task_id, "actions": list_runtime_actions_for_node(methodology_id, stage_id, activity_id, task_id)}


@router.get("/api/methodology/runtime/resolve", response_model=MethodologyRuntimeResolveResponse)
async def get_methodology_runtime_resolve(methodology_id: str, stage_id: str, activity_id: str | None = None, task_id: str | None = None, event: Literal["view", "generate", "update", "review", "approve", "publish"] = "view") -> MethodologyRuntimeResolveResponse:
    try:
        resolution_contract = resolve_runtime(methodology_id, stage_id, activity_id, task_id, event)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MethodologyRuntimeResolveResponse(resolution_contract=resolution_contract)


@router.post("/api/methodology/runtime/sor/read", response_model=SorPreviewResponse)
async def read_from_sor(payload: SorPreviewRequest) -> SorPreviewResponse:
    rc = resolve_runtime(payload.methodology_id, payload.stage_id, payload.activity_id, payload.task_id, payload.lifecycle_event)
    sources = _collect_sor_sources(rc)
    return SorPreviewResponse(sources=sources, preview_rows=_build_sor_preview_rows(sources))


@router.post("/api/methodology/runtime/sor/publish", response_model=SorPublishResponse)
async def push_to_sor(payload: SorPublishRequest) -> SorPublishResponse:
    rc = resolve_runtime(payload.methodology_id, payload.stage_id, payload.activity_id, payload.task_id, payload.lifecycle_event)
    destinations = _collect_sor_destinations(rc)
    entry = {"workspace_id": payload.workspace_id, "lifecycle_event": payload.lifecycle_event, "destinations": destinations, "changes": payload.changes, "status": "captured_in_demo_outbox" if _demo_mode_enabled() else "submitted_to_sor", "captured_at": datetime.now(tz=timezone.utc).isoformat()}
    if _demo_mode_enabled():
        demo_outbox.append("external_side_effects", entry)
    applied = {"workspace_id": payload.workspace_id, "destinations": destinations, "changes": payload.changes, "applied_at": datetime.now(tz=timezone.utc).isoformat()}
    if _demo_mode_enabled():
        demo_outbox.append("applied_changes", applied)
    get_audit_log_store().record_event(build_event(tenant_id="default", actor_id="demo-sor", actor_type="service", roles=["automation"], action="demo.sor.publish.stubbed", resource_type="workspace", resource_id=payload.workspace_id, outcome="success", metadata={"destinations": destinations}))
    return SorPublishResponse(outbox_entry=entry, applied_change=applied)


@router.get("/api/demo/sor")
async def get_demo_sor_state() -> dict[str, Any]:
    return {"outbox": demo_outbox.read("external_side_effects"), "applied_changes": demo_outbox.read("applied_changes")}


@router.post("/api/methodology/runtime/action", response_model=MethodologyNodeActionResponse)
async def run_methodology_runtime_action(payload: MethodologyNodeActionRequest) -> MethodologyNodeActionResponse:
    result = await run_methodology_node_action(payload.user_input.get("workspace_id", "default"), payload.methodology_id, payload.stage_id, payload.activity_id, payload.task_id, payload.lifecycle_event, payload.user_input)
    return MethodologyNodeActionResponse.model_validate(result)


@router.post("/api/workspace/{workspace_id}/methodology-node-actions", response_model=MethodologyNodeActionResponse)
async def run_workspace_methodology_node_action(workspace_id: str, payload: MethodologyNodeActionRequest) -> MethodologyNodeActionResponse:
    result = await run_methodology_node_action(workspace_id, payload.methodology_id, payload.stage_id, payload.activity_id, payload.task_id, payload.lifecycle_event, payload.user_input)
    return MethodologyNodeActionResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Tenant-scoped methodology management routes
# ---------------------------------------------------------------------------

@router.get("/api/methodology/tenant/list")
async def list_tenant_methodologies(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    methodologies = get_tenant_methodologies(tenant_id)
    return {"tenant_id": tenant_id, "methodologies": methodologies}


@router.get("/api/methodology/tenant/{methodology_id}")
async def get_tenant_methodology_detail(methodology_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    methodology = get_tenant_methodology(tenant_id, methodology_id)
    if not methodology:
        raise HTTPException(status_code=404, detail="Methodology not found for this tenant")
    return {"tenant_id": tenant_id, **methodology}


@router.post("/api/methodology/tenant/{methodology_id}/publish")
@permission_required("methodology.edit")
async def publish_methodology_for_tenant(methodology_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    actor_id = session.get("subject", "ui-user")
    try:
        result = publish_tenant_methodology(tenant_id, methodology_id, published_by=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    get_audit_log_store().record_event(build_event(
        tenant_id=tenant_id, actor_id=actor_id, actor_type="user",
        roles=["admin"], action="methodology.published",
        resource_type="methodology", resource_id=methodology_id,
        outcome="success", metadata={"version": result.get("version")},
    ))
    return result


@router.post("/api/methodology/tenant/{methodology_id}/deprecate")
@permission_required("methodology.edit")
async def deprecate_methodology_for_tenant(methodology_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        return deprecate_tenant_methodology(tenant_id, methodology_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Change impact analysis
# ---------------------------------------------------------------------------

@router.get("/api/methodology/tenant/{methodology_id}/impact")
@permission_required("methodology.edit")
async def get_methodology_change_impact(methodology_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    return analyse_methodology_change_impact(tenant_id, methodology_id)


# ---------------------------------------------------------------------------
# Methodology validation (used by workspace setup)
# ---------------------------------------------------------------------------

@router.get("/api/methodology/validate")
async def validate_methodology_for_workspace(
    methodology_id: str,
    request: Request,
    department: str | None = None,
) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    return validate_methodology_selection(tenant_id, methodology_id, department)


# ---------------------------------------------------------------------------
# Organisation methodology policy routes
# ---------------------------------------------------------------------------

@router.get("/api/methodology/policy")
async def get_methodology_org_policy(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    policy = get_tenant_methodology_policy(tenant_id)
    return {"tenant_id": tenant_id, **policy}


@router.post("/api/methodology/policy")
@permission_required("methodology.edit")
async def set_methodology_org_policy(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    actor_id = session.get("subject", "ui-user")
    body = await request.json()
    policy = set_tenant_methodology_policy(tenant_id, body)
    get_audit_log_store().record_event(build_event(
        tenant_id=tenant_id, actor_id=actor_id, actor_type="user",
        roles=["admin"], action="methodology.policy.updated",
        resource_type="methodology_policy", resource_id=tenant_id,
        outcome="success", metadata={"policy": policy},
    ))
    return {"tenant_id": tenant_id, **policy}
