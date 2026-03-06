"""Action handler: retry_failed_task."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_retry_failed_task(
    agent: WorkflowEngineAgent, tenant_id: str, task_id: str
) -> dict[str, Any]:
    """
    Retry failed task.

    Returns retry result.
    """
    agent.logger.info("Retrying failed task: %s", task_id)

    assignment = await agent._load_task_assignment(tenant_id, task_id)
    if not assignment:
        raise ValueError(f"Task assignment not found: {task_id}")

    # Check retry count
    retry_count = assignment.get("retry_count", 0)
    if retry_count >= agent.max_retry_attempts:
        return {
            "task_id": task_id,
            "status": "max_retries_exceeded",
            "retry_count": retry_count,
        }

    # Reset task status
    assignment["status"] = "assigned"
    assignment["retry_count"] = retry_count + 1
    assignment["retried_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())
    await agent._send_notification(
        tenant_id,
        "workflow.task.retrying",
        {"task_id": task_id, "retry_count": assignment["retry_count"]},
    )

    # Re-execute task
    assignment.get("instance_id")

    return {"task_id": task_id, "status": "retrying", "retry_count": assignment["retry_count"]}
