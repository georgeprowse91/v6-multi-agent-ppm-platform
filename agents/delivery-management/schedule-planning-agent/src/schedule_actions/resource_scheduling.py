"""Action handler for resource_constrained_schedule and resource helpers."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from schedule_utils import (
    merge_external_resource_availability,
    normalize_resource_availability,
    parse_period_availability,
    persist_schedule,
    publish_schedule_updated,
)

from schedule_actions.create_schedule import calculate_project_duration
from schedule_actions.critical_path import forward_pass

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def resource_constrained_schedule(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    resources: dict[str, Any],
    *,
    tenant_id: str = "unknown",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create resource-constrained schedule.

    Returns optimized schedule respecting resource availability.
    """
    agent.logger.info("Creating resource-constrained schedule: %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    tasks = schedule.get("tasks", [])
    dependencies = schedule.get("dependencies", [])
    lookup_context = {
        **(context or {}),
        "tenant_id": tenant_id,
        "project_id": schedule.get("project_id"),
        "schedule_id": schedule_id,
    }

    # Get resource availability from Resource Management Agent
    resource_availability = await get_resource_availability(
        agent, resources, context=lookup_context
    )

    # Apply resource leveling
    leveled_schedule = await resource_leveling(agent, tasks, dependencies, resource_availability)

    # Recalculate critical path with resource constraints
    from schedule_actions.critical_path import calculate_critical_path

    resource_critical_path = await calculate_critical_path(agent, schedule_id)

    # Calculate resource utilization
    utilization = await calculate_resource_utilization(leveled_schedule, resource_availability)

    schedule["tasks"] = leveled_schedule
    schedule["resource_leveled_at"] = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )
    if agent.enable_persistence and agent._sql_engine:
        await persist_schedule(agent, schedule)
    await publish_schedule_updated(agent, schedule, "schedule.resource_leveled")

    return {
        "schedule_id": schedule_id,
        "leveled_schedule": leveled_schedule,
        "resource_critical_path": resource_critical_path,
        "resource_utilization": utilization,
        "schedule_extension_days": await calculate_schedule_extension(
            schedule.get("project_duration_days", 0), leveled_schedule
        ),
    }


# ---------------------------------------------------------------------------
# Resource helpers
# ---------------------------------------------------------------------------


async def get_resource_availability(
    agent: SchedulePlanningAgent,
    resources: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get and normalize resource availability from Resource Capacity management integrations."""
    context = context or {}
    tenant_id = context.get("tenant_id", "unknown")
    project_id = context.get("project_id")

    normalized = normalize_resource_availability(resources)
    resource_ids = [resource_id for resource_id in resources.keys() if isinstance(resource_id, str)]
    if not resource_ids:
        return normalized

    if not agent.resource_capacity_agent:
        for resource_id in resource_ids:
            normalized.setdefault(resource_id, {}).setdefault(
                "warning", "resource_capacity_unavailable"
            )
        return normalized

    for resource_id in resource_ids:
        try:
            response = await agent.resource_capacity_agent.process(
                {
                    "action": "get_availability",
                    "resource_id": resource_id,
                    "date_range": {},
                    "project_id": project_id,
                    "tenant_id": tenant_id,
                    "context": {
                        "tenant_id": tenant_id,
                        "project_id": project_id,
                    },
                }
            )
            normalized[resource_id] = merge_external_resource_availability(
                resource_id,
                normalized.get(resource_id, {}),
                response,
            )
        except Exception as exc:
            fallback = normalized.setdefault(
                resource_id, {"capacity": 1.0, "period_availability": {}}
            )
            fallback.setdefault("warning", "resource_capacity_fetch_failed")
            fallback["warning_details"] = str(exc)
    return normalized


async def resource_leveling(
    agent: SchedulePlanningAgent,
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    resource_availability: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply resource leveling using a simple RCPSP serial schedule generation scheme."""
    forward = await forward_pass(tasks, dependencies)
    capacities: dict[str, float] = {}
    period_capacities: dict[str, dict[int, float]] = {}
    for key, value in resource_availability.items():
        if isinstance(value, dict):
            capacities[key] = float(value.get("capacity", 1.0))
            period_capacities[key] = parse_period_availability(value.get("period_availability", {}))
        else:
            capacities[key] = float(value)
            period_capacities[key] = {}

    usage: dict[str, dict[int, float]] = {key: {} for key in capacities}
    task_map = {task["task_id"]: dict(task) for task in forward}
    predecessors: dict[str, list[str]] = {task["task_id"]: [] for task in forward}
    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if pred in predecessors and succ in task_map:
            predecessors[succ].append(pred)

    remaining = set(task_map.keys())
    scheduled: list[dict[str, Any]] = []
    time_cursor = 0

    def ready_tasks(current_time: int) -> list[dict[str, Any]]:
        ready = []
        for task_id in remaining:
            preds = predecessors.get(task_id, [])
            if all(task_map[p].get("resource_finish", 0) <= current_time for p in preds):
                ready.append(task_map[task_id])
        return ready

    while remaining:
        available = ready_tasks(time_cursor)
        if not available:
            time_cursor += 1
            continue

        available.sort(key=lambda t: (t.get("early_finish", 0), t.get("duration", 0)))
        for task in available:
            duration = max(1, int(math.ceil(float(task.get("duration", 0) or 0))))
            required_resources = task.get("resources", [{"id": "default", "units": 1.0}])
            start = max(time_cursor, int(task.get("early_start", 0)))
            while True:
                if resources_available(
                    usage,
                    capacities,
                    period_capacities,
                    required_resources,
                    start,
                    duration,
                ):
                    allocate_resources(usage, required_resources, start, duration)
                    task["resource_start"] = start
                    task["resource_finish"] = start + duration
                    scheduled.append(task)
                    remaining.remove(task["task_id"])
                    break
                start += 1
        time_cursor += 1

    return scheduled


async def calculate_resource_utilization(
    schedule: list[dict[str, Any]], resource_availability: dict[str, Any]
) -> dict[str, float]:
    """Calculate resource utilization percentages."""
    utilization: dict[str, float] = {}
    capacities: dict[str, float] = {}
    for key, value in resource_availability.items():
        capacities[key] = (
            float(value.get("capacity", 1.0)) if isinstance(value, dict) else float(value)
        )

    total_usage: dict[str, float] = {key: 0.0 for key in capacities}
    for task in schedule:
        duration = float(task.get("duration", 0) or 0)
        for resource in task.get("resources", []):
            resource_id = resource.get("id")
            units = float(resource.get("units", 1.0))
            if resource_id in total_usage:
                total_usage[resource_id] += units * duration

    for resource_id, used in total_usage.items():
        capacity = capacities.get(resource_id, 1.0)
        utilization[resource_id] = used / max(capacity, 1.0)

    return utilization


async def calculate_schedule_extension(
    original_duration: float, leveled_schedule: list[dict[str, Any]]
) -> float:
    """Calculate schedule extension from resource leveling."""
    new_duration = await calculate_project_duration(leveled_schedule)
    return new_duration - original_duration


def resources_available(
    usage: dict[str, dict[int, float]],
    capacities: dict[str, float],
    period_capacities: dict[str, dict[int, float]],
    required: list[dict[str, Any]],
    start: int,
    duration: int,
) -> bool:
    for resource in required:
        resource_id = resource.get("id", "default")
        units = float(resource.get("units", 1.0))
        default_capacity = capacities.get(resource_id, 1.0)
        by_period = period_capacities.get(resource_id, {})
        for day in range(start, start + duration):
            capacity = by_period.get(day, default_capacity)
            used = usage.get(resource_id, {}).get(day, 0.0)
            if used + units > capacity:
                return False
    return True


def allocate_resources(
    usage: dict[str, dict[int, float]],
    required: list[dict[str, Any]],
    start: int,
    duration: int,
) -> None:
    for resource in required:
        resource_id = resource.get("id", "default")
        units = float(resource.get("units", 1.0))
        usage.setdefault(resource_id, {})
        for day in range(start, start + duration):
            usage[resource_id][day] = usage[resource_id].get(day, 0.0) + units
