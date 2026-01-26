import httpx
import pytest
from response_orchestration_agent import ResponseOrchestrationAgent

from agents.runtime import InMemoryEventBus


@pytest.mark.asyncio
async def test_response_orchestration_dependency_dag():
    events = []
    event_bus = InMemoryEventBus()

    async def capture_event(payload):
        events.append(payload)

    event_bus.subscribe("agent.completed", capture_event)
    invocation_order = []

    async def handler(request: httpx.Request) -> httpx.Response:
        invocation_order.append(request.url.path)
        return httpx.Response(200, json={"message": "ok", "agent": request.url.path})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {
                    "financial-management-agent": "http://test/financial",
                    "risk-management-agent": "http://test/risk",
                },
                "http_client": client,
                "event_bus": event_bus,
            }
        )
        await agent.initialize()

        result = await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management-agent"},
                    {
                        "agent_id": "risk-management-agent",
                        "depends_on": ["financial-management-agent"],
                    },
                ],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )

    assert result["execution_summary"]["total_agents"] == 2
    assert invocation_order == ["/financial", "/risk"]
    assert any(event["agent_id"] == "financial-management-agent" for event in events)
    assert "financial-management-agent" in result["aggregated_response"]


@pytest.mark.asyncio
async def test_response_orchestration_retries():
    attempts = {"risk": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/risk":
            attempts["risk"] += 1
            if attempts["risk"] == 1:
                return httpx.Response(500, json={"message": "fail"})
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"risk-management-agent": "http://test/risk"},
                "http_client": client,
                "max_retries": 1,
                "retry_backoff_base": 0,
            }
        )
        await agent.initialize()
        result = await agent.process(
            {
                "routing": [{"agent_id": "risk-management-agent"}],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )

    assert attempts["risk"] == 2
    assert result["agent_results"][0]["success"] is True
