from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
OBSERVABILITY_SRC = REPO_ROOT / "packages" / "observability" / "src"
AGENT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.extend([str(REPO_ROOT), str(OBSERVABILITY_SRC), str(AGENT_SRC)])

from workflow_engine_agent import WorkflowEngineAgent  # noqa: E402
from workflow_spec import parse_workflow_spec  # noqa: E402
from workflow_state_store import build_workflow_state_store  # noqa: E402
from workflow_task_queue import InMemoryWorkflowTaskQueue  # noqa: E402


@pytest.mark.anyio
async def test_parse_workflow_spec_builds_dependencies() -> None:
    spec = {
        "apiVersion": "ppm.workflow/v1",
        "kind": "Workflow",
        "metadata": {"name": "Parallel Example", "version": "1", "owner": "workflow-service"},
        "steps": [
            {"id": "start", "type": "task", "task_type": "automated", "initial": True},
            {
                "id": "fanout",
                "type": "parallel",
                "branches": [{"next": "branch-a"}, {"next": "branch-b"}],
            },
            {"id": "branch-a", "type": "task", "task_type": "automated", "next": "join"},
            {"id": "branch-b", "type": "task", "task_type": "automated", "next": "join"},
            {"id": "join", "type": "task", "task_type": "automated"},
        ],
    }

    parsed = parse_workflow_spec(spec)
    assert parsed.dependencies["join"] == ["branch-a", "branch-b"]


@pytest.mark.anyio
async def test_workflow_engine_executes_parallel_join(tmp_path: Path) -> None:
    state_store = build_workflow_state_store(
        {
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
        }
    )
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_state_store": state_store,
            "workflow_task_queue": task_queue,
            "event_bus": None,
        }
    )
    await agent.initialize()

    workflow_spec = {
        "workflow_id": "parallel-join",
        "apiVersion": "ppm.workflow/v1",
        "kind": "Workflow",
        "metadata": {"name": "Parallel Join", "version": "1", "owner": "workflow-service"},
        "steps": [
            {"id": "start", "type": "task", "task_type": "automated", "initial": True},
            {
                "id": "fanout",
                "type": "parallel",
                "branches": [{"next": "branch-a"}, {"next": "branch-b"}],
            },
            {"id": "branch-a", "type": "task", "task_type": "automated", "next": "join"},
            {"id": "branch-b", "type": "task", "task_type": "automated", "next": "join"},
            {"id": "join", "type": "task", "task_type": "automated"},
        ],
    }

    definition = await agent.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-1",
            "workflow": workflow_spec,
            "actor": {"id": "admin", "roles": ["workflow_admin"]},
        }
    )
    instance = await agent.process(
        {
            "action": "start_workflow",
            "tenant_id": "tenant-1",
            "workflow_id": definition["workflow_id"],
            "input_variables": {"budget": 5000},
            "actor": {"id": "operator", "roles": ["workflow_operator"]},
        }
    )

    while await agent.run_worker_once():
        continue

    stored_instance = await state_store.get_instance("tenant-1", instance["instance_id"])
    assert stored_instance is not None
    assert stored_instance["status"] == "completed"


@pytest.mark.anyio
async def test_event_criteria_positive_match() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})
    event_data = {
        "metadata": {"tenant_id": "tenant-1", "priority": 5},
        "payload": {"amount": 1200},
    }
    criteria = {
        "metadata.tenant_id": {"eq": "tenant-1"},
        "payload.amount": {"gt": 1000},
    }

    assert await agent._event_matches_criteria(event_data, criteria)


@pytest.mark.anyio
async def test_event_criteria_non_match() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})
    event_data = {"metadata": {"tenant_id": "tenant-2"}}
    criteria = {"metadata.tenant_id": {"eq": "tenant-1"}}

    assert not await agent._event_matches_criteria(event_data, criteria)


@pytest.mark.anyio
async def test_event_criteria_missing_field_non_match() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})
    event_data = {"metadata": {"tenant_id": "tenant-1"}}
    criteria = {"metadata.region": {"eq": "us-east"}}

    assert not await agent._event_matches_criteria(event_data, criteria)


@pytest.mark.anyio
async def test_event_criteria_multiple_conditions_combined() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})
    event_data = {
        "metadata": {"tenant_id": "tenant-1"},
        "payload": {
            "status": "approved",
            "tags": ["urgent", "finance"],
            "created_at": "2024-01-15T10:30:00Z",
        },
    }
    criteria = {
        "metadata.tenant_id": {"eq": "tenant-1"},
        "payload.status": {"in": ["approved", "completed"]},
        "payload.created_at": {"gte": "2024-01-01T00:00:00Z"},
        "payload.tags": {"in": ["finance"]},
    }

    assert await agent._event_matches_criteria(event_data, criteria)


@pytest.mark.anyio
async def test_event_criteria_malformed_definition_fails_closed() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})
    event_data = {"payload": {"amount": 10}}

    assert not await agent._event_matches_criteria(event_data, {"payload.amount": {"in": "10"}})
    assert not await agent._event_matches_criteria(event_data, {"payload.amount": {"unknown": 10}})
    assert not await agent._event_matches_criteria(event_data, {"payload.amount": {"gt": "abc"}})


@pytest.mark.anyio
async def test_event_criteria_empty_matches_all() -> None:
    agent = WorkflowEngineAgent(config={"event_bus": None})

    assert await agent._event_matches_criteria({"event": "anything"}, {})
