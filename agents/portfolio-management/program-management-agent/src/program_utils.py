"""
Utility functions for the Program Management Agent.

Contains pure or near-pure helpers: date parsing, graph construction,
overlap detection, critical-path calculation, resource flattening,
alignment-term extraction, and schedule-building helpers.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def parse_date(date_value: str | None) -> datetime | None:
    """Parse an ISO or ``%Y-%m-%d`` date string into a datetime."""
    if not date_value:
        return None
    try:
        return datetime.fromisoformat(date_value)
    except ValueError:
        try:
            return datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# Resource helpers
# ---------------------------------------------------------------------------


def flatten_resource_allocations(allocation: Any) -> list[str]:
    """Flatten heterogeneous allocation data into a flat list of resource identifiers."""
    if isinstance(allocation, dict):
        resources: list[str] = []
        for key, value in allocation.items():
            if isinstance(value, (list, tuple, set)):
                resources.extend(str(item) for item in value)
            elif isinstance(value, dict):
                resources.append(str(value.get("resource_id") or value.get("name") or key))
            else:
                resources.append(str(key))
        return resources
    if isinstance(allocation, list):
        resources = []
        for item in allocation:
            if isinstance(item, dict):
                resources.append(
                    str(item.get("resource_id") or item.get("name") or item.get("role"))
                )
            else:
                resources.append(str(item))
        return resources
    return [str(allocation)] if allocation else []


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def extract_dependency_edges(dependency: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract (predecessor, successor) edge tuples from a dependency dict."""
    if dependency.get("predecessor") and dependency.get("successor"):
        return [(dependency["predecessor"], dependency["successor"])]
    if dependency.get("from") and dependency.get("to"):
        return [(dependency["from"], dependency["to"])]
    if dependency.get("source") and dependency.get("target"):
        return [(dependency["source"], dependency["target"])]
    if dependency.get("project_id") and dependency.get("depends_on"):
        depends_on = dependency["depends_on"]
        if isinstance(depends_on, list):
            return [(dep, dependency["project_id"]) for dep in depends_on]
        return [(depends_on, dependency["project_id"])]
    return []


def build_dependency_graph(
    dependencies: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], set[str]]:
    """Build an adjacency-list graph and node set from a list of dependencies."""
    graph: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for dependency in dependencies:
        edges = extract_dependency_edges(dependency)
        for predecessor, successor in edges:
            nodes.update([predecessor, successor])
            graph.setdefault(predecessor, []).append(successor)
    for node in nodes:
        graph.setdefault(node, [])
    return graph, nodes


def calculate_critical_path(
    schedules: dict[str, Any], dependencies: list[dict[str, Any]]
) -> list[str]:
    """Calculate the critical path through the dependency graph using longest-path."""
    graph, nodes = build_dependency_graph(dependencies)
    if not nodes:
        nodes = set(schedules.keys())
        for node in nodes:
            graph.setdefault(node, [])

    durations: dict[str, float] = {}
    for node in nodes:
        schedule = schedules.get(node, {})
        start = schedule.get("start")
        end = schedule.get("end")
        duration = 0.0
        try:
            if start and end:
                duration = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
        except (TypeError, ValueError):
            duration = 0.0
        durations[node] = max(duration, 0.0)

    in_degree = {node: 0 for node in nodes}
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

    queue = [node for node in nodes if in_degree.get(node, 0) == 0]
    topo_order: list[str] = []
    while queue:
        current = queue.pop(0)
        topo_order.append(current)
        for neighbor in graph.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topo_order) != len(nodes):
        return []

    earliest_finish = {node: durations.get(node, 0.0) for node in nodes}
    predecessor: dict[str, str | None] = {node: None for node in nodes}

    for node in topo_order:
        for neighbor in graph.get(node, []):
            candidate_finish = earliest_finish[node] + durations.get(neighbor, 0.0)
            if candidate_finish > earliest_finish.get(neighbor, 0.0):
                earliest_finish[neighbor] = candidate_finish
                predecessor[neighbor] = node

    if not earliest_finish:
        return []

    end_node: str | None = max(earliest_finish, key=earliest_finish.get)  # type: ignore[arg-type]
    path: list[str] = []
    while end_node is not None:
        path.append(end_node)
        end_node = predecessor.get(end_node)

    return list(reversed(path))


# ---------------------------------------------------------------------------
# Overlap / conflict detection helpers
# ---------------------------------------------------------------------------


def detect_schedule_overlaps(
    project_ids: list[str], schedules: dict[str, Any]
) -> list[dict[str, Any]]:
    """Detect pairwise schedule overlaps between projects."""
    overlaps: list[dict[str, Any]] = []
    for project_a, project_b in combinations(project_ids, 2):
        schedule_a = schedules.get(project_a, {})
        schedule_b = schedules.get(project_b, {})
        start_a = parse_date(schedule_a.get("start"))
        end_a = parse_date(schedule_a.get("end"))
        start_b = parse_date(schedule_b.get("start"))
        end_b = parse_date(schedule_b.get("end"))
        if not (start_a and end_a and start_b and end_b):
            continue
        latest_start = max(start_a, start_b)
        earliest_end = min(end_a, end_b)
        if latest_start <= earliest_end:
            overlap_days = (earliest_end - latest_start).days + 1
            overlaps.append(
                {
                    "project_a": project_a,
                    "project_b": project_b,
                    "overlap_days": overlap_days,
                    "overlap_window": {
                        "start": latest_start.date().isoformat(),
                        "end": earliest_end.date().isoformat(),
                    },
                }
            )
    return overlaps


def detect_resource_overlaps(
    project_ids: list[str], allocations: dict[str, Any]
) -> list[dict[str, Any]]:
    """Detect shared-resource overlaps between projects."""
    overlaps: list[dict[str, Any]] = []
    resources_by_project = {
        project_id: set(flatten_resource_allocations(allocations.get(project_id, {})))
        for project_id in project_ids
    }
    for project_a, project_b in combinations(project_ids, 2):
        resources_a = resources_by_project.get(project_a, set())
        resources_b = resources_by_project.get(project_b, set())
        shared = resources_a.intersection(resources_b)
        if shared:
            overlap_score = len(shared) / max(1, len(resources_a | resources_b))
            overlaps.append(
                {
                    "project_a": project_a,
                    "project_b": project_b,
                    "shared_resources": sorted(shared),
                    "overlap_score": round(overlap_score, 3),
                }
            )
    return overlaps


def detect_resource_schedule_conflicts(
    schedule: dict[str, dict[str, Any]], resource_allocations: dict[str, Any]
) -> int:
    """Count resource-schedule conflict pairs in *candidate* schedule."""
    conflicts = 0
    for project_a, project_b in combinations(schedule.keys(), 2):
        data_a = schedule[project_a]
        data_b = schedule[project_b]
        if data_a["start"] <= data_b["end"] and data_b["start"] <= data_a["end"]:
            resources_a = set(flatten_resource_allocations(resource_allocations.get(project_a, {})))
            resources_b = set(flatten_resource_allocations(resource_allocations.get(project_b, {})))
            if resources_a.intersection(resources_b):
                conflicts += 1
    return conflicts


# ---------------------------------------------------------------------------
# Schedule building & scoring helpers
# ---------------------------------------------------------------------------


def build_initial_schedule(
    project_ids: list[str], schedules: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Build a schedule map (datetime-keyed) from raw schedule data."""
    schedule_map: dict[str, dict[str, Any]] = {}
    default_start = datetime.now(timezone.utc)
    for idx, project_id in enumerate(project_ids):
        schedule = schedules.get(project_id, {})
        start = parse_date(schedule.get("start")) or default_start + timedelta(days=30 * idx)
        end = parse_date(schedule.get("end")) or start + timedelta(days=180)
        schedule_map[project_id] = {
            "start": start,
            "end": end,
            "duration_days": max(1, (end - start).days),
        }
    return schedule_map


def normalize_objectives(
    objectives: dict[str, float], fallback: dict[str, float]
) -> dict[str, float]:
    """Normalize objective weights so they sum to 1.0."""
    total = sum(max(0.0, value) for value in objectives.values())
    if total == 0:
        return fallback
    return {key: max(0.0, value) / total for key, value in objectives.items()}


def extract_alignment_terms(text: str) -> set[str]:
    """Extract lowercase alphanumeric tokens from text."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))
