"""Action handler: register_stakeholder"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..stakeholder_utils import (
    enrich_stakeholder_profile,
    generate_stakeholder_id,
    suggest_classification,
    upsert_crm_profile,
)

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


async def register_stakeholder(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    stakeholder_data: dict[str, Any],
) -> dict[str, Any]:
    """Register new stakeholder."""
    agent.logger.info("Registering stakeholder: %s", stakeholder_data.get("name"))

    stakeholder_id = await generate_stakeholder_id()

    # Enrich profile from CRM
    await enrich_stakeholder_profile(agent, stakeholder_data)

    # Suggest classification
    suggested_classification = await suggest_classification(stakeholder_data)

    # Create stakeholder profile
    stakeholder = {
        "stakeholder_id": stakeholder_id,
        "name": stakeholder_data.get("name"),
        "email": stakeholder_data.get("email"),
        "phone": stakeholder_data.get("phone"),
        "role": stakeholder_data.get("role"),
        "organization": stakeholder_data.get("organization"),
        "location": stakeholder_data.get("location"),
        "influence": suggested_classification.get("influence", "medium"),
        "interest": suggested_classification.get("interest", "medium"),
        "engagement_level": suggested_classification.get("engagement_level", "medium"),
        "preferred_channels": stakeholder_data.get("preferred_channels", ["email"]),
        "time_zone": stakeholder_data.get("time_zone", "UTC"),
        "communication_preferences": stakeholder_data.get("communication_preferences", {}),
        "consent": stakeholder_data.get("consent", True),
        "opt_out": stakeholder_data.get("opt_out", False),
        "projects": stakeholder_data.get("projects", []),
        "engagement_score": 0,
        "sentiment_score": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Preserve CRM enrichment data
    if stakeholder_data.get("crm_profile"):
        stakeholder["crm_profile"] = stakeholder_data["crm_profile"]
    if stakeholder_data.get("crm_synced_at"):
        stakeholder["crm_synced_at"] = stakeholder_data["crm_synced_at"]

    # Store stakeholder
    agent.stakeholder_register[stakeholder_id] = stakeholder
    agent.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())

    # Initialize engagement metrics
    agent.engagement_metrics[stakeholder_id] = {
        "messages_sent": 0,
        "messages_opened": 0,
        "messages_clicked": 0,
        "responses_received": 0,
        "events_attended": 0,
    }

    crm_sync = await upsert_crm_profile(agent, stakeholder)
    if crm_sync:
        stakeholder["crm_upserted_at"] = datetime.now(timezone.utc).isoformat()
        stakeholder["crm_upsert_status"] = crm_sync
        agent.stakeholder_register[stakeholder_id] = stakeholder
        agent.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())

    agent._publish_event(
        "stakeholder.profile.registered",
        {"stakeholder_id": stakeholder_id, "crm_sync": crm_sync},
    )
    agent._trigger_workflow(
        "stakeholder.profile.registered",
        {"stakeholder_id": stakeholder_id, "crm_sync": crm_sync},
    )

    return {
        "stakeholder_id": stakeholder_id,
        "name": stakeholder["name"],
        "suggested_classification": suggested_classification,
        "next_steps": "Classify stakeholder and add to communication plans",
    }
