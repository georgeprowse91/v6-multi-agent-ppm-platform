"""Action handler: define_control"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import GRCControl

from compliance_utils import (
    build_control_embeddings,
    cosine_similarity,
    embed_text,
    generate_control_id,
)

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_define_control(
    agent: ComplianceRegulatoryAgent, control_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Define compliance control.

    Returns control ID and requirements.
    """
    agent.logger.info("Defining control: %s", control_data.get("description"))

    # Generate control ID
    control_id = await generate_control_id()

    # Recommend similar controls using AI
    similar_controls = await _recommend_similar_controls(agent, control_data)

    # Create control
    control = {
        "control_id": control_id,
        "description": control_data.get("description"),
        "regulation": control_data.get("regulation"),
        "control_type": control_data.get("control_type", "preventive"),
        "owner": control_data.get("owner"),
        "evidence_requirements": control_data.get("evidence_requirements", []),
        "test_frequency": control_data.get("test_frequency", "quarterly"),
        "test_procedure": control_data.get("test_procedure"),
        "status": "Active",
        "last_test_date": None,
        "last_test_result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store control
    agent.control_registry[control_id] = control

    # Link to regulation
    if control["regulation"] in agent.regulation_library:
        agent.regulation_library[control["regulation"]]["related_controls"].append(control_id)

    # Persist to database
    await agent.db_service.store("controls", control_id, control)

    # Sync control to GRC platform
    grc_control = GRCControl(
        control_id=control_id,
        name=control_data.get("description", "")[:100],
        description=control_data.get("description", ""),
        regulation=control_data.get("regulation", ""),
        status=control["status"],
        owner=control["owner"],
        test_frequency=control["test_frequency"],
    )
    grc_sync_result = await agent.grc_service.sync_control(grc_control)
    control["grc_external_id"] = grc_sync_result.get("external_id")

    return {
        "control_id": control_id,
        "description": control["description"],
        "owner": control["owner"],
        "test_frequency": control["test_frequency"],
        "similar_controls": similar_controls,
        "next_steps": "Map control to projects and deliverables",
    }


async def _recommend_similar_controls(
    agent: ComplianceRegulatoryAgent, control_data: dict[str, Any]
) -> list[str]:
    """Recommend similar controls."""
    query_text = " ".join(
        filter(
            None,
            [
                control_data.get("description", ""),
                control_data.get("regulation", ""),
                control_data.get("control_type", ""),
            ],
        )
    ).strip()
    if not query_text:
        return []

    embeddings = await build_control_embeddings(agent.control_registry)
    agent.control_embeddings = embeddings
    query_vector = embed_text(query_text)
    scores: list[tuple[str, float]] = []
    for c_id, vector in embeddings.items():
        score = cosine_similarity(query_vector, vector)
        if score > 0:
            scores.append((c_id, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    return [c_id for c_id, _ in scores[:5]]
