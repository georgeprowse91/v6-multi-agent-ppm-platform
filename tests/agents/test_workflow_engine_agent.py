import pytest
from workflow_engine_agent import WorkflowEngineAgent
from workflow_task_queue import InMemoryWorkflowTaskQueue


@pytest.mark.asyncio
async def test_workflow_engine_bpmn_deploy_parses_tasks(tmp_path):
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

    bpmn_xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
      <bpmn:process id="process_1" isExecutable="true">
        <bpmn:startEvent id="start_event"/>
        <bpmn:userTask id="user_task" name="Approve Request"/>
        <bpmn:endEvent id="end_event"/>
        <bpmn:sequenceFlow id="flow1" sourceRef="start_event" targetRef="user_task"/>
        <bpmn:sequenceFlow id="flow2" sourceRef="user_task" targetRef="end_event"/>
      </bpmn:process>
    </bpmn:definitions>"""

    response = await agent.process(
        {"action": "deploy_bpmn_workflow", "tenant_id": "tenant-bpmn", "bpmn_xml": bpmn_xml}
    )
    assert response["workflow_id"]

    definition = await agent.state_store.get_definition("tenant-bpmn", response["workflow_id"])
    assert definition is not None
    tasks = definition.get("tasks", [])
    assert any(task["task_id"] == "user_task" for task in tasks)
    assert any(task["initial"] for task in tasks)


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
async def test_workflow_engine_resume_and_compensation(tmp_path):
    task_queue = InMemoryWorkflowTaskQueue()
    agent = WorkflowEngineAgent(
        config={
            "workflow_definition_store_path": tmp_path / "definitions.json",
            "workflow_instance_store_path": tmp_path / "instances.json",
            "workflow_event_store_path": tmp_path / "events.json",
            "workflow_subscription_store_path": tmp_path / "subscriptions.json",
            "workflow_task_store_path": tmp_path / "tasks.json",
            "workflow_task_queue": task_queue,
            "max_retry_attempts": 0,
        }
    )
    await agent.initialize()

    workflow = await agent.process(
        {
            "action": "define_workflow",
            "tenant_id": "tenant-workflow",
            "workflow": {
                "name": "Compensation Workflow",
                "tasks": [
                    {
                        "task_id": "fail-task",
                        "type": "automated",
                        "initial": True,
                        "simulate_failure": True,
                        "compensation_task_id": "rollback-task",
                    },
                    {"task_id": "rollback-task", "type": "automated"},
                ],
            },
        }
    )

    instance = await agent.process(
        {
            "action": "start_workflow",
            "tenant_id": "tenant-workflow",
            "workflow_id": workflow["workflow_id"],
            "input_variables": {"requester": "ops"},
        }
    )

    await agent.run_worker_once()

    failed_instance = await agent.state_store.get_instance(
        "tenant-workflow", instance["instance_id"]
    )
    assert failed_instance is not None
    assert failed_instance["status"] in {"failed", "retrying", "compensating"}
    assert failed_instance["last_checkpoint"] == "fail-task"

    compensation_task = await agent.state_store.get_task("tenant-workflow", "rollback-task")
    assert compensation_task is not None

    resumed = await agent.process(
        {
            "action": "resume_workflow",
            "tenant_id": "tenant-workflow",
            "instance_id": instance["instance_id"],
        }
    )

    assert resumed["status"] == "running"


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
