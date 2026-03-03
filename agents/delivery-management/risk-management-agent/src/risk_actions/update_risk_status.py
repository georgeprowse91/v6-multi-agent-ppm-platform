"""Action handler for risk status updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import (
    publish_risk_event,
    store_risk_dataset,
    validate_risk_record,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def update_risk_status(
    agent: RiskManagementAgent,
    risk_id: str,
    updates: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Update risk status and details.

    Returns updated risk status.
    """
    agent.logger.info("Updating risk status: %s", risk_id)

    risk = agent.risk_register.get(risk_id)
    if not risk:
        raise ValueError(f"Risk not found: {risk_id}")

    # Track history
    if risk_id not in agent.risk_histories:
        agent.risk_histories[risk_id] = []

    # Record current state before update
    agent.risk_histories[risk_id].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": risk.get("status"),
            "probability": risk.get("probability"),
            "impact": risk.get("impact"),
            "score": risk.get("score"),
        }
    )

    # Apply updates
    for key, value in updates.items():
        if key in risk:
            risk[key] = value

    # Recalculate score if probability or impact changed
    if "probability" in updates or "impact" in updates:
        risk["score"] = risk.get("probability", 0) * risk.get("impact", 0)

    risk["last_updated"] = datetime.now(timezone.utc).isoformat()

    validation = await validate_risk_record(agent, risk=risk, tenant_id=tenant_id)
    agent.risk_store.upsert(tenant_id, risk_id, risk)
    if agent.db_service:
        await agent.db_service.store("risks", risk_id, risk)
    await store_risk_dataset(agent, "risks", [risk], domain="risk_register")
    await publish_risk_event(
        agent,
        "risk.status_updated",
        {"risk_id": risk_id, "status": risk["status"], "score": risk["score"]},
    )

    return {
        "risk_id": risk_id,
        "status": risk["status"],
        "score": risk["score"],
        "last_updated": risk["last_updated"],
        "data_quality": validation,
    }
