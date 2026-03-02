from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
_own_src = str(Path(__file__).resolve().parent)
_common_src = str(REPO_ROOT / "packages" / "common" / "src")
# Ensure this service's own src/ appears first so local modules (e.g. orchestrator.py,
# config.py) are resolved before identically-named modules elsewhere in the monorepo.
for _p in (_own_src, _common_src):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from leader_election import build_leader_elector  # noqa: E402
from observability.logging import configure_logging  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from orchestrator import AgentOrchestrator  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402

from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("orchestration-service")
logging.basicConfig(level=logging.INFO)

_settings = validate_startup_config()

app = FastAPI(title="Orchestration Service", version=API_VERSION)
api_router = APIRouter(prefix="/v1")
if not _settings.auth_dev_mode:
    app.add_middleware(
        AuthTenantMiddleware, exempt_paths={"/health", "/healthz", "/health/ready", "/version"}
    )
configure_tracing("orchestration-service")
configure_metrics("orchestration-service")
configure_logging("orchestration-service")
app.add_middleware(TraceMiddleware, service_name="orchestration-service")
app.add_middleware(RequestMetricsMiddleware, service_name="orchestration-service")
apply_api_governance(app, service_name="orchestration-service")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orchestration-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class DependencyRequest(BaseModel):
    agent_id: str
    depends_on: list[str] = Field(default_factory=list)


class AgentStateResponse(BaseModel):
    agent_id: str
    status: str
    updated_at: str
    reason: str | None = None


class ReadinessCheckResponse(BaseModel):
    name: str
    passed: bool
    severity: str
    message: str
    remediation_hint: str | None = None


class AgentReadinessResponse(BaseModel):
    agent_id: str
    catalog_id: str
    ready: bool
    generated_at: str
    status: str
    last_failure_reason: str | None = None
    checks: list[ReadinessCheckResponse] = Field(default_factory=list)


class WorkflowUploadResponse(BaseModel):
    workflow_id: str | None
    status: str
    tasks: int | None = None
    definition_source: str | None = None


class PlanApprovalRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    tasks: list[dict[str, object]] | None = None
    actor: str = "orchestration-api"


class PlanApprovalResponse(BaseModel):
    success: bool
    data: dict[str, object] | None = None
    error: str | None = None


@app.on_event("startup")
async def startup() -> None:
    try:
        app.state.orchestrator = AgentOrchestrator()
        await app.state.orchestrator.initialize()
        app.state.leader_elector = build_leader_elector("orchestration-service")
        app.state.leader_elector.start()
        logger.info("orchestrator_ready", extra={"agents": len(app.state.orchestrator.agents)})
    except Exception as exc:
        logger.warning("orchestrator_startup_failed", extra={"error": str(exc)})
        if not hasattr(app.state, "orchestrator"):
            app.state.orchestrator = None


@app.on_event("shutdown")
async def shutdown() -> None:
    leader_elector = getattr(app.state, "leader_elector", None)
    if leader_elector:
        leader_elector.stop()
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.cleanup()


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    dependencies = {
        "orchestrator": "ok" if (orchestrator and orchestrator.initialized) else "down",
        "leader_elector": (
            "ok" if getattr(app.state, "leader_elector", None) is not None else "down"
        ),
    }
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("orchestration-service")


@app.get("/health/ready")
async def readiness(request: Request) -> dict[str, bool | dict[str, bool]]:
    leader_elector = getattr(request.app.state, "leader_elector", None)
    leader_ready = leader_elector.is_leader if leader_elector else True
    orchestrator = getattr(request.app.state, "orchestrator", None)
    checks = {"orchestrator": bool(orchestrator and orchestrator.initialized), "leader": leader_ready}
    ready = all(checks.values())
    if not ready:
        raise HTTPException(status_code=503, detail={"ready": ready, "checks": checks})
    return {"ready": ready, "checks": checks}


@api_router.get("/agents", response_model=list[str])
async def list_agents(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[str]:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    agents = sorted(orchestrator.agents.keys()) if orchestrator else []
    sliced = agents[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(agents))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.get("/dependencies", response_model=list[DependencyRequest])
async def list_dependencies(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DependencyRequest]:
    orchestrator = request.app.state.orchestrator
    deps = [
        DependencyRequest(agent_id=dep.agent_id, depends_on=dep.depends_on)
        for dep in orchestrator.list_dependencies()
    ]
    sliced = deps[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(deps))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.post("/dependencies", response_model=DependencyRequest)
async def register_dependency(payload: DependencyRequest, request: Request) -> DependencyRequest:
    orchestrator = request.app.state.orchestrator
    orchestrator.register_dependency(payload.agent_id, payload.depends_on)
    return payload


@api_router.get("/agents/{agent_id}/state", response_model=AgentStateResponse)
async def get_agent_state(agent_id: str, request: Request) -> AgentStateResponse:
    orchestrator = request.app.state.orchestrator
    state = orchestrator.get_agent_state(agent_id)
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")
    return AgentStateResponse(**state.__dict__)


@api_router.post("/agents/{agent_id}/activate", response_model=AgentStateResponse)
async def activate_agent(agent_id: str, request: Request) -> AgentStateResponse:
    auth = request.state.auth
    orchestrator = request.app.state.orchestrator
    if not orchestrator.dependencies_satisfied(agent_id):
        raise HTTPException(status_code=409, detail="Agent dependencies not satisfied")
    try:
        await orchestrator.enforce_policy(auth.tenant_id, agent_id, auth.roles)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    orchestrator.set_agent_state(agent_id, "running")
    state = orchestrator.get_agent_state(agent_id)
    return AgentStateResponse(**state.__dict__)


@api_router.post("/agents/{agent_id}/deactivate", response_model=AgentStateResponse)
async def deactivate_agent(agent_id: str, request: Request) -> AgentStateResponse:
    orchestrator = request.app.state.orchestrator
    orchestrator.set_agent_state(agent_id, "stopped")
    state = orchestrator.get_agent_state(agent_id)
    return AgentStateResponse(**state.__dict__)


@api_router.get("/agents/readiness", response_model=list[AgentReadinessResponse])
async def list_agent_readiness(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AgentReadinessResponse]:
    orchestrator = request.app.state.orchestrator
    reports = sorted(orchestrator.list_agent_readiness(), key=lambda report: report.agent_id)
    sliced = reports[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(reports))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    payload: list[AgentReadinessResponse] = []
    for report in sliced:
        state = orchestrator.get_agent_state(report.agent_id)
        status = state.status if state else ("running" if report.ready else "unknown")
        payload.append(
            AgentReadinessResponse(
                agent_id=report.agent_id,
                catalog_id=report.catalog_id,
                ready=report.ready,
                generated_at=report.generated_at,
                status=status,
                last_failure_reason=report.last_failure_reason,
                checks=[ReadinessCheckResponse(**check.model_dump()) for check in report.checks],
            )
        )
    return payload


@api_router.post("/workflows/upload", response_model=WorkflowUploadResponse)
async def upload_workflow(
    request: Request, file: UploadFile = File(...), workflow_name: str | None = None
) -> WorkflowUploadResponse:
    auth = request.state.auth
    orchestrator = request.app.state.orchestrator
    workflow_agent = orchestrator.agents.get("approval-workflow-agent")
    if not workflow_agent:
        raise HTTPException(status_code=503, detail="Approval workflow agent not available")
    bpmn_payload = (await file.read()).decode("utf-8")
    response = await workflow_agent.process(
        {
            "action": "deploy_bpmn_workflow",
            "tenant_id": auth.tenant_id,
            "bpmn_xml": bpmn_payload,
            "workflow_name": workflow_name or file.filename,
        }
    )
    return WorkflowUploadResponse(**response)


@api_router.post("/plans/{plan_id}/approve", response_model=PlanApprovalResponse)
async def approve_plan(
    plan_id: str, payload: PlanApprovalRequest, request: Request
) -> PlanApprovalResponse:
    auth = request.state.auth
    orchestrator = request.app.state.orchestrator
    response = await orchestrator.approve_plan(
        plan_id=plan_id,
        decision=payload.decision,
        tasks=payload.tasks,
        actor=payload.actor,
        context={"tenant_id": auth.tenant_id},
    )
    return PlanApprovalResponse(**response)


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
