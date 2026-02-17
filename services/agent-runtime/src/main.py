from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from runtime import AgentRuntime  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)

from packages.version import API_VERSION  # noqa: E402

app = FastAPI(title="Agent Runtime Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
configure_tracing("agent-runtime")
configure_metrics("agent-runtime")
app.add_middleware(TraceMiddleware, service_name="agent-runtime")
app.add_middleware(RequestMetricsMiddleware, service_name="agent-runtime")
apply_api_governance(app, service_name="agent-runtime")

runtime = AgentRuntime()


@app.on_event("startup")
async def start_event_bus() -> None:
    if hasattr(runtime.event_bus, "start"):
        await runtime.event_bus.start()


@app.on_event("shutdown")
async def stop_event_bus() -> None:
    if hasattr(runtime.event_bus, "stop"):
        await runtime.event_bus.stop()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "agent-runtime"
    dependencies: dict[str, str] = Field(default_factory=dict)


class AgentExecuteRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class RoutingEntry(BaseModel):
    agent_id: str
    action: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    intent: str | None = None
    priority: float | None = None


class OrchestrationConfig(BaseModel):
    default_routing: list[RoutingEntry] = Field(default_factory=list)
    last_updated_by: str = "system"


class OrchestrationRunRequest(BaseModel):
    routing: list[RoutingEntry] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    context: dict[str, Any] | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None


class ConnectorActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EventPublishRequest(BaseModel):
    topic: str
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"event_bus": "ok" if runtime.event_bus else "down"}
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("agent-runtime")


@api_router.get("/agents")
async def list_agents() -> list[dict[str, Any]]:
    return runtime.list_agents()


@api_router.post("/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, request: AgentExecuteRequest) -> dict[str, Any]:
    try:
        return await runtime.execute_agent(agent_id, request.payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/orchestration/config", response_model=OrchestrationConfig)
async def get_orchestration_config() -> OrchestrationConfig:
    return OrchestrationConfig(**runtime.get_orchestration_config())


@api_router.put("/orchestration/config", response_model=OrchestrationConfig)
async def update_orchestration_config(config: OrchestrationConfig) -> OrchestrationConfig:
    runtime.set_orchestration_config(config.model_dump())
    return config


@api_router.post("/orchestration/run")
async def run_orchestration(request: OrchestrationRunRequest) -> dict[str, Any]:
    routing = request.routing
    if routing is None:
        routing = [
            RoutingEntry(**entry)
            for entry in runtime.get_orchestration_config().get("default_routing", [])
        ]
    if not routing:
        raise HTTPException(status_code=400, detail="No routing entries provided")

    payload = {
        "routing": [entry.model_dump() for entry in routing],
        "parameters": request.parameters,
        "query": request.query,
        "context": request.context,
        "correlation_id": request.correlation_id,
        "tenant_id": request.tenant_id,
    }
    return await runtime.execute_agent("response-orchestration", payload)


@api_router.get("/connectors")
async def list_connectors() -> list[dict[str, Any]]:
    return [
        {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "manifest_path": connector.manifest_path,
            "status": connector.status,
            "certification": connector.certification,
        }
        for connector in runtime.connector_registry.list_connectors()
    ]


@api_router.post("/connectors/{connector_id}/actions")
async def run_connector_action(
    connector_id: str, request: ConnectorActionRequest
) -> dict[str, Any]:
    try:
        return await runtime.connector_client.execute(
            connector_id=connector_id,
            action=request.action,
            payload=request.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/events/publish")
async def publish_event(request: EventPublishRequest) -> dict[str, Any]:
    await runtime.event_bus.publish(request.topic, request.payload)
    return {"published": True, "topic": request.topic}


@api_router.get("/events")
async def list_events(topic: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "topic": record.topic,
            "payload": record.payload,
            "published_at": record.published_at,
        }
        for record in runtime.event_bus.get_recent_events(topic)
    ]


app.include_router(api_router)
