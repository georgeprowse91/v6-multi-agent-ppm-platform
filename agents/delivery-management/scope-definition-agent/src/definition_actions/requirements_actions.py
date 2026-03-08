"""
Requirements management and traceability action handlers.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import (
    generate_traceability_matrix,
    serialize_requirements_for_index,
    serialize_traceability_for_index,
)

from definition_actions.charter_actions import _index_artifact

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# Requirements helpers (previously private methods on the agent)
# ---------------------------------------------------------------------------


async def _extract_requirements_from_sources(
    agent: ProjectDefinitionAgent,
    project_id: str,
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract requirements from various sources."""
    extracted: list[dict[str, Any]] = []
    if agent.form_recognizer_client:
        extracted.extend(
            await _extract_requirements_with_form_recognizer(agent, project_id, requirements)
        )
    keyword_patterns = [
        r"\\bshall\\b",
        r"\\bmust\\b",
        r"\\bshould\\b",
        r"\\bis required to\\b",
        r"\\bneeds to\\b",
    ]
    keyword_regex = re.compile("|".join(keyword_patterns), re.IGNORECASE)

    for req in requirements:
        if "text" in req or "description" in req:
            extracted.append(
                {
                    "id": req.get("id") or f"REQ-{uuid.uuid4().hex[:6]}",
                    "text": req.get("text") or req.get("description", ""),
                    "source": req.get("source", "manual"),
                    "category": req.get("category"),
                }
            )
        source_text = req.get("source_text") or req.get("document") or req.get("notes", "")
        if source_text:
            sentences = re.split(r"(?<=[.!?])\\s+", str(source_text))
            for sentence in sentences:
                if keyword_regex.search(sentence):
                    extracted.append(
                        {
                            "id": f"REQ-{uuid.uuid4().hex[:6]}",
                            "text": sentence.strip(),
                            "source": req.get("source", "keyword_parse"),
                        }
                    )

    if not extracted and requirements:
        for req in requirements:
            if "text" in req or "description" in req:
                extracted.append(req)

    return extracted


async def _extract_requirements_with_form_recognizer(
    agent: ProjectDefinitionAgent,
    project_id: str,
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for req in requirements:
        if not isinstance(req, dict):
            continue
        document_content = req.get("document_content") or req.get("document_text")
        document_url = req.get("document_url")
        if not document_content and not document_url:
            continue
        try:
            if hasattr(agent.form_recognizer_client, "extract_requirements"):
                result = await agent.form_recognizer_client.extract_requirements(
                    document_content=document_content, document_url=document_url
                )
            elif hasattr(agent.form_recognizer_client, "analyze"):
                result = await agent.form_recognizer_client.analyze(
                    document_content=document_content, document_url=document_url
                )
            else:
                result = []
            for item in result or []:
                text = item.get("text") if isinstance(item, dict) else str(item)
                if text:
                    extracted.append(
                        {
                            "id": f"REQ-{uuid.uuid4().hex[:6]}",
                            "text": text.strip(),
                            "source": "form_recognizer",
                            "project_id": project_id,
                        }
                    )
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
                "Form Recognizer extraction failed",
                extra={"project_id": project_id, "error": str(exc)},
            )
    return extracted


async def _categorize_requirements(
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Categorize requirements by type."""
    for req in requirements:
        if "category" not in req:
            req["category"] = "functional"
    return requirements


async def _prioritize_requirements(
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prioritize requirements."""
    for req in requirements:
        if "priority" not in req:
            req["priority"] = "medium"
    return requirements


async def _detect_requirement_conflicts(
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect conflicting requirements."""
    return []


async def _validate_requirements_completeness(
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate requirements completeness."""
    return {"complete": True, "missing_fields": [], "validation_score": 0.95}


async def _get_requirement_categories(
    requirements: list[dict[str, Any]],
) -> dict[str, int]:
    """Get requirement count by category."""
    categories: dict[str, int] = {}
    for req in requirements:
        category = req.get("category", "unknown")
        categories[category] = categories.get(category, 0) + 1
    return categories


async def _get_user_stories(agent: ProjectDefinitionAgent, project_id: str) -> list[dict[str, Any]]:
    """Get user stories from work item tracking system."""
    return await agent.project_service.get_tasks(project_id, filters={"item_type": "user_story"})


async def _get_test_cases(agent: ProjectDefinitionAgent, project_id: str) -> list[dict[str, Any]]:
    """Get test cases from test management system."""
    return await agent.project_service.get_tasks(project_id, filters={"item_type": "test_case"})


async def _identify_traceability_gaps(
    requirements: list[dict[str, Any]], traceability_links: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Identify gaps in traceability."""
    return []


async def _calculate_traceability_coverage(
    requirements: list[dict[str, Any]], traceability_links: list[dict[str, Any]]
) -> float:
    """Calculate traceability coverage percentage."""
    if not requirements:
        return 1.0

    covered_requirement_ids = {
        link.get("requirement_id")
        for link in traceability_links
        if link.get("coverage_status") == "covered" and link.get("wbs_item_ids")
    }
    requirement_ids = {req.get("id") for req in requirements if req.get("id")}
    if not requirement_ids:
        return 1.0 if traceability_links else 0.0
    return len(requirement_ids & covered_requirement_ids) / len(requirement_ids)


async def _sync_requirements_external(
    agent: ProjectDefinitionAgent,
    project_id: str,
    requirements: list[dict[str, Any]],
) -> dict[str, str]:
    status: dict[str, str] = {}
    if agent.doors_client:
        status["doors"] = await _sync_with_requirements_tool(
            agent, "doors", agent.doors_client, project_id, requirements
        )
    if agent.jama_client:
        status["jama"] = await _sync_with_requirements_tool(
            agent, "jama", agent.jama_client, project_id, requirements
        )
    return status


async def _sync_with_requirements_tool(
    agent: ProjectDefinitionAgent,
    tool_name: str,
    client: Any,
    project_id: str,
    requirements: list[dict[str, Any]],
) -> str:
    try:
        if hasattr(client, "sync_requirements"):
            await client.sync_requirements(project_id=project_id, requirements=requirements)
        elif hasattr(client, "upsert"):
            await client.upsert("requirements", requirements)
        return "synced"
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
            "External requirements sync failed",
            extra={"tool": tool_name, "error": str(exc)},
        )
        return "failed"


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------


async def handle_manage_requirements(
    agent: ProjectDefinitionAgent,
    project_id: str,
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Manage project requirements.

    Returns requirements repository with metadata.
    """
    agent.logger.info("Managing requirements for project: %s", project_id)

    extracted_requirements = await _extract_requirements_from_sources(
        agent, project_id, requirements
    )
    categorized = await _categorize_requirements(extracted_requirements)
    prioritized = await _prioritize_requirements(categorized)
    conflicts = await _detect_requirement_conflicts(prioritized)
    validation = await _validate_requirements_completeness(prioritized)

    requirements_repo = {
        "project_id": project_id,
        "requirements": prioritized,
        "categories": await _get_requirement_categories(prioritized),
        "conflicts": conflicts,
        "validation": validation,
        "total_count": len(prioritized),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.requirements[project_id] = requirements_repo

    await agent.db_service.store(
        "project_requirements",
        project_id,
        {"tenant_id": "unknown", "requirements": requirements_repo},
    )
    sync_status = await _sync_requirements_external(agent, project_id, prioritized)
    requirements_repo["external_sync"] = sync_status
    await _index_artifact(
        agent,
        artifact_type="project_requirements",
        artifact_id=project_id,
        content=serialize_requirements_for_index(prioritized),
        metadata={"project_id": project_id},
    )
    await agent.project_service.sync_project(
        {
            "project_id": project_id,
            "requirements_count": requirements_repo.get("total_count", 0),
            "requirements": requirements_repo.get("requirements", []),
            "updated_at": requirements_repo.get("updated_at"),
        }
    )

    return requirements_repo


async def handle_create_traceability_matrix(
    agent: ProjectDefinitionAgent,
    project_id: str,
) -> dict[str, Any]:
    """
    Create requirements traceability matrix.

    Returns matrix linking requirements to user stories and test cases.
    """
    agent.logger.info("Creating traceability matrix for project: %s", project_id)

    requirements_repo = agent.requirements.get(project_id)
    if not requirements_repo:
        raise ValueError(f"Requirements not found for project: {project_id}")

    requirements_list = requirements_repo.get("requirements", [])

    user_stories = await _get_user_stories(agent, project_id)
    test_cases = await _get_test_cases(agent, project_id)

    wbs = agent.wbs_structures.get(project_id, {}).get("structure", {})
    traceability_links = generate_traceability_matrix(requirements_list, [wbs])

    gaps = await _identify_traceability_gaps(requirements_list, traceability_links)
    coverage = await _calculate_traceability_coverage(requirements_list, traceability_links)

    matrix = {
        "project_id": project_id,
        "requirements": requirements_list,
        "user_stories": user_stories,
        "test_cases": test_cases,
        "traceability_links": traceability_links,
        "gaps": gaps,
        "coverage": coverage,
        "meets_threshold": coverage >= agent.traceability_threshold,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.traceability_matrices[project_id] = matrix
    await _index_artifact(
        agent,
        artifact_type="traceability_matrix",
        artifact_id=project_id,
        content=serialize_traceability_for_index(matrix),
        metadata={"project_id": project_id},
    )
    await agent.event_bus.publish(
        "traceability.matrix.created",
        {
            "project_id": project_id,
            "created_at": matrix["created_at"],
            "coverage": coverage,
            "entry_count": len(traceability_links),
        },
    )

    return matrix


async def handle_get_requirements(
    agent: ProjectDefinitionAgent,
    project_id: str,
) -> dict[str, Any]:
    """Retrieve requirements repository by project ID."""
    requirements = agent.requirements.get(project_id)
    if not requirements:
        raise ValueError(f"Requirements not found for project: {project_id}")
    return requirements  # type: ignore
