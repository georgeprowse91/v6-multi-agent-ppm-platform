import pytest
from workflow_engine_agent import WorkflowEngineAgent


@pytest.mark.asyncio
async def test_workflow_engine_persists_and_handles_events(tmp_path):
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
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

    instances = agent.workflow_instance_store.list("tenant-workflow")
    assert instances
    events = agent.workflow_event_store.list("tenant-workflow")
    assert events


@pytest.mark.asyncio
async def test_workflow_engine_instances_success(tmp_path):
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {"action": "get_workflow_instances", "tenant_id": "tenant-workflow"}
    )

    assert "instances" in response


@pytest.mark.asyncio
async def test_workflow_engine_validation_rejects_invalid_action(tmp_path):
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_workflow_engine_validation_rejects_missing_fields(tmp_path):
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "define_workflow"})

    assert valid is False
