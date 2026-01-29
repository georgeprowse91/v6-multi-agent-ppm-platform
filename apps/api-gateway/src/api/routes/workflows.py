from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.runtime_bootstrap import bootstrap_runtime_paths

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKFLOW_ENGINE_SRC = REPO_ROOT / "apps" / "workflow-engine" / "src"
if str(WORKFLOW_ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ENGINE_SRC))

from agent_client import get_agent_client  # noqa: E402
from workflow_definitions import load_definition, seed_definitions  # noqa: E402
from workflow_runtime import WorkflowRuntime  # noqa: E402
from security.audit_log import build_event, get_audit_log_store
from workflow_storage import WorkflowStore  # noqa: E402

router = APIRouter()

bootstrap_runtime_paths()

WORKFLOW_ROOT = REPO_ROOT / "apps" / "workflow-engine"
DEFINITIONS_DIR = WORKFLOW_ROOT / "workflows" / "definitions"
SCHEMA_PATH = WORKFLOW_ROOT / "workflows" / "schema" / "workflow.schema.json"
DB_PATH = Path(os.getenv("WORKFLOW_DB_PATH", "apps/workflow-engine/storage/workflows.db"))

store = WorkflowStore(DB_PATH)
seed_definitions(store, DEFINITIONS_DIR, SCHEMA_PATH)


class WorkflowStartRequest(BaseModel):
    workflow_id: str
    payload: dict[str, Any]
    actor: dict[str, Any]
    classification: str = "internal"


class WorkflowRunResponse(BaseModel):
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    current_step_id: str | None
    created_at: str
    updated_at: str


class WorkflowDefinitionResponse(BaseModel):
    workflow_id: str
    name: str
    version: str
    owner: str
    description: str | None


class WorkflowDefinitionCreateRequest(BaseModel):
    workflow_id: str
    definition: dict[str, Any]


class WorkflowEventResponse(BaseModel):
    event_id: str
    run_id: str
    step_id: str | None
    status: str
    message: str
    created_at: str


class WorkflowApprovalResponse(BaseModel):
    approval_id: str
    run_id: str
    step_id: str
    tenant_id: str
    status: str
    created_at: str
    updated_at: str
    decision: str | None
    approver_id: str | None
    comments: str | None
    metadata: dict[str, Any]


class WorkflowApprovalDetailResponse(WorkflowApprovalResponse):
    audit_trail: list[dict[str, Any]]


class WorkflowApprovalDecisionRequest(BaseModel):
    decision: str
    approver_id: str
    comments: str | None = None


def _get_definition(workflow_id: str) -> dict[str, Any]:
    stored = store.get_definition(workflow_id)
    if stored:
        return stored.definition
    path = DEFINITIONS_DIR / f"{workflow_id}.workflow.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    try:
        definition = load_definition(path, SCHEMA_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.upsert_definition(workflow_id, definition)
    return definition


def _get_runtime(request: Request) -> WorkflowRuntime:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    approval_agent = orchestrator.get_agent("agent_003_approval_workflow")
    if not approval_agent:
        raise HTTPException(status_code=503, detail="Approval agent unavailable")
    agent_client = get_agent_client()
    return WorkflowRuntime(store, approval_agent, agent_client)


@router.get("/workflows/definitions", response_model=list[WorkflowDefinitionResponse])
async def list_definitions() -> list[WorkflowDefinitionResponse]:
    return [
        WorkflowDefinitionResponse(
            workflow_id=definition.workflow_id,
            name=definition.name,
            version=definition.version,
            owner=definition.owner,
            description=definition.description,
        )
        for definition in store.list_definitions()
    ]


@router.post("/workflows/definitions", response_model=WorkflowDefinitionResponse)
async def create_definition(request: WorkflowDefinitionCreateRequest) -> WorkflowDefinitionResponse:
    record = store.upsert_definition(request.workflow_id, request.definition)
    return WorkflowDefinitionResponse(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        owner=record.owner,
        description=record.description,
    )


@router.post("/workflows/start", response_model=WorkflowRunResponse)
async def start_workflow(request: WorkflowStartRequest, http_request: Request) -> WorkflowRunResponse:
    definition = _get_definition(request.workflow_id)
    run_id = str(uuid4())
    instance = store.create(
        run_id,
        request.workflow_id,
        http_request.state.auth.tenant_id,
        request.payload,
    )
    runtime = _get_runtime(http_request)
    instance = await runtime.start(instance, definition, request.actor)
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("/workflows/instances", response_model=list[WorkflowRunResponse])
async def list_instances(http_request: Request) -> list[WorkflowRunResponse]:
    return [
        WorkflowRunResponse(
            run_id=instance.run_id,
            workflow_id=instance.workflow_id,
            tenant_id=instance.tenant_id,
            status=instance.status,
            current_step_id=instance.current_step_id,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )
        for instance in store.list_instances(http_request.state.auth.tenant_id)
    ]


@router.get("/workflows/instances/{run_id}", response_model=WorkflowRunResponse)
async def get_instance(run_id: str, http_request: Request) -> WorkflowRunResponse:
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.post("/workflows/instances/{run_id}/resume", response_model=WorkflowRunResponse)
async def resume_workflow(run_id: str, http_request: Request) -> WorkflowRunResponse:
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    runtime = _get_runtime(http_request)
    definition = _get_definition(instance.workflow_id)
    instance = await runtime.resume(instance, definition, {"id": http_request.state.auth.subject})
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("/workflows/instances/{run_id}/timeline", response_model=list[WorkflowEventResponse])
async def workflow_timeline(run_id: str, http_request: Request) -> list[WorkflowEventResponse]:
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return [
        WorkflowEventResponse(
            event_id=event.event_id,
            run_id=event.run_id,
            step_id=event.step_id,
            status=event.status,
            message=event.message,
            created_at=event.created_at,
        )
        for event in store.list_events(run_id)
    ]


@router.get("/workflows/approvals", response_model=list[WorkflowApprovalResponse])
async def list_approvals(
    http_request: Request, status: str | None = None, approver_id: str | None = None
) -> list[WorkflowApprovalResponse]:
    approvals = store.list_approvals(http_request.state.auth.tenant_id, status=status)
    if approver_id:
        approvals = [
            approval
            for approval in approvals
            if approver_id in approval.metadata.get("approvers", [])
        ]
    return [
        WorkflowApprovalResponse(
            approval_id=approval.approval_id,
            run_id=approval.run_id,
            step_id=approval.step_id,
            tenant_id=approval.tenant_id,
            status=approval.status,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
            decision=approval.decision,
            approver_id=approval.approver_id,
            comments=approval.comments,
            metadata=approval.metadata,
        )
        for approval in approvals
    ]


@router.get("/workflows/approvals/{approval_id}", response_model=WorkflowApprovalDetailResponse)
async def get_approval(approval_id: str, http_request: Request) -> WorkflowApprovalDetailResponse:
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    runtime = _get_runtime(http_request)
    approval_record = runtime.approval_agent.approval_store.get(
        approval.tenant_id, approval.approval_id
    )
    audit_trail: list[dict[str, Any]] = []
    if approval_record:
        notifications = approval_record.get("details", {}).get("notifications", [])
        for notification in notifications:
            audit_trail.append(
                {
                    "action": "notification_sent",
                    "timestamp": notification.get("sent_at"),
                    "actor": notification.get("to"),
                    "details": notification,
                }
            )
        decision = approval_record.get("details", {}).get("decision")
        if decision:
            audit_trail.append(
                {
                    "action": "decision",
                    "timestamp": approval_record.get("details", {}).get("decided_at"),
                    "actor": approval_record.get("details", {}).get("decided_by"),
                    "details": {
                        "decision": decision,
                        "comments": approval_record.get("details", {}).get("comments"),
                    },
                }
            )

    return WorkflowApprovalDetailResponse(
        approval_id=approval.approval_id,
        run_id=approval.run_id,
        step_id=approval.step_id,
        tenant_id=approval.tenant_id,
        status=approval.status,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
        decision=approval.decision,
        approver_id=approval.approver_id,
        comments=approval.comments,
        metadata=approval.metadata,
        audit_trail=audit_trail,
    )


@router.post("/workflows/approvals/{approval_id}/decision", response_model=WorkflowRunResponse)
async def decide_approval(
    approval_id: str, request: WorkflowApprovalDecisionRequest, http_request: Request
) -> WorkflowRunResponse:
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    runtime = _get_runtime(http_request)
    instance = await runtime.handle_approval_decision(
        approval, request.decision, request.approver_id, request.comments
    )
    auth = http_request.state.auth
    get_audit_log_store().record_event(
        build_event(
            tenant_id=auth.tenant_id,
            actor_id=auth.subject,
            actor_type="user",
            roles=auth.roles,
            action="approval.decision",
            resource_type="approval",
            resource_id=approval_id,
            outcome="success",
            metadata={
                "decision": request.decision,
                "approver_id": request.approver_id,
            },
        )
    )
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )
