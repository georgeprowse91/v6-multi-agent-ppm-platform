"""Action handler: get_workflow_status."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_get_workflow_status(
    agent: WorkflowEngineAgent, tenant_id: str, instance_id: str
) -> dict[str, Any]:
    """
    Get workflow instance status.

    Returns current state and progress.
    """
    agent.logger.info("Getting workflow status: %s", instance_id)

    instance = await agent._load_instance(tenant_id, instance_id)
    if not instance:
        raise ValueError(f"Workflow instance not found: {instance_id}")

    # Calculate progress
    workflow_id = instance.get("workflow_id")
    workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
    total_tasks = len(workflow.get("tasks", [])) if workflow else 0
    completed_tasks = len(instance.get("completed_tasks", []))
    progress_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    return {
        "instance_id": instance_id,
        "workflow_id": workflow_id,
        "status": instance.get("status"),
        "progress_percentage": progress_pct,
        "current_tasks": instance.get("current_tasks"),
        "completed_tasks": len(instance.get("completed_tasks", [])),
        "failed_tasks": len(instance.get("failed_tasks", [])),
        "started_at": instance.get("started_at"),
        "completed_at": instance.get("completed_at"),
    }
