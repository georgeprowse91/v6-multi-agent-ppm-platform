from __future__ import annotations

import httpx
import pytest
from response_orchestration_agent import ResponseOrchestrationAgent

from tests.helpers.service_bus import build_test_event_bus


@pytest.mark.asyncio
async def test_plan_is_created_as_pending_approval(tmp_path) -> None:
    event_bus = build_test_event_bus()
    agent = ResponseOrchestrationAgent(
        config={"event_bus": event_bus, "plans_dir": str(tmp_path), "require_approval": True}
    )
    await agent.initialize()

    response = await agent.process(
        {
            "routing": [{"agent_id": "financial-management"}],
            "parameters": {"project_id": "APOLLO"},
            "query": "build plan",
        }
    )

    payload = response.model_dump()
    assert payload["status"] == "pending_approval"
    assert payload["plan"]["status"] == "pending_approval"
    assert payload["agent_results"] == []


@pytest.mark.asyncio
async def test_approving_updated_plan_executes_modified_tasks(tmp_path) -> None:
    events: list[dict[str, object]] = []
    event_bus = build_test_event_bus()

    async def on_plan_approved(payload: dict[str, object]) -> None:
        events.append(payload)

    event_bus.subscribe("plan.approved", on_plan_approved)

    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"message": "ok", "agent": request.url.path})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        agent = ResponseOrchestrationAgent(
            config={
                "event_bus": event_bus,
                "plans_dir": str(tmp_path),
                "require_approval": True,
                "http_client": client,
                "agent_endpoints": {
                    "financial-management": "http://test/financial",
                    "risk-management": "http://test/risk",
                },
            }
        )
        await agent.initialize()

        pending = await agent.process(
            {
                "routing": [
                    {"agent_id": "financial-management"},
                    {"agent_id": "risk-management"},
                ],
                "parameters": {"project_id": "APOLLO"},
                "query": "build plan",
            }
        )

        plan_id = pending.plan["plan_id"]
        approved = await agent.process(
            {
                "routing": [],
                "plan_id": plan_id,
                "approval_decision": "approve",
                "approval_actor": "planner-ui",
                "plan_updates": [
                    {
                        "task_id": "task-2",
                        "agent_id": "risk-management",
                        "action": None,
                        "dependencies": [],
                        "metadata": {},
                    }
                ],
                "parameters": {"project_id": "APOLLO"},
                "query": "approve plan",
            }
        )

    payload = approved.model_dump()
    assert payload["status"] == "completed"
    assert payload["execution_summary"]["total_agents"] == 1
    assert calls == ["/risk"]
    assert events
    assert events[0]["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_rejected_plan_emits_event_and_does_not_execute(tmp_path) -> None:
    events: list[dict[str, object]] = []
    event_bus = build_test_event_bus()

    async def on_plan_rejected(payload: dict[str, object]) -> None:
        events.append(payload)

    event_bus.subscribe("plan.rejected", on_plan_rejected)

    agent = ResponseOrchestrationAgent(
        config={"event_bus": event_bus, "plans_dir": str(tmp_path), "require_approval": True}
    )
    await agent.initialize()

    pending = await agent.process(
        {
            "routing": [{"agent_id": "financial-management"}],
            "parameters": {},
            "query": "build plan",
        }
    )
    plan_id = pending.plan["plan_id"]

    rejected = await agent.process(
        {
            "routing": [],
            "plan_id": plan_id,
            "approval_decision": "reject",
            "approval_actor": "planner-ui",
            "parameters": {},
            "query": "reject plan",
        }
    )

    payload = rejected.model_dump()
    assert payload["status"] == "rejected"
    assert payload["agent_results"] == []
    assert events
    assert events[0]["plan_id"] == plan_id
