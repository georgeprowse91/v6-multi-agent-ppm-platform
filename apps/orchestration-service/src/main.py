from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
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


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orchestration-service"


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
