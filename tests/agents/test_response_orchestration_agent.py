import httpx
import pytest
from response_orchestration_agent import ResponseOrchestrationAgent

from agents.runtime import InMemoryEventBus


@pytest.mark.asyncio
async def test_response_orchestration_http_and_events():
    events = []
    event_bus = InMemoryEventBus()

    async def capture_event(payload):
        events.append(payload)

    event_bus.subscribe("agent.completed", capture_event)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "ok", "agent": "financial"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"financial-management-agent": "http://test/agent"},
                "http_client": client,
                "event_bus": event_bus,
            }
        )
        await agent.initialize()

        result = await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management-agent"},
                    {"agent_id": "risk-management-agent"},
                ],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )

    assert result["execution_summary"]["total_agents"] == 2
    assert any(event["agent_id"] == "financial-management-agent" for event in events)
    assert "financial-management-agent" in result["aggregated_response"]
