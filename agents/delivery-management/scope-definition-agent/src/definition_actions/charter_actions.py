"""
Charter generation and retrieval action handlers.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from definition_utils import (
    generate_charter_content,
    generate_charter_id,
    generate_project_id,
    serialize_charter_for_index,
)
from events import CharterCreatedEvent
from feature_flags import is_feature_enabled
from observability.tracing import get_trace_id

from agents.common.connector_integration import DocumentMetadata

if TYPE_CHECKING:
    from project_definition_agent import ProjectDefinitionAgent


# ---------------------------------------------------------------------------
# Charter section generators (previously private methods on the agent)
# ---------------------------------------------------------------------------


async def _select_charter_template(charter_data: dict[str, Any]) -> str:
    """Select appropriate charter template."""
    project_type = charter_data.get("project_type", "general")
    methodology = charter_data.get("methodology", "hybrid")
    return f"template_{project_type}_{methodology}"


async def _generate_executive_summary(
    agent: ProjectDefinitionAgent, charter_data: dict[str, Any]
) -> str:
    """Generate executive summary using AI."""
    title = charter_data.get("title", "Project")
    description = charter_data.get("description", "")
    prompt = (
        "Draft an executive summary for a project charter.\n"
        f"Title: {title}\nDescription: {description}\n"
        "Provide a concise summary highlighting purpose and outcomes."
    )
    openai_response = await _generate_with_openai(agent, prompt)
    if openai_response:
        return openai_response
    return f"This project charter establishes {title}. {description}"


async def _generate_objectives(charter_data: dict[str, Any]) -> list[str]:
    """Generate project objectives."""
    return charter_data.get(  # type: ignore
        "objectives",
        [
            "Deliver project on time and within budget",
            "Meet stakeholder expectations",
            "Achieve defined success criteria",
        ],
    )


async def _generate_scope_overview(charter_data: dict[str, Any]) -> dict[str, Any]:
    """Generate scope overview."""
    return {
        "in_scope": charter_data.get("in_scope", []),
        "out_of_scope": charter_data.get("out_of_scope", []),
        "deliverables": charter_data.get("deliverables", []),
    }


async def _generate_governance_structure(charter_data: dict[str, Any]) -> dict[str, Any]:
    """Generate governance structure."""
    return {
        "sponsor": charter_data.get("sponsor", "Unassigned"),
        "project_manager": charter_data.get("project_manager", "Unassigned"),
        "steering_committee": charter_data.get("steering_committee", []),
        "reporting_frequency": charter_data.get("reporting_frequency", "weekly"),
    }


async def _extract_high_level_requirements(charter_data: dict[str, Any]) -> list[str]:
    """Extract high-level requirements."""
    return charter_data.get("high_level_requirements", [])  # type: ignore


async def _identify_stakeholders(charter_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Identify project stakeholders."""
    return charter_data.get("stakeholders", [])  # type: ignore


async def _generate_success_criteria(charter_data: dict[str, Any]) -> list[str]:
    """Generate success criteria."""
    return charter_data.get(  # type: ignore
        "success_criteria",
        [
            "Project completed within approved budget",
            "All deliverables meet quality standards",
            "Stakeholder satisfaction > 80%",
        ],
    )


async def _generate_assumptions(charter_data: dict[str, Any]) -> list[str]:
    """Generate project assumptions."""
    return charter_data.get("assumptions", [])  # type: ignore


async def _generate_constraints(charter_data: dict[str, Any]) -> list[str]:
    """Generate project constraints."""
    return charter_data.get("constraints", [])  # type: ignore


async def _generate_with_openai(agent: ProjectDefinitionAgent, prompt: str) -> str | None:
    if not agent.openai_client:
        return None
    try:
        if hasattr(agent.openai_client, "generate"):
            response = await agent.openai_client.generate(prompt)
            return response if isinstance(response, str) else str(response)
        if hasattr(agent.openai_client, "complete"):
            response = await agent.openai_client.complete(prompt)
            return response if isinstance(response, str) else str(response)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:  # pragma: no cover - defensive
        agent.logger.warning("OpenAI generation failed", extra={"error": str(exc)})
    return None


def _autonomous_deliverables_enabled(agent: ProjectDefinitionAgent) -> bool:
    if agent.config and "autonomous_deliverables" in agent.config:
        return bool(agent.config.get("autonomous_deliverables"))
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("autonomous_deliverables", environment=environment, default=False)


def _build_charter_document_entity(
    agent: ProjectDefinitionAgent,
    charter: dict[str, Any],
    charter_content: str,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    created_at = charter.get("created_at") or datetime.now(timezone.utc).isoformat()
    provenance = {
        "sourceAgent": agent.agent_id,
        "generatedAt": created_at,
        "correlationId": correlation_id,
        "inputContext": {
            "project_id": charter.get("project_id", ""),
            "charter_id": charter.get("charter_id", ""),
            "methodology": charter.get("methodology", "hybrid"),
        },
    }
    title = charter.get("title") or "Project Charter"
    return {
        "title": f"{title} Project Charter",
        "content": charter_content,
        "author": charter.get("created_by", "unknown"),
        "project_id": charter.get("project_id"),
        "tags": ["project-charter", charter.get("project_type") or "general"],
        "metadata": {
            "charter_id": charter.get("charter_id", ""),
            "status": charter.get("status", "Draft"),
            "provenance": provenance,
        },
        "source": "agent_output",
        "status": charter.get("status", "Draft"),
    }


async def _publish_charter_created(
    agent: ProjectDefinitionAgent,
    charter: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> None:
    event = CharterCreatedEvent(
        event_name="charter.created",
        event_id=f"evt-{uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=get_trace_id(),
        payload={
            "charter_id": charter.get("charter_id", ""),
            "project_id": charter.get("project_id", ""),
            "created_at": datetime.fromisoformat(charter.get("created_at")),
            "owner": charter.get("created_by", "unknown"),
        },
    )
    await agent.event_bus.publish("charter.created", event.model_dump(mode="json"))


async def _request_signoff(
    agent: ProjectDefinitionAgent,
    *,
    request_type: str,
    request_id: str,
    requester: str,
    details: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    if not agent.approval_agent:
        return {"status": "skipped", "reason": "approval_agent_not_configured"}
    response = await agent.approval_agent.process(
        {
            "request_type": request_type,
            "request_id": request_id,
            "requester": requester,
            "details": details,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
    )
    return response


async def _index_artifact(
    agent: ProjectDefinitionAgent,
    *,
    artifact_type: str,
    artifact_id: str,
    content: str,
    metadata: dict[str, Any],
) -> None:
    if not content:
        return
    if agent.cognitive_search_client and hasattr(agent.cognitive_search_client, "index"):
        try:
            await agent.cognitive_search_client.index(
                {
                    "id": artifact_id,
                    "type": artifact_type,
                    "content": content,
                    "metadata": metadata,
                }
            )
            return
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # pragma: no cover - defensive
            agent.logger.warning("Cognitive Search indexing failed", extra={"error": str(exc)})
    agent.search_index.add(artifact_id, content, {"type": artifact_type, **metadata})


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------


async def handle_generate_charter(
    agent: ProjectDefinitionAgent,
    charter_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Generate comprehensive project charter.

    Returns charter ID and complete document.
    """
    agent.logger.info("Generating project charter")

    project_id = await generate_project_id()
    template = await _select_charter_template(charter_data)

    title = charter_data.get("title")
    charter_data.get("description")
    project_type = charter_data.get("project_type")
    methodology = charter_data.get("methodology", "hybrid")

    executive_summary = await _generate_executive_summary(agent, charter_data)
    objectives = await _generate_objectives(charter_data)
    scope_overview = await _generate_scope_overview(charter_data)
    governance_structure = await _generate_governance_structure(charter_data)
    high_level_requirements = await _extract_high_level_requirements(charter_data)
    stakeholders = await _identify_stakeholders(charter_data)
    success_criteria = await _generate_success_criteria(charter_data)
    assumptions = await _generate_assumptions(charter_data)
    constraints = await _generate_constraints(charter_data)

    charter_id = await generate_charter_id(project_id)

    charter = {
        "charter_id": charter_id,
        "project_id": project_id,
        "title": title,
        "project_type": project_type,
        "methodology": methodology,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": charter_data.get("requester", "unknown"),
        "status": "Draft",
        "template": template,
        "document": {
            "executive_summary": executive_summary,
            "objectives": objectives,
            "scope_overview": scope_overview,
            "high_level_requirements": high_level_requirements,
            "stakeholders": stakeholders,
            "governance_structure": governance_structure,
            "success_criteria": success_criteria,
            "assumptions": assumptions,
            "constraints": constraints,
        },
        "version": "1.0",
    }

    agent.charters[project_id] = charter
    agent.charter_store.upsert(tenant_id, project_id, charter)

    approval = await _request_signoff(
        agent,
        request_type="scope_change",
        request_id=charter_id,
        requester=charter.get("created_by", "unknown"),
        details={
            "description": "Project charter sign-off",
            "project_id": project_id,
            "title": title,
            "methodology": methodology,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await _publish_charter_created(
        agent,
        charter,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await agent.db_service.store(
        "project_charters",
        charter_id,
        {"tenant_id": tenant_id, "charter": charter},
    )
    await _index_artifact(
        agent,
        artifact_type="project_charter",
        artifact_id=charter_id,
        content=serialize_charter_for_index(charter),
        metadata={"project_id": project_id, "title": title or ""},
    )
    charter_content = await generate_charter_content(charter)
    await agent.document_service.publish_document(
        charter_content,
        DocumentMetadata(
            title=f"{title} Project Charter",
            description=charter_data.get("description", ""),
            tags=["project-charter", project_type or "general"],
            owner=charter.get("created_by", "unknown"),
        ),
        folder_path="Project Charters",
    )

    agent.logger.info("Generated charter for project: %s", project_id)

    document_entities: list[dict[str, Any]] = []
    if _autonomous_deliverables_enabled(agent):
        document_entities.append(
            _build_charter_document_entity(
                agent, charter, charter_content, correlation_id=correlation_id
            )
        )

    return {
        "project_id": project_id,
        "charter_id": charter_id,
        "status": "Draft",
        "document": charter["document"],
        "next_steps": "Review and refine charter, then submit for approval",
        "approval": approval,
        "documents": document_entities,
    }


async def handle_get_charter(
    agent: ProjectDefinitionAgent,
    project_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Retrieve project charter by ID."""
    charter = agent.charters.get(project_id)
    if not charter:
        charter = agent.charter_store.get(tenant_id, project_id)
    if not charter:
        raise ValueError(f"Charter not found for project: {project_id}")
    return charter  # type: ignore
