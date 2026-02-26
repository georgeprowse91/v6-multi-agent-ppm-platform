"""Workspace state management routes (from legacy_main.py)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from routes._deps import (
    _require_session,
    available_methodologies,
    evaluate_activity_access,
    get_methodology_map,
    list_runtime_actions_for_node,
    list_templates_for_methodology_node,
    next_required_activity,
    permission_required,
    resolve_runtime,
    stage_progress,
    workspace_state_store,
)
from routes._deps import (
    ActivityCompletionUpdate,
    CanvasTab,
    OpenRef,
    WorkspaceSelectionUpdate,
    WorkspaceState,
)
from routes._models import (
    ActivityAccessSummary,
    ActivitySummary,
    GatingSummary,
    MethodologyMapSummary,
    SelectedActivitySummary,
    StageProgressSummary,
    StageSummary,
    WorkspaceStateResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_activity_summary(
    activity: dict[str, Any],
    state: WorkspaceState,
    completed: dict[str, bool],
) -> ActivitySummary:
    access_result = evaluate_activity_access(activity, completed)
    children = [
        _build_activity_summary(child, state, completed)
        for child in activity.get("children", [])
    ]
    return ActivitySummary(
        id=activity.get("id", ""),
        name=activity.get("name", ""),
        description=activity.get("description", ""),
        prerequisites=activity.get("prerequisites", []),
        category=activity.get("category", "methodology"),
        recommended_canvas_tab=activity.get("recommended_canvas_tab", "document"),
        assistant_prompts=activity.get("assistant_prompts", []),
        template_id=activity.get("template_id"),
        agent_id=activity.get("agent_id"),
        connector_id=activity.get("connector_id"),
        access=ActivityAccessSummary(
            allowed=access_result["allowed"],
            reasons=access_result.get("reasons", []),
            missing_prereqs=access_result.get("missing_prereqs", []),
        ),
        completed=completed.get(activity.get("id", ""), False),
        children=children,
    )


def _build_workspace_response(state: WorkspaceState) -> WorkspaceStateResponse:
    methodology_map = get_methodology_map(state.methodology)
    completed = state.activity_completion
    stages: list[StageSummary] = []
    for stage in methodology_map.get("stages", []):
        prog = stage_progress(stage, completed)
        activities = [_build_activity_summary(a, state, completed) for a in stage.get("activities", [])]
        stages.append(StageSummary(
            id=stage.get("id", ""), name=stage.get("name", ""),
            progress=StageProgressSummary(complete_count=prog["complete_count"], total_count=prog["total_count"], percent=prog["percent"]),
            activities=activities,
        ))
    monitoring = [_build_activity_summary(a, state, completed) for a in methodology_map.get("monitoring", [])]
    methodology_summary = MethodologyMapSummary(
        id=methodology_map.get("id", state.methodology or "unknown"),
        name=methodology_map.get("name", state.methodology or "Unknown"),
        description=methodology_map.get("description", ""),
        stages=stages, monitoring=monitoring,
    )
    gating_access = {"allowed": True, "reasons": [], "missing_prereqs": []}
    next_required_id = None
    if state.current_activity_id:
        all_activities = [a for s in methodology_map.get("stages", []) for a in s.get("activities", [])]
        current_activity = next((a for a in all_activities if a.get("id") == state.current_activity_id), None)
        if current_activity:
            gating_access = evaluate_activity_access(current_activity, completed)
        next_required_id = next_required_activity(all_activities, completed)
    gating = GatingSummary(
        current_activity_access=ActivityAccessSummary(allowed=gating_access["allowed"], reasons=gating_access.get("reasons", []), missing_prereqs=gating_access.get("missing_prereqs", [])),
        next_required_activity_id=next_required_id,
    )
    selected = None
    templates_here: list = []
    templates_required: list = []
    templates_review: list = []
    runtime_actions: list[str] = []
    runtime_default_view_contract: dict[str, Any] | None = None
    if state.current_activity_id and state.current_stage_id:
        all_activities = [a for s in methodology_map.get("stages", []) for a in s.get("activities", [])]
        act = next((a for a in all_activities if a.get("id") == state.current_activity_id), None)
        if act:
            selected = SelectedActivitySummary(
                id=act["id"], name=act.get("name", ""), description=act.get("description", ""),
                assistant_prompts=act.get("assistant_prompts", []),
                recommended_canvas_tab=act.get("recommended_canvas_tab", "document"),
                category=act.get("category", "methodology"),
                template_id=act.get("template_id"), agent_id=act.get("agent_id"), connector_id=act.get("connector_id"),
            )
        templates_here = list_templates_for_methodology_node(state.methodology or "hybrid", state.current_stage_id, state.current_activity_id, task_id=None, lifecycle_event=None)
        templates_required = [t for t in templates_here if t.lifecycle_events and "generate" in t.lifecycle_events]
        templates_review = [t for t in templates_here if t.lifecycle_events and "review" in t.lifecycle_events]
        runtime_actions = list_runtime_actions_for_node(state.methodology or "hybrid", state.current_stage_id, state.current_activity_id, task_id=None)
        try:
            runtime_default_view_contract = resolve_runtime(state.methodology or "hybrid", state.current_stage_id, state.current_activity_id, None, "view")
        except (ValueError, KeyError):
            runtime_default_view_contract = None
    return WorkspaceStateResponse(
        version=state.version, tenant_id=state.tenant_id, project_id=state.project_id,
        methodology=state.methodology, current_stage_id=state.current_stage_id,
        current_activity_id=state.current_activity_id, activity_completion=completed,
        current_canvas_tab=state.current_canvas_tab,
        last_opened_document_id=state.last_opened_document_id,
        last_opened_sheet_id=state.last_opened_sheet_id,
        last_opened_milestone_id=state.last_opened_milestone_id,
        updated_at=state.updated_at, available_methodologies=list(available_methodologies()),
        methodology_map_summary=methodology_summary, gating=gating, selected_activity=selected,
        templates_available_here=templates_here, templates_required_here=templates_required,
        templates_in_review=templates_review, runtime_actions_available=runtime_actions,
        runtime_default_view_contract=runtime_default_view_contract,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/workspace/{project_id}", response_model=WorkspaceStateResponse)
@permission_required("portfolio.view")
async def get_workspace_state(project_id: str, request: Request, methodology: str | None = Query(default=None)) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.get_or_create(tenant_id, project_id)
    if methodology is not None:
        selected = methodology.strip()
        if selected not in set(available_methodologies()):
            raise HTTPException(status_code=422, detail="Invalid methodology")
        state = workspace_state_store.update_selection(tenant_id, project_id, {"methodology": selected, "current_stage_id": None, "current_activity_id": None})
    return _build_workspace_response(state)


@router.post("/api/workspace/{project_id}/select", response_model=WorkspaceStateResponse)
@permission_required("portfolio.view")
async def update_workspace_selection(project_id: str, payload: WorkspaceSelectionUpdate, request: Request) -> WorkspaceStateResponse:
    session = _require_session(request)
    if payload.project_id and payload.project_id != project_id:
        raise HTTPException(status_code=422, detail="project_id mismatch")
    tenant_id = session["tenant_id"]
    updates = payload.model_dump(exclude={"project_id"})
    open_ref = updates.pop("open_ref", None)
    if open_ref:
        open_ref = OpenRef.model_validate(open_ref)
        if open_ref.document_id:
            updates["last_opened_document_id"] = open_ref.document_id
        if open_ref.sheet_id:
            updates["last_opened_sheet_id"] = open_ref.sheet_id
        if open_ref.milestone_id:
            updates["last_opened_milestone_id"] = open_ref.milestone_id
    state = workspace_state_store.update_selection(tenant_id, project_id, updates)
    return _build_workspace_response(state)


@router.post("/api/workspace/{project_id}/activity-completion", response_model=WorkspaceStateResponse)
@permission_required("portfolio.view")
async def update_activity_completion(project_id: str, payload: ActivityCompletionUpdate, request: Request) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.update_activity_completion(tenant_id, project_id, payload.activity_id, payload.completed)
    return _build_workspace_response(state)
