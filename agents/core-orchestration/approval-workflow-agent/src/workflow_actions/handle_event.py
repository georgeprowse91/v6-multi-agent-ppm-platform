"""Action handler: handle_event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine_utils import event_matches_criteria

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_handle_event(
    agent: WorkflowEngineAgent, tenant_id: str, event: dict[str, Any]
) -> dict[str, Any]:
    """
    Handle workflow event.

    Returns event handling result.
    """
    agent.logger.info("Handling event: %s", event.get("event_type"))

    event_type = event.get("event_type")
    event_data = event.get("data", {})
    if event_type in {"workflow.compensation.requested", "workflow.rollback.requested"}:
        return await _handle_compensation_event(agent, tenant_id, event_type, event_data)

    # Find subscribed workflows
    subscribed_workflows = await agent._find_event_subscriptions(tenant_id, event_type)  # type: ignore

    triggered_instances = []
    for subscription in subscribed_workflows:
        # Check if event matches subscription criteria
        if await event_matches_criteria(event_data, subscription.get("criteria", {})):
            # Start or advance workflow
            if subscription.get("action") == "start":
                from workflow_actions.start_workflow import handle_start_workflow

                result = await handle_start_workflow(
                    agent, tenant_id, subscription.get("workflow_id"), event_data  # type: ignore
                )
                triggered_instances.append(result.get("instance_id"))
            elif subscription.get("action") == "trigger_task":
                instance_id = event_data.get("instance_id")
                task_id = event_data.get("task_id") or subscription.get("task_id")
                if not instance_id or not task_id:
                    continue
                instance = await agent._load_instance(tenant_id, instance_id)
                if not instance:
                    continue
                workflow_id = instance.get("workflow_id") or subscription.get("workflow_id")
                workflow = await agent._load_definition(tenant_id, workflow_id)
                if not workflow:
                    continue
                task = next(
                    (
                        item
                        for item in workflow.get("tasks", [])
                        if item.get("task_id") == task_id
                    ),
                    None,
                )
                if not task:
                    continue
                await agent._execute_task(tenant_id, instance_id, task)
                triggered_instances.append(instance_id)

    await agent._emit_workflow_event(
        tenant_id,
        "workflow.event.handled",
        {"event_type": event_type, "instances_triggered": triggered_instances},
    )

    return {
        "event_type": event_type,
        "subscriptions_matched": len(subscribed_workflows),
        "instances_triggered": len(triggered_instances),
        "triggered_instances": triggered_instances,
    }


async def _handle_compensation_event(
    agent: WorkflowEngineAgent,
    tenant_id: str,
    event_type: str,
    event_data: dict[str, Any],
) -> dict[str, Any]:
    instance_id = event_data.get("instance_id")
    if not instance_id:
        raise ValueError("instance_id is required for compensation events")
    instance = await agent._load_instance(tenant_id, instance_id)
    if not instance:
        raise ValueError(f"Workflow instance not found: {instance_id}")
    await agent._trigger_compensation(tenant_id, instance, reason=event_type)
    return {"instance_id": instance_id, "status": "compensation_triggered"}
