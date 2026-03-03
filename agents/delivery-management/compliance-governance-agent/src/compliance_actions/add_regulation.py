"""Action handler: add_regulation"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_utils import generate_regulation_id

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_add_regulation(
    agent: ComplianceRegulatoryAgent, regulation_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Add regulation to library.

    Returns regulation ID and applicability.
    """
    agent.logger.info("Adding regulation: %s", regulation_data.get("name"))

    # Generate regulation ID
    regulation_id = await generate_regulation_id()

    # Parse regulation using Azure Cognitive Services
    regulation_metadata = await agent._extract_regulation_metadata(regulation_data)
    parsed_obligations = regulation_metadata.get("obligations", [])

    # Determine applicability
    applicability = await _determine_applicability(regulation_data)

    effective_date = regulation_data.get("effective_date") or regulation_metadata.get(
        "effective_date"
    )

    # Create regulation entry
    regulation = {
        "regulation_id": regulation_id,
        "name": regulation_data.get("name"),
        "description": regulation_data.get("description"),
        "jurisdiction": regulation_data.get("jurisdiction", []),
        "industry": regulation_data.get("industry", []),
        "effective_date": effective_date,
        "obligations": parsed_obligations,
        "related_controls": [],
        "applicability_rules": applicability,
        "metadata": regulation_metadata.get("metadata", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store regulation
    agent.regulation_library[regulation_id] = regulation

    # Persist to database
    await agent.db_service.store("regulations", regulation_id, regulation)

    return {
        "regulation_id": regulation_id,
        "name": regulation["name"],
        "obligations_extracted": len(parsed_obligations),
        "applicability": applicability,
        "next_steps": "Define controls to satisfy regulatory obligations",
    }


async def _determine_applicability(regulation_data: dict[str, Any]) -> dict[str, Any]:
    """Determine regulation applicability rules."""
    return {
        "applies_to_all": False,
        "jurisdiction_filter": regulation_data.get("jurisdiction", []),
        "industry_filter": regulation_data.get("industry", []),
    }
