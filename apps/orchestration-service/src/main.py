from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from orchestrator import AgentOrchestrator  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("orchestration-service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Orchestration Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/health", "/healthz"})
configure_tracing("orchestration-service")
configure_metrics("orchestration-service")
app.add_middleware(TraceMiddleware, service_name="orchestration-service")
app.add_middleware(RequestMetricsMiddleware, service_name="orchestration-service")

orchestrator = AgentOrchestrator()
kpi_handles = build_kpi_handles("orchestration-service")

workflows_started = configure_metrics("orchestration-service").create_counter(
    name="orchestration_workflows_started_total",
    description="Number of workflows started",
    unit="1",
)
workflows_resumed = configure_metrics("orchestration-service").create_counter(
    name="orchestration_workflows_resumed_total",
    description="Number of workflows resumed",
    unit="1",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orchestration-service"


class WorkflowRequest(BaseModel):
    run_id: str
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    run_id: str
    status: str
    last_checkpoint: str
    payload: dict[str, Any]


@app.on_event("startup")
async def startup() -> None:
    await orchestrator.initialize()
    logger.info("orchestrator_ready", extra={"agents": len(orchestrator.agents)})


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/agents", response_model=list[str])
async def list_agents() -> list[str]:
    return sorted(orchestrator.agents.keys())


@app.post("/workflows/run", response_model=WorkflowResponse)
async def run_workflow(request: Request, payload: WorkflowRequest) -> WorkflowResponse:
    tenant_id = request.state.auth.tenant_id
    state_payload = {"tenant_id": tenant_id, "intent": payload.intent, "payload": payload.payload}
    orchestrator.persist_workflow_state(payload.run_id, "running", "received", state_payload)
    workflows_started.add(1, {"tenant_id": tenant_id, "intent": payload.intent})
    kpi_handles.requests.add(1, {"operation": "run_workflow", "tenant_id": tenant_id})
    state = orchestrator.workflow_states[payload.run_id]
    return WorkflowResponse(
        run_id=state.run_id,
        status=state.status,
        last_checkpoint=state.last_checkpoint,
        payload=state.payload,
    )


@app.get("/workflows", response_model=list[WorkflowResponse])
async def list_workflows(request: Request) -> list[WorkflowResponse]:
    tenant_id = request.state.auth.tenant_id
    responses: list[WorkflowResponse] = []
    for state in orchestrator.workflow_states.values():
        if state.payload.get("tenant_id") == tenant_id:
            responses.append(
                WorkflowResponse(
                    run_id=state.run_id,
                    status=state.status,
                    last_checkpoint=state.last_checkpoint,
                    payload=state.payload,
                )
            )
    return responses


@app.get("/workflows/{run_id}", response_model=WorkflowResponse)
async def get_workflow(run_id: str, request: Request) -> WorkflowResponse:
    tenant_id = request.state.auth.tenant_id
    state = orchestrator.workflow_states.get(run_id)
    if not state or state.payload.get("tenant_id") != tenant_id:
        kpi_handles.errors.add(1, {"operation": "get_workflow", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Workflow not found")
    kpi_handles.requests.add(1, {"operation": "get_workflow", "tenant_id": tenant_id})
    return WorkflowResponse(
        run_id=state.run_id,
        status=state.status,
        last_checkpoint=state.last_checkpoint,
        payload=state.payload,
    )


@app.post("/workflows/{run_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(run_id: str, request: Request) -> WorkflowResponse:
    tenant_id = request.state.auth.tenant_id
    state = orchestrator.workflow_states.get(run_id)
    if not state or state.payload.get("tenant_id") != tenant_id:
        kpi_handles.errors.add(1, {"operation": "resume_workflow", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Workflow not found")
    state.status = "resumed"
    orchestrator.persist_workflow_state(run_id, state.status, state.last_checkpoint, state.payload)
    workflows_resumed.add(1, {"tenant_id": tenant_id})
    kpi_handles.requests.add(1, {"operation": "resume_workflow", "tenant_id": tenant_id})
    return WorkflowResponse(
        run_id=state.run_id,
        status=state.status,
        last_checkpoint=state.last_checkpoint,
        payload=state.payload,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
