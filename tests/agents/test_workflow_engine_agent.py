import pytest

from workflow_engine_agent import WorkflowEngineAgent
from workflow_task_queue import InMemoryWorkflowTaskQueue


@pytest.mark.asyncio
async def test_workflow_engine_persists_and_handles_events(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
        }
    )
    await agent.initialize()

    workflow = await agent.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-workflow",
            "workflow": {
                "name": "Improvement Workflow",
                "tasks": [{"task_id": "t1", "type": "human", "initial": True}],
                "event_triggers": [
                    {"event_type": "workflow.improvement.recommendation", "action": "start"}
                ],
            },
        }
    )
    assert workflow["workflow_id"]

    await agent.process(
        {
            "action": "handle_event",
            "tenant_id": "tenant-workflow",
            "event": {
                "event_type": "workflow.improvement.recommendation",
                "data": {"requester": "ops"},
            },
        }
    )

    instances = await agent.state_store.list_instances("tenant-workflow")
    assert instances
    events = await agent.state_store.list_events("tenant-workflow")
    assert events


@pytest.mark.asyncio
async def test_workflow_engine_instances_success(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
        }
    )
    await agent.initialize()

    response = await agent.process(
        {"action": "get_workflow_instances", "tenant_id": "tenant-workflow"}
    )

    assert "instances" in response


@pytest.mark.asyncio
async def test_workflow_engine_trigger_task_event_executes_automated_task(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
        }
    )
    await agent.initialize()

    workflow = await agent.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-workflow",
            "workflow": {
                "name": "Event Triggered Workflow",
                "tasks": [{"task_id": "auto-task", "type": "automated"}],
                "event_triggers": [
                    {
                        "event_type": "workflow.task.trigger",
                        "action": "trigger_task",
                        "task_id": "auto-task",
                    }
                ],
            },
        }
    )

    instance = await agent.process(
        {
            "action": "start_workflow",
            "tenant_id": "tenant-workflow",
            "workflow_id": workflow["workflow_id"],
            "input": {"requester": "ops"},
        }
    )

    await agent.process(
        {
            "action": "handle_event",
            "tenant_id": "tenant-workflow",
            "event": {
                "event_type": "workflow.task.trigger",
                "data": {
                    "instance_id": instance["instance_id"],
                    "task_id": "auto-task",
                },
            },
        }
    )

    await agent.run_worker_once()

    assignment = await agent.state_store.get_task("tenant-workflow", "auto-task")
    assert assignment is not None
    assert assignment["status"] == "completed"


@pytest.mark.asyncio
async def test_workflow_engine_validation_rejects_invalid_action(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_workflow_engine_validation_rejects_missing_fields(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "define_workflow"})

    assert valid is False
