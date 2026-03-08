"""
Scope research action handler -- generates scope proposals using optional external search.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import sanitize_search_query

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# Internal helpers that mirror the original private methods
# ---------------------------------------------------------------------------


async def _generate_scope_overview(charter_data: dict[str, Any]) -> dict[str, Any]:
    """Generate scope overview (thin wrapper kept for consistency)."""
    return {
        "in_scope": charter_data.get("in_scope", []),
        "out_of_scope": charter_data.get("out_of_scope", []),
        "deliverables": charter_data.get("deliverables", []),
    }


async def _extract_high_level_requirements(charter_data: dict[str, Any]) -> list[str]:
    """Extract high-level requirements."""
    return charter_data.get("high_level_requirements", [])  # type: ignore


async def _generate_wbs_structure_for_research(
    agent: ProjectDefinitionAgent,
    scope_overview: dict[str, Any],
) -> dict[str, Any]:
    """Lightweight WBS generation used exclusively by scope research."""
    # Delegate to the WBS actions helper to avoid duplication
    from definition_actions.wbs_actions import _generate_wbs_structure

    return await _generate_wbs_structure(agent, {}, scope_overview, [])


# ---------------------------------------------------------------------------
# Public action handler
# ---------------------------------------------------------------------------


async def handle_generate_scope_research(
    agent: ProjectDefinitionAgent,
    project_id: str,
    objective: str,
    *,
    tenant_id: str,
    correlation_id: str,
    requester: str,
    enable_external_research: bool | None = None,
    search_result_limit: int | None = None,
) -> dict[str, Any]:
    agent.logger.info(
        "Generating scope research proposals",
        extra={"project_id": project_id, "tenant_id": tenant_id},
    )

    baseline_scope = await _generate_scope_overview(
        {"in_scope": [objective], "out_of_scope": [], "deliverables": []}
    )
    baseline_requirements = await _extract_high_level_requirements({"high_level_requirements": []})
    baseline_wbs = await _generate_wbs_structure_for_research(agent, baseline_scope)
    baseline_wbs_items = [
        f"{code} {node.get('name', '')}".strip()
        for code, node in baseline_wbs.items()
        if isinstance(node, dict)
    ]

    use_external = (
        agent.enable_external_research
        if enable_external_research is None
        else enable_external_research
    )
    result_limit = search_result_limit or agent.search_result_limit

    snippets: list[str] = []
    notice: str | None = None
    if use_external:
        safe_query = sanitize_search_query(objective)
        if safe_query:
            agent.logger.info(
                "External scope research request",
                extra={
                    "project_id": project_id,
                    "tenant_id": tenant_id,
                    "query": safe_query,
                    "result_limit": result_limit,
                },
            )
            try:
                # Resolve search_web via the main module so monkeypatching in tests works.
                _main = importlib.import_module("project_definition_agent")
                _search_web = getattr(_main, "search_web")
                snippets = await _search_web(safe_query, result_limit=result_limit)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # pragma: no cover - defensive
                agent.logger.warning(
                    "Search failed; falling back to templates", extra={"error": str(exc)}
                )
                snippets = []
        else:
            notice = "Objective was too sensitive for external research; using templates."
    else:
        notice = "External research disabled; using internal templates."

    if not snippets:
        if notice is None:
            notice = "No external information found; falling back to templates."
        return {
            "project_id": project_id,
            "objective": objective,
            "scope": baseline_scope,
            "requirements": baseline_requirements,
            "wbs": baseline_wbs_items,
            "sources": [],
            "used_external_research": False,
            "notice": notice,
            "requested_by": requester,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
        }

    # Resolve generate_scope_from_search via the main module so monkeypatching in tests works.
    _main = importlib.import_module("project_definition_agent")
    _generate_scope_from_search = getattr(_main, "generate_scope_from_search")
    generated = await _generate_scope_from_search(
        objective,
        snippets,
        baseline_scope,
        baseline_requirements,
        baseline_wbs_items,
    )

    return {
        "project_id": project_id,
        "objective": objective,
        "scope": generated.get("scope", baseline_scope),
        "requirements": generated.get("requirements", baseline_requirements),
        "wbs": generated.get("wbs", baseline_wbs_items),
        "sources": snippets,
        "summary": generated.get("summary", ""),
        "used_external_research": True,
        "notice": notice,
        "requested_by": requester,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
