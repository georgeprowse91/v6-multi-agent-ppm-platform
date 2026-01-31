from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from runtime import AgentRuntime

app = FastAPI(title="Agent Runtime Service", version="0.1.0")

runtime = AgentRuntime()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "agent-runtime"


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
    return HealthResponse()


@app.get("/agents")
async def list_agents() -> list[dict[str, Any]]:
    return runtime.list_agents()


@app.post("/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, request: AgentExecuteRequest) -> dict[str, Any]:
    try:
        return await runtime.execute_agent(agent_id, request.payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/orchestration/config", response_model=OrchestrationConfig)
async def get_orchestration_config() -> OrchestrationConfig:
    return OrchestrationConfig(**runtime.get_orchestration_config())


@app.put("/orchestration/config", response_model=OrchestrationConfig)
async def update_orchestration_config(config: OrchestrationConfig) -> OrchestrationConfig:
    runtime.set_orchestration_config(config.model_dump())
    return config


@app.post("/orchestration/run")
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


@app.get("/connectors")
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


@app.post("/connectors/{connector_id}/actions")
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


@app.post("/events/publish")
async def publish_event(request: EventPublishRequest) -> dict[str, Any]:
    await runtime.event_bus.publish(request.topic, request.payload)
    return {"published": True, "topic": request.topic}


@app.get("/events")
async def list_events(topic: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "topic": record.topic,
            "payload": record.payload,
            "published_at": record.published_at,
        }
        for record in runtime.event_bus.get_recent_events(topic)
    ]
