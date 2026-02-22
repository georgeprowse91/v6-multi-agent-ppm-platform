from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from tools.runtime_paths import bootstrap_runtime_paths

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = Path(__file__).resolve().parent
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
WORKFLOW_PACKAGE_ROOT = REPO_ROOT / "packages" / "workflow" / "src"
EVENT_BUS_ROOT = REPO_ROOT / "packages" / "event-bus" / "src"
COMMON_ROOT = REPO_ROOT / "packages" / "common" / "src"
for root in (
    REPO_ROOT,
    WORKFLOW_ROOT,
    SECURITY_ROOT,
    OBSERVABILITY_ROOT,
    WORKFLOW_PACKAGE_ROOT,
    EVENT_BUS_ROOT,
    COMMON_ROOT,
):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from agent_client import get_agent_client  # noqa: E402
from common.env_validation import environment_value  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402
from workflow.dispatcher import WorkflowDispatcher  # noqa: E402
from workflow_audit import emit_audit_event  # noqa: E402
from workflow_definitions import (  # noqa: E402
    load_definition,
    seed_definitions,
    validate_definition,
)
from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore, resolve_workflow_storage  # noqa: E402

from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("workflow-engine")
logging.basicConfig(level=logging.INFO)

settings = validate_startup_config()

WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_DIR = WORKFLOW_ROOT / "workflows" / "definitions"
DEMO_DEFINITIONS_DIR = REPO_ROOT / "config" / "demo-workflows"
ENVIRONMENT = environment_value(os.environ)
WORKFLOW_STORAGE = resolve_workflow_storage(environment=ENVIRONMENT)
DB_PATH = WORKFLOW_STORAGE.db_path
SCHEMA_PATH = WORKFLOW_ROOT / "workflows" / "schema" / "workflow.schema.json"
RATE_LIMIT = os.getenv("WORKFLOW_ENGINE_RATE_LIMIT", "100/minute")

app = FastAPI(title="Workflow Engine", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
app.add_middleware(SlowAPIMiddleware)
configure_tracing("workflow-engine")
configure_metrics("workflow-engine")
app.add_middleware(TraceMiddleware, service_name="workflow-engine")
app.add_middleware(RequestMetricsMiddleware, service_name="workflow-engine")
apply_api_governance(app, service_name="workflow-engine")
logger.info(
    "workflow-engine persistence configuration",
    extra={
        "environment": ENVIRONMENT,
        "storage_backend": WORKFLOW_STORAGE.backend,
        "durability_mode": WORKFLOW_STORAGE.durability_mode,
        "workflow_db_path_source": WORKFLOW_STORAGE.source,
        "workflow_db_path": str(DB_PATH),
    },
)
store = WorkflowStore.from_selection(WORKFLOW_STORAGE)
bootstrap_runtime_paths()
from approval_workflow_agent import ApprovalWorkflowAgent  # noqa: E402

approval_agent = ApprovalWorkflowAgent()
agent_client = get_agent_client()
runtime = WorkflowRuntime(store, approval_agent, agent_client)
dispatcher = WorkflowDispatcher()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "workflow-engine"
    dependencies: dict[str, str] = Field(default_factory=dict)


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


class WorkflowDefinitionUpdateRequest(BaseModel):
    definition: dict[str, Any]


class WorkflowCompensationRetryRequest(BaseModel):
    step_id: str | None = None
    actor: dict[str, Any] | None = None


class WorkflowJournalResponse(BaseModel):
    journal_id: str
    run_id: str
    step_id: str | None
    phase: str
    status: str
    attempt: int
    details: dict[str, Any]
    created_at: str


ROLE_POLICIES = {
    "workflow:manage_definitions": {"workflow_admin", "workflow_editor"},
    "workflow:start": {"workflow_admin", "workflow_operator", "portfolio_admin"},
    "workflow:monitor": {
        "workflow_admin",
        "workflow_operator",
        "portfolio_admin",
        "portfolio_viewer",
    },
    "workflow:update": {"workflow_admin", "workflow_operator"},
}


def _require_roles(request: Request, allowed: set[str]) -> None:
    roles = set(request.state.auth.roles or [])
    if allowed and not roles.intersection(allowed):
        raise HTTPException(status_code=403, detail="Insufficient role permissions")


def _enforce_methodology_gates(definition: dict[str, Any], payload: dict[str, Any]) -> None:
    gates = definition.get("gates", {})
    required = set(gates.get("required_activities", []))
    if not required:
        return
    completed = set(payload.get("completed_activities", []))
    missing = required.difference(completed)
    if missing:
        raise HTTPException(
            status_code=409,
            detail={"message": "Methodology gates not satisfied", "missing": sorted(missing)},
        )


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
async def healthz(response: Response) -> HealthResponse:
    dependencies = {"workflow_store": "unknown", "definitions": "unknown"}
    try:
        store.ping()
        dependencies["workflow_store"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["workflow_store"] = "down"
    try:
        if DEFINITIONS_DIR.exists():
            dependencies["definitions"] = "ok"
        else:
            dependencies["definitions"] = "down"
    except Exception:  # noqa: BLE001
        dependencies["definitions"] = "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("workflow-engine")


@app.on_event("startup")
async def startup_event() -> None:
    await approval_agent.initialize()
    seed_definitions(store, DEFINITIONS_DIR, SCHEMA_PATH)
    if settings.demo_mode:
        seed_definitions(store, DEMO_DEFINITIONS_DIR, SCHEMA_PATH)


@api_router.get("/workflows/definitions", response_model=list[WorkflowDefinitionResponse])
async def list_definitions(
    http_request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[WorkflowDefinitionResponse]:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    definitions = [
        WorkflowDefinitionResponse(
            workflow_id=definition.workflow_id,
            name=definition.name,
            version=definition.version,
            owner=definition.owner,
            description=definition.description,
        )
        for definition in store.list_definitions()
    ]
    sliced = definitions[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(definitions))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.post("/workflows/definitions", response_model=WorkflowDefinitionResponse)
async def create_definition(
    request: WorkflowDefinitionCreateRequest, http_request: Request
) -> WorkflowDefinitionResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:manage_definitions"])
    errors = validate_definition(request.definition)
    if errors:
        raise HTTPException(
            status_code=422, detail={"message": "Invalid definition", "errors": errors}
        )
    record = store.upsert_definition(request.workflow_id, request.definition)
    return WorkflowDefinitionResponse(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        owner=record.owner,
        description=record.description,
    )


@api_router.get("/workflows/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def get_definition(workflow_id: str, http_request: Request) -> WorkflowDefinitionResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    record = store.get_definition(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return WorkflowDefinitionResponse(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        owner=record.owner,
        description=record.description,
    )


@api_router.put("/workflows/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def update_definition(
    workflow_id: str, request: WorkflowDefinitionUpdateRequest, http_request: Request
) -> WorkflowDefinitionResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:manage_definitions"])
    errors = validate_definition(request.definition)
    if errors:
        raise HTTPException(
            status_code=422, detail={"message": "Invalid definition", "errors": errors}
        )
    record = store.upsert_definition(workflow_id, request.definition)
    return WorkflowDefinitionResponse(
        workflow_id=record.workflow_id,
        name=record.name,
        version=record.version,
        owner=record.owner,
        description=record.description,
    )


@api_router.delete("/workflows/definitions/{workflow_id}")
async def delete_definition(workflow_id: str, http_request: Request) -> dict[str, str]:
    _require_roles(http_request, ROLE_POLICIES["workflow:manage_definitions"])
    record = store.get_definition(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    store.delete_definition(workflow_id)
    return {"status": "deleted"}


@api_router.post("/workflows/start", response_model=WorkflowRunResponse)
@limiter.limit(RATE_LIMIT)
async def start_workflow(
    request: WorkflowStartRequest,
    http_request: Request,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        description="Optional key to ensure workflow creation is idempotent.",
    ),
) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:start"])
    if request.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    definition = _get_definition(request.workflow_id)
    _enforce_methodology_gates(definition, request.payload)
    steps = definition.get("steps", [])
    if not steps:
        raise HTTPException(status_code=422, detail="Workflow definition has no steps")
    first_step_id = steps[0]["id"]
    run_id = str(uuid4())
    instance = store.create(
        run_id=run_id,
        workflow_id=request.workflow_id,
        tenant_id=request.tenant_id,
        payload=request.payload,
        current_step_id=first_step_id,
        idempotency_key=idempotency_key,
    )
    is_new_run = instance.run_id == run_id
    if is_new_run:
        dispatcher.dispatch_step(instance.run_id, first_step_id, request.actor)
        emit_audit_event(
            tenant_id=request.tenant_id,
            actor=request.actor,
            action="workflow.started",
            resource={
                "id": instance.run_id,
                "type": "workflow",
                "definition": definition.get("name"),
            },
            classification=request.classification,
        )
        await runtime._publish_event(  # noqa: SLF001 - workflow runtime manages event publishing
            "workflow.started",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
                "actor": request.actor,
            },
        )

    logger.info(
        "workflow_started" if is_new_run else "workflow_start_idempotent",
        extra={"run_id": instance.run_id, "workflow_id": request.workflow_id},
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


@api_router.get("/workflows/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow(run_id: str, http_request: Request) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
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


@api_router.get("/workflows", response_model=list[WorkflowRunResponse])
async def list_workflows(
    http_request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[WorkflowRunResponse]:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    runs = [
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
    sliced = runs[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(runs))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.post("/workflows/{run_id}/resume", response_model=WorkflowRunResponse)
async def resume_workflow(run_id: str, http_request: Request) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:update"])
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    definition = _get_definition(instance.workflow_id)
    _enforce_methodology_gates(definition, instance.payload)
    step_id = instance.current_step_id or (definition.get("steps", [{}])[0].get("id"))
    if not step_id:
        raise HTTPException(status_code=422, detail="Workflow definition has no steps")
    store.update_status(run_id, "running", step_id)
    dispatcher.dispatch_step(run_id, step_id, {"id": http_request.state.auth.subject})
    instance = store.get(run_id)
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


@api_router.get("/workflows/{run_id}/timeline", response_model=list[WorkflowEventResponse])
async def workflow_timeline(
    run_id: str,
    http_request: Request,
    response: Response,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> list[WorkflowEventResponse]:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    events = [
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
    sliced = events[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(events))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.post("/workflows/{run_id}/status", response_model=WorkflowRunResponse)
async def update_workflow(
    run_id: str, request: WorkflowUpdateRequest, http_request: Request
) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:update"])
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


@api_router.get("/approvals", response_model=list[WorkflowApprovalResponse])
async def list_approvals(
    http_request: Request,
    response: Response,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[WorkflowApprovalResponse]:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    approvals = store.list_approvals(http_request.state.auth.tenant_id, status=status)
    responses = [
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
    sliced = responses[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(responses))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.get("/approvals/{approval_id}", response_model=WorkflowApprovalResponse)
async def get_approval(approval_id: str, http_request: Request) -> WorkflowApprovalResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
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


@api_router.post("/approvals/{approval_id}/decision", response_model=WorkflowRunResponse)
async def decide_approval(
    approval_id: str, request: WorkflowApprovalDecisionRequest, http_request: Request
) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:update"])
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    instance = await runtime.handle_approval_decision(
        approval,
        request.decision,
        request.approver_id,
        request.comments,
        resume_after_decision=False,
    )
    if instance and instance.status == "running" and instance.current_step_id:
        dispatcher.dispatch_step(
            instance.run_id,
            instance.current_step_id,
            {"id": request.approver_id},
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


@api_router.get("/workflows/{run_id}/compensation", response_model=list[WorkflowJournalResponse])
async def get_compensation_journal(
    run_id: str, http_request: Request
) -> list[WorkflowJournalResponse]:
    _require_roles(http_request, ROLE_POLICIES["workflow:monitor"])
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    entries = await runtime.inspect_compensation(run_id)
    return [WorkflowJournalResponse(**entry) for entry in entries]


@api_router.post("/workflows/{run_id}/compensation/retry", response_model=WorkflowRunResponse)
async def retry_compensation(
    run_id: str, request: WorkflowCompensationRetryRequest, http_request: Request
) -> WorkflowRunResponse:
    _require_roles(http_request, ROLE_POLICIES["workflow:update"])
    instance = store.get(run_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if instance.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    definition = _get_definition(instance.workflow_id)
    actor = request.actor or {"id": http_request.state.auth.subject}
    updated = await runtime.retry_compensation(instance, definition, actor, step_id=request.step_id)
    return WorkflowRunResponse(
        run_id=updated.run_id,
        workflow_id=updated.workflow_id,
        tenant_id=updated.tenant_id,
        status=updated.status,
        current_step_id=updated.current_step_id,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
