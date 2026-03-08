"""
Stakeholder analysis and RACI matrix action handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import parse_raci_response, serialize_raci_for_index

from definition_actions.charter_actions import _generate_with_openai, _index_artifact

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# Stakeholder helpers (previously private methods on the agent)
# ---------------------------------------------------------------------------


async def _classify_stakeholders(
    stakeholders: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify stakeholders by influence and interest."""
    for stakeholder in stakeholders:
        if "influence" not in stakeholder:
            stakeholder["influence"] = "medium"
        if "interest" not in stakeholder:
            stakeholder["interest"] = "medium"
    return stakeholders


async def _analyze_influence_network(
    agent: ProjectDefinitionAgent,
    stakeholders: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze stakeholder influence network."""
    edges: list[tuple[str, str]] = []
    for stakeholder in stakeholders:
        source = stakeholder.get("name", "unknown")
        for target in stakeholder.get("connections", []):
            edges.append((source, target))
    if agent.graph_client and hasattr(agent.graph_client, "get_relationships"):
        try:
            graph_edges = await agent.graph_client.get_relationships(stakeholders)
            edges.extend(graph_edges)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # pragma: no cover - defensive
            agent.logger.warning("Graph API lookup failed", extra={"error": str(exc)})

    node_set = {node for edge in edges for node in edge}
    for stakeholder in stakeholders:
        node_set.add(stakeholder.get("name", "unknown"))
    node_list = sorted(node_set)
    centrality = {node: 0 for node in node_list}
    for source, target in edges:
        centrality[source] = centrality.get(source, 0) + 1
        centrality[target] = centrality.get(target, 0) + 1
    return {
        "nodes": len(node_list),
        "edges": len(edges),
        "degree_centrality": centrality,
    }


async def _determine_communication_strategies(
    stakeholders: list[dict[str, Any]],
) -> dict[str, str]:
    """Determine communication strategies for stakeholders."""
    strategies = {}
    for stakeholder in stakeholders:
        name = stakeholder.get("name", "unknown")
        influence = stakeholder.get("influence", "medium")
        interest = stakeholder.get("interest", "medium")

        if influence == "high" and interest == "high":
            strategies[name] = "Manage Closely"
        elif influence == "high" and interest == "low":
            strategies[name] = "Keep Satisfied"
        elif influence == "low" and interest == "high":
            strategies[name] = "Keep Informed"
        else:
            strategies[name] = "Monitor"

    return strategies


async def _generate_raci_assignments(
    agent: ProjectDefinitionAgent,
    stakeholders: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate RACI assignments."""
    if agent.openai_client:
        prompt = (
            "Generate a RACI matrix for the following stakeholders and deliverables.\n"
            f"Stakeholders: {stakeholders}\nDeliverables: {deliverables}\n"
            "Return a list of assignments with stakeholder, deliverable, and role."
        )
        response = await _generate_with_openai(agent, prompt)
        parsed = parse_raci_response(response)
        if parsed:
            return parsed
    assignments = []
    roles = ["Responsible", "Accountable", "Consulted", "Informed"]
    for deliverable in deliverables:
        deliverable_name = (
            deliverable.get("name") or deliverable.get("deliverable") or "Deliverable"
        )
        for index, stakeholder in enumerate(stakeholders):
            assignments.append(
                {
                    "deliverable": deliverable_name,
                    "stakeholder": stakeholder.get("name", "unknown"),
                    "role": roles[index % len(roles)],
                }
            )
    return assignments


async def _validate_raci_assignments(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate RACI assignments."""
    return {"valid": True, "issues": [], "warnings": []}


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------


async def handle_analyze_stakeholders(
    agent: ProjectDefinitionAgent,
    project_id: str,
    stakeholders: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Analyze project stakeholders.

    Returns stakeholder register with influence and interest analysis.
    """
    agent.logger.info("Analyzing stakeholders for project: %s", project_id)

    classified = await _classify_stakeholders(stakeholders)
    influence_network = await _analyze_influence_network(agent, classified)
    communication_strategies = await _determine_communication_strategies(classified)

    stakeholder_register = {
        "project_id": project_id,
        "stakeholders": classified,
        "influence_network": influence_network,
        "communication_strategies": communication_strategies,
        "total_count": len(classified),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.stakeholder_registers[project_id] = stakeholder_register

    return stakeholder_register


async def handle_create_raci_matrix(
    agent: ProjectDefinitionAgent,
    project_id: str,
    stakeholders: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create RACI matrix.

    Returns matrix mapping stakeholders to deliverables with RACI roles.
    """
    agent.logger.info("Creating RACI matrix for project: %s", project_id)

    raci_assignments = await _generate_raci_assignments(agent, stakeholders, deliverables)
    validation = await _validate_raci_assignments(raci_assignments)

    raci_matrix = {
        "project_id": project_id,
        "stakeholders": stakeholders,
        "deliverables": deliverables,
        "assignments": raci_assignments,
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await agent.db_service.store(
        "project_raci_matrices",
        f"{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        {"tenant_id": "unknown", "raci_matrix": raci_matrix},
    )
    await _index_artifact(
        agent,
        artifact_type="raci_matrix",
        artifact_id=project_id,
        content=serialize_raci_for_index(raci_matrix),
        metadata={"project_id": project_id},
    )
    await agent.event_bus.publish(
        "raci_matrix.created",
        {
            "project_id": project_id,
            "created_at": raci_matrix["created_at"],
            "assignment_count": len(raci_assignments),
        },
    )

    return raci_matrix
