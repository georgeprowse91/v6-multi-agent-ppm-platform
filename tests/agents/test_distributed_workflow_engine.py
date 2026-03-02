import pytest
from workflow_service_agent import WorkflowEngineAgent
from workflow_state_store import DatabaseWorkflowStateStore
from workflow_task_queue import InMemoryWorkflowTaskQueue


def _build_state_store(database_url: str, tmp_path):
    return DatabaseWorkflowStateStore(database_url)


@pytest.mark.asyncio
async def test_distributed_workflow_executes_across_workers(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path}/workflow.db"
    state_store = _build_state_store(database_url, tmp_path)
    task_queue = InMemoryWorkflowTaskQueue()

    agent_a = WorkflowEngineAgent(
        config={
            "workflow_state_store": state_store,
            "workflow_task_queue": task_queue,
            "worker_id": "worker-a",
        }
    )
    agent_b = WorkflowEngineAgent(
        config={
            "workflow_state_store": state_store,
            "workflow_task_queue": task_queue,
            "worker_id": "worker-b",
        }
    )

    await agent_a.initialize()
    await agent_b.initialize()

    workflow = await agent_a.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-distributed",
            "workflow": {
                "name": "Distributed Workflow",
                "tasks": [{"task_id": "auto-1", "type": "automated", "initial": True}],
            },
        }
    )

    instance = await agent_a.process(
        {
            "action": "start_workflow",
            "tenant_id": "tenant-distributed",
            "workflow_id": workflow["workflow_id"],
            "input_variables": {"requester": "ops"},
        }
    )

    result = await agent_b.run_worker_once()
    assert result is not None
    assert result["status"] == "completed"

    stored_instance = await state_store.get_instance("tenant-distributed", instance["instance_id"])
    assert stored_instance
    assert stored_instance["status"] == "completed"


@pytest.mark.asyncio
async def test_distributed_workflow_marks_failed_tasks(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path}/workflow-failure.db"
    state_store = _build_state_store(database_url, tmp_path)
    task_queue = InMemoryWorkflowTaskQueue()

    agent = WorkflowEngineAgent(
        config={
            "workflow_state_store": state_store,
            "workflow_task_queue": task_queue,
            "worker_id": "worker-failure",
        }
    )

    await agent.initialize()

    workflow = await agent.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-distributed",
            "workflow": {
                "name": "Failure Workflow",
                "tasks": [
                    {
                        "task_id": "auto-fail",
                        "type": "automated",
                        "initial": True,
                        "simulate_failure": True,
                    }
                ],
            },
        }
    )

    instance = await agent.process(
        {
            "action": "start_workflow",
            "tenant_id": "tenant-distributed",
            "workflow_id": workflow["workflow_id"],
            "input_variables": {"requester": "ops"},
        }
    )

    result = await agent.run_worker_once()
    assert result is not None
    assert result["status"] == "failed"

    task = await state_store.get_task("tenant-distributed", "auto-fail")
    assert task
    assert task["status"] == "failed"

    stored_instance = await state_store.get_instance("tenant-distributed", instance["instance_id"])
    assert stored_instance
    assert stored_instance["status"] == "failed"
