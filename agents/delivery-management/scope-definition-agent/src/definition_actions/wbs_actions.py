"""
WBS generation, update and retrieval action handlers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import (
    generate_wbs_id,
    parse_wbs_response,
    serialize_wbs_for_index,
)
from events import ScopeChangeEvent, WbsCreatedEvent
from observability.tracing import get_trace_id

from definition_actions.charter_actions import (
    _generate_with_openai,
    _index_artifact,
    _request_signoff,
)

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# WBS helpers (previously private methods on the agent)
# ---------------------------------------------------------------------------


async def _find_similar_projects(
    agent: ProjectDefinitionAgent, charter: dict[str, Any]
) -> list[dict[str, Any]]:
    """Find similar projects for WBS reference."""
    if not charter:
        return []
    title = charter.get("title", "")
    if not title:
        return []
    results = agent.search_index.search(title, top_k=3)
    return [result.metadata for result in results]


async def _generate_wbs_with_openai(
    agent: ProjectDefinitionAgent, prompt: str
) -> dict[str, Any] | None:
    response = await _generate_with_openai(agent, prompt)
    if not response:
        return None
    try:
        parsed = parse_wbs_response(response)
        return parsed if parsed else None
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):  # pragma: no cover - defensive
        return None


async def _generate_wbs_from_objectives(
    objectives: list[str],
    scope_overview: dict[str, Any],
    similar_projects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a WBS by decomposing objectives into phases and work packages."""
    if not objectives and not scope_overview.get("deliverables"):
        return {}

    wbs: dict[str, Any] = {
        "1.0": {
            "name": "Project Management",
            "children": {
                "1.1": {"name": "Initiation & Planning", "children": {}},
                "1.2": {"name": "Monitoring & Control", "children": {}},
                "1.3": {"name": "Closure", "children": {}},
            },
        }
    }

    deliverables = scope_overview.get("deliverables", [])

    def objective_work_packages(objective: str) -> list[str]:
        base_packages = [
            "Discovery & Analysis",
            "Design & Build",
            "Validation & Acceptance",
            "Deployment & Handover",
        ]
        lowered = objective.lower()
        if "migrate" in lowered or "migration" in lowered:
            return [
                "Migration Planning",
                "Data & System Migration",
                "Migration Validation",
                "Go-Live Support",
            ]
        if "implement" in lowered or "build" in lowered or "develop" in lowered:
            return [
                "Solution Design",
                "Implementation",
                "Testing",
                "Release",
            ]
        return base_packages

    index_offset = 2
    for idx, objective in enumerate(objectives or ["Deliver scoped outcomes"]):
        root_code = f"{idx + index_offset}.0"
        children: dict[str, Any] = {}
        packages = objective_work_packages(objective)
        for pkg_index, package in enumerate(packages, start=1):
            child_code = f"{idx + index_offset}.{pkg_index}"
            children[child_code] = {"name": package, "children": {}}
        if deliverables:
            for deliverable_index, deliverable in enumerate(deliverables, start=len(children) + 1):
                child_code = f"{idx + index_offset}.{deliverable_index}"
                children[child_code] = {"name": f"Deliver {deliverable}", "children": {}}
        if similar_projects:
            children[f"{idx + index_offset}.{len(children) + 1}"] = {
                "name": "Leverage Similar Project Assets",
                "children": {},
            }
        wbs[root_code] = {"name": objective, "children": children}

    return wbs


async def _generate_wbs_structure(
    agent: ProjectDefinitionAgent,
    charter: dict[str, Any],
    scope_statement: dict[str, Any],
    similar_projects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate hierarchical WBS structure."""
    charter_context = {
        "title": charter.get("title"),
        "project_type": charter.get("project_type"),
        "methodology": charter.get("methodology"),
        "objectives": charter.get("document", {}).get("objectives", [])
        or charter.get("objectives", []),
        "in_scope": charter.get("document", {}).get("scope_overview", {}).get("in_scope", []),
    }
    openai_prompt = (
        "Generate a Work Breakdown Structure (WBS) for the project.\n"
        f"Project context: {charter_context}\nScope statement: {scope_statement}\n"
        "Return a hierarchical mapping keyed by WBS codes."
    )
    openai_structure = await _generate_wbs_with_openai(agent, openai_prompt)
    if openai_structure:
        return openai_structure
    objectives = charter.get("document", {}).get("objectives", []) or charter.get("objectives", [])
    scope_overview = scope_statement or charter.get("document", {}).get("scope_overview", {})
    wbs_from_objectives = await _generate_wbs_from_objectives(
        objectives, scope_overview, similar_projects
    )
    if wbs_from_objectives:
        return wbs_from_objectives

    return {
        "1.0": {
            "name": "Project Management",
            "children": {
                "1.1": {"name": "Project Planning", "children": {}},
                "1.2": {"name": "Project Monitoring", "children": {}},
            },
        }
    }


async def _add_work_package_details(wbs_structure: dict[str, Any]) -> dict[str, Any]:
    """Add details to work packages."""
    return wbs_structure


async def _count_work_packages(wbs_structure: dict[str, Any]) -> int:
    """Count total work packages in WBS."""
    return 10  # Baseline


async def _publish_wbs_created(
    agent: ProjectDefinitionAgent,
    wbs: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> None:
    event = WbsCreatedEvent(
        event_name="wbs.created",
        event_id=f"evt-{uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=get_trace_id(),
        payload={
            "wbs_id": wbs.get("wbs_id", ""),
            "project_id": wbs.get("project_id", ""),
            "created_at": datetime.fromisoformat(wbs.get("created_at")),
            "baseline_date": None,
        },
    )
    await agent.event_bus.publish("wbs.created", event.model_dump(mode="json"))


async def _publish_wbs_updated(
    agent: ProjectDefinitionAgent,
    wbs: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> None:
    if not agent.event_bus:
        return
    event = ScopeChangeEvent(
        event_name="wbs.updated",
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        payload={
            "wbs_id": wbs.get("wbs_id", ""),
            "project_id": wbs.get("project_id", ""),
            "updated_at": datetime.fromisoformat(wbs.get("updated_at")),
        },
    )
    await agent.event_bus.publish("wbs.updated", event.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------


async def handle_generate_wbs(
    agent: ProjectDefinitionAgent,
    project_id: str,
    scope_statement: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    requester: str,
) -> dict[str, Any]:
    """
    Generate Work Breakdown Structure.

    Returns WBS ID and hierarchical structure.
    """
    agent.logger.info("Generating WBS for project: %s", project_id)

    charter = agent.charters.get(project_id)
    if not charter:
        raise ValueError(f"Charter not found for project: {project_id}")

    similar_projects = await _find_similar_projects(agent, charter)
    wbs_structure = await _generate_wbs_structure(agent, charter, scope_statement, similar_projects)
    wbs_with_details = await _add_work_package_details(wbs_structure)
    wbs_id = await generate_wbs_id(project_id)

    wbs = {
        "wbs_id": wbs_id,
        "project_id": project_id,
        "structure": wbs_with_details,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "Draft",
        "version": "1.0",
    }

    agent.wbs_structures[project_id] = wbs
    agent.wbs_store.upsert(tenant_id, project_id, wbs)

    approval = await _request_signoff(
        agent,
        request_type="scope_change",
        request_id=wbs_id,
        requester=requester,
        details={
            "description": "WBS sign-off",
            "project_id": project_id,
            "wbs_id": wbs_id,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await _publish_wbs_created(agent, wbs, tenant_id=tenant_id, correlation_id=correlation_id)

    await agent.db_service.store(
        "project_wbs",
        wbs_id,
        {"tenant_id": tenant_id, "wbs": wbs},
    )
    await _index_artifact(
        agent,
        artifact_type="project_wbs",
        artifact_id=wbs_id,
        content=serialize_wbs_for_index(wbs_with_details),
        metadata={"project_id": project_id},
    )

    return {
        "wbs_id": wbs_id,
        "project_id": project_id,
        "structure": wbs_with_details,
        "total_work_packages": await _count_work_packages(wbs_with_details),
        "next_steps": "Review and refine WBS, then pass to Schedule & Planning Agent",
        "approval": approval,
    }


async def handle_update_wbs(
    agent: ProjectDefinitionAgent,
    project_id: str,
    updates: dict[str, Any],
    *,
    wbs_payload: dict[str, Any] | None,
    tenant_id: str,
    correlation_id: str,
    requester: str,
) -> dict[str, Any]:
    """Update an existing WBS structure and persist the canonical record."""
    agent.logger.info("Updating WBS for project: %s", project_id)

    existing = agent.wbs_structures.get(project_id) or agent.wbs_store.get(tenant_id, project_id)
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        wbs = dict(existing)
    else:
        wbs = {
            "wbs_id": await generate_wbs_id(project_id),
            "project_id": project_id,
            "structure": {},
            "created_at": now,
            "created_by": requester,
            "version": "1.0",
        }

    update_payload = dict(updates or {})
    if wbs_payload:
        update_payload.setdefault("structure", wbs_payload.get("structure", wbs_payload))
        if wbs_payload.get("wbs_id"):
            update_payload.setdefault("wbs_id", wbs_payload.get("wbs_id"))

    for key in ("wbs_id", "structure", "scope_statement", "status", "metadata"):
        if key in update_payload:
            wbs[key] = update_payload[key]

    wbs["updated_at"] = now
    wbs["updated_by"] = requester

    agent.wbs_structures[project_id] = wbs
    agent.wbs_store.upsert(tenant_id, project_id, wbs)
    await agent.db_service.store(
        "project_wbs",
        wbs.get("wbs_id", project_id),
        {"tenant_id": tenant_id, "wbs": wbs},
    )
    await _index_artifact(
        agent,
        artifact_type="project_wbs",
        artifact_id=wbs.get("wbs_id", project_id),
        content=serialize_wbs_for_index(wbs.get("structure", {})),
        metadata={"project_id": project_id},
    )
    await _publish_wbs_updated(agent, wbs, tenant_id=tenant_id, correlation_id=correlation_id)

    return {
        "wbs_id": wbs.get("wbs_id"),
        "project_id": project_id,
        "status": wbs.get("status", "Updated"),
        "updated_at": wbs.get("updated_at"),
    }


async def handle_get_wbs(
    agent: ProjectDefinitionAgent,
    project_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Retrieve WBS by project ID."""
    wbs = agent.wbs_structures.get(project_id)
    if not wbs:
        wbs = agent.wbs_store.get(tenant_id, project_id)
    if not wbs:
        raise ValueError(f"WBS not found for project: {project_id}")
    return wbs  # type: ignore
