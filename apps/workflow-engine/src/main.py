from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from tools.runtime_paths import bootstrap_runtime_paths

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = Path(__file__).resolve().parent
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, WORKFLOW_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from agent_client import get_agent_client  # noqa: E402
from workflow_audit import emit_audit_event  # noqa: E402
from workflow_definitions import load_definition, seed_definitions  # noqa: E402
from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402

logger = logging.getLogger("workflow-engine")
logging.basicConfig(level=logging.INFO)

WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_DIR = WORKFLOW_ROOT / "workflows" / "definitions"
DB_PATH = Path(os.getenv("WORKFLOW_DB_PATH", "apps/workflow-engine/storage/workflows.db"))
SCHEMA_PATH = WORKFLOW_ROOT / "workflows" / "schema" / "workflow.schema.json"

app = FastAPI(title="Workflow Engine", version="1.0.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("workflow-engine")
configure_metrics("workflow-engine")
app.add_middleware(TraceMiddleware, service_name="workflow-engine")
app.add_middleware(RequestMetricsMiddleware, service_name="workflow-engine")
store = WorkflowStore(DB_PATH)
bootstrap_runtime_paths()
from approval_workflow_agent import ApprovalWorkflowAgent  # noqa: E402

approval_agent = ApprovalWorkflowAgent()
agent_client = get_agent_client()
runtime = WorkflowRuntime(store, approval_agent, agent_client)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "workflow-engine"


class WorkflowStartRequest(BaseModel):
    workflow_id: str
    tenant_id: str
    classification: str
    payload: dict[str, Any]
    actor: dict[str, Any]


class WorkflowRunResponse(BaseModel):
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    current_step_id: str | None
    created_at: str
    updated_at: str


class WorkflowUpdateRequest(BaseModel):
    status: str


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


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


@app.on_event("startup")
async def startup_event() -> None:
    await approval_agent.initialize()
    seed_definitions(store, DEFINITIONS_DIR, SCHEMA_PATH)


@app.get("/workflows/definitions", response_model=list[WorkflowDefinitionResponse])
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


@app.post("/workflows/definitions", response_model=WorkflowDefinitionResponse)
async def create_definition(request: WorkflowDefinitionCreateRequest) -> WorkflowDefinitionResponse:
    record = store.upsert_definition(request.workflow_id, request.definition)
    return WorkflowDefinitionResponse(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        owner=record.owner,
        description=record.description,
    )


@app.post("/workflows/start", response_model=WorkflowRunResponse)
async def start_workflow(
    request: WorkflowStartRequest, http_request: Request
) -> WorkflowRunResponse:
    if request.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    definition = _get_definition(request.workflow_id)
    run_id = str(uuid4())
    instance = store.create(run_id, request.workflow_id, request.tenant_id, request.payload)
    instance = await runtime.start(instance, definition, request.actor)

    emit_audit_event(
        tenant_id=request.tenant_id,
        actor=request.actor,
        action="workflow.started",
        resource={"id": run_id, "type": "workflow", "definition": definition.get("name")},
        classification=request.classification,
    )

    logger.info("workflow_started", extra={"run_id": run_id, "workflow_id": request.workflow_id})
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@app.get("/workflows/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow(run_id: str, http_request: Request) -> WorkflowRunResponse:
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


@app.get("/workflows", response_model=list[WorkflowRunResponse])
async def list_workflows(http_request: Request) -> list[WorkflowRunResponse]:
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


@app.post("/workflows/{run_id}/resume", response_model=WorkflowRunResponse)
async def resume_workflow(run_id: str, http_request: Request) -> WorkflowRunResponse:
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
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


@app.get("/workflows/{run_id}/timeline", response_model=list[WorkflowEventResponse])
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


@app.post("/workflows/{run_id}/status", response_model=WorkflowRunResponse)
async def update_workflow(
    run_id: str, request: WorkflowUpdateRequest, http_request: Request
) -> WorkflowRunResponse:
    instance = store.update_status(run_id, request.status)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    emit_audit_event(
        tenant_id=instance.tenant_id,
        actor={"id": "workflow-engine", "type": "system", "roles": ["integration_service"]},
        action="workflow.updated",
        resource={"id": run_id, "type": "workflow", "status": request.status},
        classification="internal",
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


@app.get("/approvals", response_model=list[WorkflowApprovalResponse])
async def list_approvals(
    http_request: Request, status: str | None = None
) -> list[WorkflowApprovalResponse]:
    approvals = store.list_approvals(http_request.state.auth.tenant_id, status=status)
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


@app.get("/approvals/{approval_id}", response_model=WorkflowApprovalResponse)
async def get_approval(approval_id: str, http_request: Request) -> WorkflowApprovalResponse:
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return WorkflowApprovalResponse(
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


@app.post("/approvals/{approval_id}/decision", response_model=WorkflowRunResponse)
async def decide_approval(
    approval_id: str, request: WorkflowApprovalDecisionRequest, http_request: Request
) -> WorkflowRunResponse:
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    instance = await runtime.handle_approval_decision(
        approval, request.decision, request.approver_id, request.comments
    )
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowRunResponse(
        run_id=instance.run_id,
        workflow_id=instance.workflow_id,
        tenant_id=instance.tenant_id,
        status=instance.status,
        current_step_id=instance.current_step_id,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
