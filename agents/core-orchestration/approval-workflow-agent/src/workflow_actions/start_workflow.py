"""Action handler: start_workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine_utils import generate_instance_id

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_start_workflow(
    agent: WorkflowEngineAgent,
    tenant_id: str,
    workflow_id: str,
    input_variables: dict[str, Any],
) -> dict[str, Any]:
    """
    Start workflow instance.

    Returns instance ID and initial state.
    """
    agent.logger.info("Starting workflow instance: %s", workflow_id)

    # Get workflow definition
    workflow = await agent._load_definition(tenant_id, workflow_id)
    if not workflow:
        raise ValueError(f"Workflow not found: {workflow_id}")

    # Generate instance ID
    instance_id = await generate_instance_id()

    # Initialize workflow state
    instance = {
        "instance_id": instance_id,
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "workflow_version": workflow.get("version"),
        "status": "running",
        "current_tasks": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "completed_steps": [],
        "checkpoints": [],
        "last_checkpoint": None,
        "compensation_history": [],
        "orchestration": {
            "engine": "durable_functions",
            "orchestration_id": f"durable-{instance_id}",
            "workflow_orchestration": workflow.get("orchestration"),
        },
        "variables": input_variables,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_by": input_variables.get("requester"),
        "history": [],
    }

    # Store instance
    agent.workflow_instances[instance_id] = instance
    await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())

    await agent._emit_workflow_event(
        tenant_id,
        "workflow.started",
        {"workflow_id": workflow_id, "instance_id": instance_id},
    )

    # Execute first tasks
    initial_tasks = await _get_initial_tasks(workflow)
    for task in initial_tasks:
        await agent._execute_task(tenant_id, instance_id, task)

    return {
        "instance_id": instance_id,
        "workflow_id": workflow_id,
        "status": "running",
        "current_tasks": instance["current_tasks"],
        "started_at": instance["started_at"],
    }


async def _get_initial_tasks(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Get initial tasks to execute."""
    tasks = workflow.get("tasks", [])
    initial = [t for t in tasks if t.get("initial", False)]
    if initial:
        return initial
    return tasks[:1]
