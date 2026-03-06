"""Action handler: assign_task."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_assign_task(
    agent: WorkflowEngineAgent, tenant_id: str, task_id: str, assignee: str
) -> dict[str, Any]:
    """
    Assign task to user.

    Returns assignment confirmation.
    """
    agent.logger.info("Assigning task %s to %s", task_id, assignee)

    # Find task assignment
    assignment = await agent._load_task_assignment(tenant_id, task_id)
    if not assignment:
        assignment = {"task_id": task_id, "status": "assigned"}
    assignment["assignee"] = assignee
    assignment["assigned_at"] = datetime.now(timezone.utc).isoformat()
    agent.task_assignments[task_id] = assignment
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())
    await agent._send_notification(
        tenant_id,
        "workflow.task.assigned",
        {
            "task_id": task_id,
            "assignee": assignee,
            "instance_id": assignment.get("instance_id"),
        },
    )

    return {"task_id": task_id, "assignee": assignee, "assigned_at": assignment["assigned_at"]}
