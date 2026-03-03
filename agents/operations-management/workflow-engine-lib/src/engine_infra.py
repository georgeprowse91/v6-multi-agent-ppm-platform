"""
Shared infrastructure helpers used by the WorkflowEngineAgent class.

These async functions operate on the agent instance and are called as
thin delegating methods from the main class.  Extracting them keeps
the class body under the target line budget.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from observability.tracing import get_trace_id
from workflow_task_queue import build_task_message

from agents.runtime.src.audit import build_audit_event, emit_audit_event

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


# ------------------------------------------------------------------
# Task execution
# ------------------------------------------------------------------


async def execute_task(
    agent: WorkflowEngineAgent, tenant_id: str, instance_id: str, task: dict[str, Any]
) -> None:
    """Execute workflow task."""
    task_id = task.get("task_id")

    # Create task assignment
    assignment = {
        "task_id": task_id,
        "instance_id": instance_id,
        "task_type": task.get("type"),
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_payload": task,
        "retry_policy": task.get("retry_policy"),
        "compensation_task_id": task.get("compensation_task_id"),
    }
    agent.task_assignments[task_id] = assignment
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())

    # Add to instance current tasks
    instance = await agent._load_instance(tenant_id, instance_id)
    if instance:
        instance.get("current_tasks", []).append(task_id)
        await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())

    await agent.task_queue.publish_task(
        build_task_message(
            tenant_id=tenant_id,
            instance_id=instance_id,
            task_id=task_id,
            task_type=task.get("type"),
            payload={"workflow_id": instance.get("workflow_id") if instance else None},
        )
    )


# ------------------------------------------------------------------
# Compensation
# ------------------------------------------------------------------


async def trigger_compensation(
    agent: WorkflowEngineAgent, tenant_id: str, instance: dict[str, Any], reason: str
) -> None:
    workflow_id = instance.get("workflow_id")
    workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
    if not workflow:
        return
    compensation_tasks = []
    completed_steps = list(instance.get("completed_steps", []))
    failed_steps = list(instance.get("failed_tasks", []))
    for task_id in completed_steps + failed_steps:
        task = next(
            (item for item in workflow.get("tasks", []) if item.get("task_id") == task_id),
            None,
        )
        if task and task.get("compensation_task_id"):
            comp_task = next(
                (
                    item
                    for item in workflow.get("tasks", [])
                    if item.get("task_id") == task.get("compensation_task_id")
                ),
                None,
            )
            if comp_task:
                compensation_tasks.append(comp_task)

    if not compensation_tasks:
        return

    instance["status"] = "compensating"
    await agent.state_store.save_instance(tenant_id, instance["instance_id"], instance.copy())
    await emit_workflow_event(
        agent,
        tenant_id,
        "workflow.compensation.started",
        {"instance_id": instance["instance_id"], "reason": reason},
    )
    await send_notification(
        agent,
        tenant_id,
        "workflow.compensation.started",
        {"instance_id": instance["instance_id"], "reason": reason},
    )

    for task in compensation_tasks:
        await execute_task(agent, tenant_id, instance["instance_id"], task)

    instance.setdefault("compensation_history", []).append(
        {
            "reason": reason,
            "tasks": [task.get("task_id") for task in compensation_tasks],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    await agent.state_store.save_instance(tenant_id, instance["instance_id"], instance.copy())
    await emit_workflow_event(
        agent,
        tenant_id,
        "workflow.compensation.completed",
        {
            "instance_id": instance["instance_id"],
            "tasks": [t.get("task_id") for t in compensation_tasks],
        },
    )
    await send_notification(
        agent,
        tenant_id,
        "workflow.compensation.completed",
        {
            "instance_id": instance["instance_id"],
            "tasks": [t.get("task_id") for t in compensation_tasks],
        },
    )


# ------------------------------------------------------------------
# Eventing / notifications / telemetry
# ------------------------------------------------------------------


async def emit_workflow_event(
    agent: WorkflowEngineAgent, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    """Emit workflow events for audit/analytics."""
    event_id = f"WF-EVT-{len(agent.workflow_instances) + 1}"
    event_record = {
        "event_id": event_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await agent.state_store.save_event(tenant_id, event_id, event_record)
    audit_event = build_audit_event(
        tenant_id=tenant_id,
        action=event_type,
        outcome="success",
        actor_id=agent.agent_id,
        actor_type="service",
        actor_roles=[],
        resource_id=payload.get("instance_id") or payload.get("workflow_id") or event_id,
        resource_type="workflow_event",
        metadata={"event_id": event_id},
        trace_id=get_trace_id(),
    )
    emit_audit_event(audit_event)
    if agent.event_bus:
        await agent.event_bus.publish("workflow.events", event_record)
        await agent.event_bus.publish("workflow.notifications", event_record)
    await _emit_monitor_telemetry(agent, tenant_id, event_type, payload)
    await _emit_event_grid_event(agent, tenant_id, event_type, payload)


async def _emit_monitor_telemetry(
    agent: WorkflowEngineAgent, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    if not agent.monitoring_enabled:
        return
    telemetry_payload = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "workflow_engine_agent",
    }
    if agent.event_bus:
        await agent.event_bus.publish("azure.monitor.telemetry", telemetry_payload)


async def _emit_event_grid_event(
    agent: WorkflowEngineAgent, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    if not agent.event_grid_enabled:
        return
    event_grid_payload = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "workflow_engine_agent",
    }
    if agent.event_bus:
        await agent.event_bus.publish("azure.eventgrid.events", event_grid_payload)


async def invoke_logic_app(
    agent: WorkflowEngineAgent, tenant_id: str, assignment: dict[str, Any]
) -> None:
    payload = {
        "tenant_id": tenant_id,
        "task_id": assignment.get("task_id"),
        "instance_id": assignment.get("instance_id"),
        "payload": assignment.get("task_payload", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if agent.logic_apps_endpoint:
        agent.logger.info(
            "Logic Apps invocation scheduled",
            extra={"endpoint": agent.logic_apps_endpoint, "task_id": assignment.get("task_id")},
        )
    if agent.event_bus:
        await agent.event_bus.publish("logic.apps.invocations", payload)


async def send_notification(
    agent: WorkflowEngineAgent, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    notification = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "workflow_engine_agent",
    }
    if agent.event_bus:
        await agent.event_bus.publish("workflow.notifications", notification)


# ------------------------------------------------------------------
# Event subscriptions
# ------------------------------------------------------------------


async def register_event_triggers(
    agent: WorkflowEngineAgent, tenant_id: str, workflow_id: str, triggers: list[dict[str, Any]]
) -> None:
    """Register event triggers for a workflow definition."""
    for trigger in triggers:
        subscription_id = f"SUB-{len(agent.event_subscriptions) + 1}"
        subscription = {
            "subscription_id": subscription_id,
            "workflow_id": workflow_id,
            "event_type": trigger.get("event_type"),
            "criteria": trigger.get("criteria", {}),
            "action": trigger.get("action", "start"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task_id": trigger.get("task_id"),
        }
        agent.event_subscriptions[subscription_id] = subscription
        await agent.state_store.save_subscription(
            tenant_id, subscription_id, subscription.copy()
        )


async def find_event_subscriptions(
    agent: WorkflowEngineAgent, tenant_id: str, event_type: str
) -> list[dict[str, Any]]:
    """Find workflows subscribed to event type."""
    subscriptions = await agent.state_store.list_subscriptions(tenant_id, event_type=event_type)
    for subscription in subscriptions:
        if subscription.get("subscription_id"):
            agent.event_subscriptions[subscription["subscription_id"]] = subscription
    return subscriptions
