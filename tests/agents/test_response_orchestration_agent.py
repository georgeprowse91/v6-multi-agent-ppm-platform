import asyncio
import json

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
                    "financial-management": "http://test/financial",
                    "risk-management": "http://test/risk",
                },
                "http_client": client,
                "event_bus": event_bus,
            }
        )
        await agent.initialize()

        result = await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management"},
                    {
                        "agent_id": "risk-management",
                        "depends_on": ["financial-management"],
                    },
                ],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )
        payload = result.model_dump()

    assert payload["execution_summary"]["total_agents"] == 2
    assert invocation_order == ["/financial", "/risk"]
    assert any(event["agent_id"] == "financial-management" for event in events)
    assert "financial-management" in payload["aggregated_response"]


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
                "agent_endpoints": {"risk-management": "http://test/risk"},
                "http_client": client,
                "max_retries": 1,
                "retry_backoff_base": 0,
            }
        )
        await agent.initialize()
        result = await agent.process(
            {
                "routing": [{"agent_id": "risk-management"}],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )
        payload = result.model_dump()

    assert attempts["risk"] == 2
    assert payload["agent_results"][0]["success"] is True


@pytest.mark.asyncio
async def test_response_orchestration_cache_hits():
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"financial-management": "http://test/financial"},
                "http_client": client,
                "cache_ttl": 60,
            }
        )
        await agent.initialize()

        payload = {
            "routing": [{"agent_id": "financial-management"}],
            "parameters": {"project_id": "APOLLO"},
            "query": "test",
        }
        first = await agent.process(payload)
        second = await agent.process(payload)
        first_payload = first.model_dump()
        second_payload = second.model_dump()

    assert calls["count"] == 1
    assert first_payload["agent_results"][0]["success"] is True
    assert second_payload["agent_results"][0]["cached"] is True


@pytest.mark.asyncio
async def test_response_orchestration_timeout_failure():
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)
        return httpx.Response(200, json={"message": "late"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"risk-management": "http://test/risk"},
                "http_client": client,
                "agent_timeout": 0.001,
            }
        )
        await agent.initialize()
        result = await agent.process(
            {"routing": [{"agent_id": "risk-management"}], "parameters": {}, "query": "test"}
        )
        payload = result.model_dump()

    assert payload["agent_results"][0]["success"] is False


@pytest.mark.asyncio
async def test_response_orchestration_includes_prompt_metadata():
    captured_payload = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"risk-management": "http://test/risk"},
                "http_client": client,
            }
        )
        await agent.initialize()
        result = await agent.process(
            {
                "routing": [{"agent_id": "risk-management"}],
                "parameters": {},
                "query": "identify risks",
                "prompt_id": "risk_identification",
                "prompt_description": "Identify project risks and mitigations.",
                "prompt_tags": ["risk", "planning"],
            }
        )
        payload = result.model_dump()

    assert payload["agent_results"][0]["success"] is True
    assert captured_payload["parameters"]["prompt"]["id"] == "risk_identification"
    assert (
        captured_payload["parameters"]["prompt"]["description"]
        == "Identify project risks and mitigations."
    )


@pytest.mark.asyncio
async def test_response_orchestration_detects_dependency_cycle():
    agent = ResponseOrchestrationAgent()
    await agent.initialize()

    with pytest.raises(ValueError):
        await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management", "depends_on": ["risk-management"]},
                    {"agent_id": "risk-management", "depends_on": ["financial-management"]},
                ],
                "parameters": {},
                "query": "test",
            }
        )
