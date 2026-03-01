from pathlib import Path

import httpx
import pytest
import yaml
from plan_schema import Plan
from response_orchestration_agent import ResponseOrchestrationAgent

from tests.helpers.service_bus import build_test_event_bus


@pytest.mark.asyncio
async def test_plan_file_created_during_execution(tmp_path: Path):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"financial-management-agent": "http://test/financial"},
                "http_client": client,
                "plans_dir": str(tmp_path),
                "event_bus": build_test_event_bus(),
            }
        )
        await agent.initialize()
        response = await agent.process(
            {
                "routing": [{"agent_id": "financial-management-agent"}],
                "parameters": {"project_id": "APOLLO"},
                "query": "test",
            }
        )

    payload = response.model_dump()
    plan_id = payload["plan"]["plan_id"]
    assert (tmp_path / f"{plan_id}.yaml").exists()


@pytest.mark.asyncio
async def test_plan_payload_matches_schema(tmp_path: Path):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {
                    "financial-management-agent": "http://test/financial",
                    "risk-management-agent": "http://test/risk",
                },
                "http_client": client,
                "plans_dir": str(tmp_path),
                "event_bus": build_test_event_bus(),
            }
        )
        await agent.initialize()
        response = await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management-agent"},
                    {
                        "agent_id": "risk-management-agent",
                        "depends_on": ["financial-management-agent"],
                    },
                ],
                "parameters": {},
                "query": "test",
            }
        )

    plan_payload = response.model_dump()["plan"]
    parsed = Plan.model_validate(plan_payload)
    assert parsed.version >= 1
    assert parsed.tasks[1].dependencies == ["financial-management-agent"]


@pytest.mark.asyncio
async def test_loading_saved_plan_executes_same_steps(tmp_path: Path):
    called_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        called_paths.append(request.url.path)
        return httpx.Response(200, json={"message": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "agent_endpoints": {"financial-management-agent": "http://test/financial"},
                "http_client": client,
                "plans_dir": str(tmp_path),
                "event_bus": build_test_event_bus(),
                "cache_ttl": -1,
            }
        )
        await agent.initialize()

        first = await agent.process(
            {
                "routing": [{"agent_id": "financial-management-agent"}],
                "parameters": {},
                "query": "test",
            }
        )
        plan_id = first.model_dump()["plan"]["plan_id"]

        second = await agent.process(
            {
                "routing": [{"agent_id": "risk-management-agent"}],
                "plan_id": plan_id,
                "parameters": {},
                "query": "test",
            }
        )

    assert called_paths == ["/financial", "/financial"]
    assert first.model_dump()["aggregated_response"] == second.model_dump()["aggregated_response"]

    stored_plan_payload = yaml.safe_load((tmp_path / f"{plan_id}.yaml").read_text())
    assert Plan.model_validate(stored_plan_payload).plan_id == plan_id
