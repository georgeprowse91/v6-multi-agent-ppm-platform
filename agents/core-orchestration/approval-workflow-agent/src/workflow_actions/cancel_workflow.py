"""Action handler: cancel_workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_cancel_workflow(
    agent: WorkflowEngineAgent, tenant_id: str, instance_id: str
) -> dict[str, Any]:
    """
    Cancel workflow instance.

    Returns cancellation confirmation.
    """
    agent.logger.info("Canceling workflow: %s", instance_id)

    instance = await agent._load_instance(tenant_id, instance_id)
    if not instance:
        raise ValueError(f"Workflow instance not found: {instance_id}")

    await agent._trigger_compensation(tenant_id, instance, reason="cancelled")

    # Update instance status
    instance["status"] = "cancelled"
    instance["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
    await agent._emit_workflow_event(tenant_id, "workflow.cancelled", {"instance_id": instance_id})
    await agent._send_notification(tenant_id, "workflow.cancelled", {"instance_id": instance_id})

    # Cancel pending tasks
    for task_id in instance.get("current_tasks", []):
        assignment = await agent._load_task_assignment(tenant_id, task_id)
        if assignment:
            assignment["status"] = "cancelled"
            assignment["cancelled_at"] = datetime.now(timezone.utc).isoformat()
            agent.task_assignments[task_id] = assignment
            await agent.state_store.save_task(tenant_id, task_id, assignment.copy())

    return {
        "instance_id": instance_id,
        "status": "cancelled",
        "cancelled_at": instance["cancelled_at"],
    }
