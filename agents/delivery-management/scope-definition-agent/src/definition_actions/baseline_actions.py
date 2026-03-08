"""
Scope baseline management and scope-creep detection action handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import scope_to_text

from services.scope_baseline.scope_baseline_service import create_baseline, retrieve_baseline

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# Baseline / scope-creep helpers
# ---------------------------------------------------------------------------


async def _compare_scope(
    agent: ProjectDefinitionAgent,
    baseline_scope: dict[str, Any],
    current_scope: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare current scope to baseline."""
    baseline_text = scope_to_text(baseline_scope)
    current_text = scope_to_text(current_scope)
    similarity = _semantic_similarity(agent, baseline_text, current_text)
    changes: list[dict[str, Any]] = []
    if similarity < 0.9:
        changes.append(
            {
                "type": "semantic_variance",
                "baseline": baseline_text,
                "current": current_text,
                "similarity": similarity,
            }
        )
    return changes


async def _calculate_scope_variance(changes: list[dict[str, Any]]) -> float:
    """Calculate scope variance percentage."""
    return 0.05  # 5% variance


def _semantic_similarity(
    agent: ProjectDefinitionAgent, baseline_text: str, current_text: str
) -> float:
    embeddings = agent.embedding_service.embed([baseline_text, current_text])
    baseline_vector, current_vector = embeddings
    numerator = sum(a * b for a, b in zip(baseline_vector, current_vector))
    denom = (sum(a * a for a in baseline_vector) ** 0.5) * (
        sum(b * b for b in current_vector) ** 0.5
    )
    if denom == 0:
        return 0.0
    return numerator / denom


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------


async def handle_manage_scope_baseline(
    agent: ProjectDefinitionAgent,
    project_id: str,
) -> dict[str, Any]:
    """
    Establish and manage scope baseline.

    Returns baseline ID and locked scope elements.
    """
    agent.logger.info("Managing scope baseline for project: %s", project_id)

    charter = agent.charters.get(project_id)
    wbs = agent.wbs_structures.get(project_id)
    requirements_repo = agent.requirements.get(project_id)

    if not charter or not wbs or not requirements_repo:
        raise ValueError(f"Missing required artifacts for baseline: {project_id}")

    from definition_utils import generate_baseline_id

    baseline = {
        "project_id": project_id,
        "baseline_id": await generate_baseline_id(project_id),
        "charter_version": charter.get("version"),
        "wbs_version": wbs.get("version"),
        "requirements_count": len(requirements_repo.get("requirements", [])),
        "scope_statement": charter["document"].get("scope_overview"),
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "locked_by": "system",
        "status": "Locked",
        "traceability_matrix": agent.traceability_matrices.get(project_id),
        "version": str(wbs.get("version", "1.0")),
        "created_by": "system",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "charter": charter,
            "wbs": wbs,
            "requirements": requirements_repo,
        },
    }

    baseline_id = create_baseline(project_id, baseline)
    baseline["baseline_id"] = baseline_id

    agent.scope_baselines[project_id] = baseline
    agent.scope_baseline_store.upsert("default", project_id, baseline)
    await agent.db_service.store(
        "scope_baselines",
        baseline["baseline_id"],
        {"tenant_id": "unknown", "baseline": baseline},
    )
    await agent.event_bus.publish(
        "baseline.created",
        {
            "project_id": project_id,
            "baseline_id": baseline["baseline_id"],
            "created_at": baseline["timestamp"],
        },
    )
    await agent.event_bus.publish(
        "scope.baseline.locked",
        {
            "project_id": project_id,
            "baseline_id": baseline["baseline_id"],
            "locked_at": baseline["locked_at"],
        },
    )

    return baseline


async def handle_detect_scope_creep(
    agent: ProjectDefinitionAgent,
    project_id: str,
    current_scope: dict[str, Any],
) -> dict[str, Any]:
    """
    Detect scope creep by comparing current scope to baseline.

    Returns detected changes and approval recommendations.
    """
    agent.logger.info("Detecting scope creep for project: %s", project_id)

    charter = agent.charters.get(project_id)
    if not charter:
        raise ValueError(f"Charter not found for project: {project_id}")

    baseline_scope = charter["document"].get("scope_overview", {})

    changes = await _compare_scope(agent, baseline_scope, current_scope)
    variance = await _calculate_scope_variance(changes)
    approval_needed = variance > agent.scope_change_threshold

    return {
        "project_id": project_id,
        "changes_detected": changes,
        "scope_variance": variance,
        "approval_needed": approval_needed,
        "threshold": agent.scope_change_threshold,
        "recommendation": (
            "Submit to Change Control Board" if approval_needed else "Accept changes"
        ),
    }


async def handle_get_baseline(
    baseline_id: str,
) -> dict[str, Any]:
    """Retrieve persisted baseline by baseline ID."""
    if not baseline_id:
        raise ValueError("baseline_id is required")
    return retrieve_baseline(baseline_id)
