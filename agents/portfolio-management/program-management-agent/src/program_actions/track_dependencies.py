"""Action handler for tracking inter-project dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from program_utils import build_dependency_graph, calculate_critical_path

if TYPE_CHECKING:
    from program_management_agent import ProgramManagementAgent


async def handle_track_dependencies(
    agent: ProgramManagementAgent,
    program_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Track and analyze inter-project dependencies.

    Returns dependency graph and critical paths.
    """
    agent.logger.info("Tracking dependencies for program: %s", program_id)

    program = agent.program_store.get(tenant_id, program_id)
    if not program:
        raise ValueError(f"Program not found: {program_id}")

    constituent_projects = program.get("constituent_projects", [])

    # Identify all dependencies
    project_schedules = await agent._get_project_schedules(constituent_projects)
    resource_allocations = await agent._get_resource_allocations(constituent_projects)
    dependencies = await agent._identify_dependencies(
        constituent_projects,
        schedules=project_schedules,
        resource_allocations=resource_allocations,
    )
    agent.dependency_store.upsert(
        tenant_id, program_id, {"program_id": program_id, "dependencies": dependencies}
    )
    await agent._update_dependency_graph(program_id, dependencies, tenant_id=tenant_id)
    if agent.db_service:
        await agent.db_service.store(
            "program_dependencies",
            program_id,
            {"program_id": program_id, "dependencies": dependencies},
        )

    # Analyze dependency graph
    graph_analysis = await _analyze_dependency_graph(dependencies)

    # Identify critical dependencies
    critical_dependencies = await _identify_critical_dependencies(dependencies, graph_analysis)

    # Detect circular dependencies
    circular_deps = await _detect_circular_dependencies(dependencies)
    optimization = await _optimize_dependency_graph(dependencies, graph_analysis, circular_deps)

    return {
        "program_id": program_id,
        "dependencies": dependencies,
        "dependency_count": len(dependencies),
        "critical_dependencies": critical_dependencies,
        "circular_dependencies": circular_deps,
        "graph_analysis": graph_analysis,
        "recommendations": await _generate_dependency_recommendations(dependencies, circular_deps),
        "optimization": optimization,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _analyze_dependency_graph(dependencies: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze dependency graph structure."""
    graph, nodes = build_dependency_graph(dependencies)
    in_degree = {node: 0 for node in nodes}
    out_degree = {node: 0 for node in nodes}
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
            out_degree[node] = out_degree.get(node, 0) + 1
    return {
        "node_count": len(nodes),
        "edge_count": sum(len(edges) for edges in graph.values()),
        "adjacency_list": graph,
        "in_degree": in_degree,
        "out_degree": out_degree,
    }


async def _identify_critical_dependencies(
    dependencies: list[dict[str, Any]], graph_analysis: dict[str, Any]
) -> list[dict[str, Any]]:
    """Identify critical dependencies."""
    return []


async def _detect_circular_dependencies(
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect circular dependencies."""
    graph, nodes = build_dependency_graph(dependencies)
    visited: set[str] = set()
    visiting: set[str] = set()
    stack: list[str] = []
    cycles: list[dict[str, Any]] = []

    def dfs(node: str) -> None:
        visiting.add(node)
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor in visiting:
                cycle_start = stack.index(neighbor)
                cycles.append({"cycle": stack[cycle_start:] + [neighbor]})
            elif neighbor not in visited:
                dfs(neighbor)
        visiting.remove(node)
        visited.add(node)
        stack.pop()

    for node in nodes:
        if node not in visited:
            dfs(node)

    return cycles


async def _generate_dependency_recommendations(
    dependencies: list[dict[str, Any]], circular_deps: list[dict[str, Any]]
) -> list[str]:
    """Generate recommendations for dependency management."""
    recommendations: list[str] = []
    if circular_deps:
        recommendations.append("Resolve circular dependencies to avoid deadlocks")
    return recommendations


async def _optimize_dependency_graph(
    dependencies: list[dict[str, Any]],
    graph_analysis: dict[str, Any],
    circular_deps: list[dict[str, Any]],
) -> dict[str, Any]:
    graph = graph_analysis.get("adjacency_list", {})
    conflicts = []
    for node, neighbors in graph.items():
        if len(neighbors) > 3:
            conflicts.append(
                {
                    "node": node,
                    "issue": "Too many downstream dependencies",
                    "count": len(neighbors),
                }
            )
    critical_path = calculate_critical_path({}, dependencies)
    recommendations: list[str] = []
    if circular_deps:
        recommendations.append("Break circular dependencies to unblock delivery flow.")
    if conflicts:
        recommendations.append("Sequence downstream work to reduce dependency contention.")
    if critical_path:
        recommendations.append(f"Focus mitigation on critical path: {' > '.join(critical_path)}.")
    return {
        "conflicts": conflicts,
        "critical_path": critical_path,
        "recommendations": recommendations,
    }
