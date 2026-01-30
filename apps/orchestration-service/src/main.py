from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.logging import configure_logging  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from orchestrator import AgentOrchestrator  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from leader_election import build_leader_elector  # noqa: E402

logger = logging.getLogger("orchestration-service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Orchestration Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/health", "/healthz", "/health/ready"})
configure_tracing("orchestration-service")
configure_metrics("orchestration-service")
configure_logging("orchestration-service")
app.add_middleware(TraceMiddleware, service_name="orchestration-service")
app.add_middleware(RequestMetricsMiddleware, service_name="orchestration-service")

orchestrator = AgentOrchestrator()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orchestration-service"


class DependencyRequest(BaseModel):
    agent_id: str
    depends_on: list[str] = Field(default_factory=list)


class AgentStateResponse(BaseModel):
    agent_id: str
    status: str
    updated_at: str
    reason: str | None = None


@app.on_event("startup")
async def startup() -> None:
    await orchestrator.initialize()
    app.state.leader_elector = build_leader_elector("orchestration-service")
    app.state.leader_elector.start()
    logger.info("orchestrator_ready", extra={"agents": len(orchestrator.agents)})


@app.on_event("shutdown")
async def shutdown() -> None:
    leader_elector = getattr(app.state, "leader_elector", None)
    if leader_elector:
        leader_elector.stop()


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/health/ready")
async def readiness(request: Request) -> dict[str, bool | dict[str, bool]]:
    leader_elector = getattr(request.app.state, "leader_elector", None)
    leader_ready = leader_elector.is_leader if leader_elector else True
    checks = {"orchestrator": orchestrator.initialized, "leader": leader_ready}
    ready = all(checks.values())
    if not ready:
        raise HTTPException(status_code=503, detail={"ready": ready, "checks": checks})
    return {"ready": ready, "checks": checks}


@app.get("/agents", response_model=list[str])
async def list_agents() -> list[str]:
    return sorted(orchestrator.agents.keys())


@app.get("/dependencies", response_model=list[DependencyRequest])
async def list_dependencies() -> list[DependencyRequest]:
    return [
        DependencyRequest(agent_id=dep.agent_id, depends_on=dep.depends_on)
        for dep in orchestrator.list_dependencies()
    ]


@app.post("/dependencies", response_model=DependencyRequest)
async def register_dependency(payload: DependencyRequest) -> DependencyRequest:
    orchestrator.register_dependency(payload.agent_id, payload.depends_on)
    return payload


@app.get("/agents/{agent_id}/state", response_model=AgentStateResponse)
async def get_agent_state(agent_id: str) -> AgentStateResponse:
    state = orchestrator.get_agent_state(agent_id)
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")
    return AgentStateResponse(**state.__dict__)


@app.post("/agents/{agent_id}/activate", response_model=AgentStateResponse)
async def activate_agent(agent_id: str, request: Request) -> AgentStateResponse:
    auth = request.state.auth
    if not orchestrator.dependencies_satisfied(agent_id):
        raise HTTPException(status_code=409, detail="Agent dependencies not satisfied")
    try:
        await orchestrator.enforce_policy(auth.tenant_id, agent_id, auth.roles)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    orchestrator.set_agent_state(agent_id, "running")
    state = orchestrator.get_agent_state(agent_id)
    return AgentStateResponse(**state.__dict__)


@app.post("/agents/{agent_id}/deactivate", response_model=AgentStateResponse)
async def deactivate_agent(agent_id: str) -> AgentStateResponse:
    orchestrator.set_agent_state(agent_id, "stopped")
    state = orchestrator.get_agent_state(agent_id)
    return AgentStateResponse(**state.__dict__)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
