"""Action handler for trigger monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import (
    check_risk_triggers,
    publish_risk_event,
    store_risk_dataset,
    update_risk_from_trigger,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def monitor_triggers(agent: RiskManagementAgent, risk_id: str | None) -> dict[str, Any]:
    """
    Monitor risk triggers and early warnings.

    Returns trigger alerts and risk updates.
    """
    agent.logger.info("Monitoring triggers for risk: %s", risk_id)

    # Get risks to monitor
    risks_to_monitor = []
    if risk_id:
        risk = agent.risk_register.get(risk_id)
        if risk:
            risks_to_monitor.append(risk)
    else:
        risks_to_monitor = list(agent.risk_register.values())

    # Check triggers
    triggered_risks = []
    for risk in risks_to_monitor:
        trigger_status = await check_risk_triggers(risk)

        if trigger_status.get("triggered"):
            # Update risk probability/impact
            await update_risk_from_trigger(risk, trigger_status)
            triggered_risks.append(
                {
                    "risk_id": risk["risk_id"],
                    "title": risk["title"],
                    "trigger": trigger_status.get("trigger"),
                    "old_score": risk.get("score"),
                    "new_score": trigger_status.get("new_score"),
                }
            )

    if agent.db_service and triggered_risks:
        await agent.db_service.store(
            "risk_triggers",
            f"trigger-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            {
                "risks": triggered_risks,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    if triggered_risks:
        await store_risk_dataset(agent, "risk_triggers", triggered_risks, domain="triggers")
        for triggered in triggered_risks:
            await publish_risk_event(agent, "risk.triggered", triggered)
            await publish_risk_event(agent, "risk.trigger_activated", triggered)

    return {
        "risks_monitored": len(risks_to_monitor),
        "risks_triggered": len(triggered_risks),
        "triggered_risks": triggered_risks,
    }
