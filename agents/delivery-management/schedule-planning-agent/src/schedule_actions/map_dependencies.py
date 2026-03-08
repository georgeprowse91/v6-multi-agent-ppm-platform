"""Action handler for map_dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from schedule_utils import (
    persist_schedule,
    publish_dependency_added,
    publish_schedule_updated,
)

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def map_dependencies(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    dependencies: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Map task dependencies.

    Returns dependency network diagram.
    """
    agent.logger.info("Mapping dependencies for schedule: %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    # Validate dependencies
    validated_dependencies = await validate_dependencies(dependencies, schedule.get("tasks", []))

    # Detect circular dependencies
    circular_deps = await detect_circular_dependencies(validated_dependencies)

    if circular_deps:
        raise ValueError(f"Circular dependencies detected: {circular_deps}")

    # Update schedule with dependencies
    schedule["dependencies"] = validated_dependencies
    agent.dependencies[schedule_id] = validated_dependencies

    if agent.enable_persistence and agent._sql_engine:
        await persist_schedule(agent, schedule)

    for dependency in validated_dependencies:
        await publish_dependency_added(agent, schedule, dependency)

    # Generate network diagram data
    network_diagram = await generate_network_diagram(
        schedule.get("tasks", []), validated_dependencies
    )

    await publish_schedule_updated(agent, schedule, "dependencies.updated")

    return {
        "schedule_id": schedule_id,
        "dependencies": validated_dependencies,
        "dependency_count": len(validated_dependencies),
        "network_diagram": network_diagram,
        "circular_dependencies": circular_deps,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def validate_dependencies(
    dependencies: list[dict[str, Any]], tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Validate dependency definitions."""
    task_ids = {task["task_id"] for task in tasks}
    valid_dependencies = []

    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if pred in task_ids and succ in task_ids:
            valid_dependencies.append(dep)

    return valid_dependencies


async def detect_circular_dependencies(dependencies: list[dict[str, Any]]) -> list[str]:
    """Detect circular dependencies."""
    graph: dict[str, list[str]] = {}
    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if not pred or not succ:
            continue
        graph.setdefault(pred, []).append(succ)

    visiting: set[str] = set()
    visited: set[str] = set()
    cycles = []

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            cycles.append(" -> ".join(path + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for neighbor in graph.get(node, []):
            visit(neighbor, path + [node])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [])

    return cycles


async def generate_network_diagram(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate network diagram data."""
    return {"nodes": tasks, "edges": dependencies}
