"""Action handlers: get_workflow_instances, get_task_inbox."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine_utils import matches_instance_filters

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_get_workflow_instances(
    agent: WorkflowEngineAgent, tenant_id: str, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Get workflow instances with filters.

    Returns list of instances.
    """
    agent.logger.info("Retrieving workflow instances")

    # Filter instances
    filtered = []
    instances = await agent.state_store.list_instances(tenant_id)
    for instance in instances:
        instance_id = instance.get("instance_id")
        if await matches_instance_filters(instance, filters):
            filtered.append(
                {
                    "instance_id": instance_id,
                    "workflow_id": instance.get("workflow_id"),
                    "status": instance.get("status"),
                    "started_at": instance.get("started_at"),
                    "completed_at": instance.get("completed_at"),
                }
            )

    # Sort by start date
    filtered.sort(key=lambda x: x.get("started_at", ""), reverse=True)

    return {"total_instances": len(filtered), "instances": filtered, "filters": filters}


async def handle_get_task_inbox(
    agent: WorkflowEngineAgent, tenant_id: str, user_id: str
) -> dict[str, Any]:
    """
    Get user's pending tasks.

    Returns task list.
    """
    agent.logger.info("Retrieving task inbox for user: %s", user_id)

    # Find tasks assigned to user
    user_tasks = []
    tasks = await agent.state_store.list_tasks(tenant_id, assignee=user_id, status="assigned")
    for assignment in tasks:
        if assignment.get("assignee") == user_id and assignment.get("status") == "assigned":
            user_tasks.append(
                {
                    "task_id": assignment.get("task_id"),
                    "instance_id": assignment.get("instance_id"),
                    "assigned_at": assignment.get("assigned_at"),
                    "task_type": assignment.get("task_type"),
                }
            )

    # Sort by assigned date
    user_tasks.sort(key=lambda x: x.get("assigned_at", ""))

    return {"user_id": user_id, "pending_tasks": len(user_tasks), "tasks": user_tasks}
