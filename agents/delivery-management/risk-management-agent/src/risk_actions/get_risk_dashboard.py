"""Action handler for risk dashboard retrieval."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import collect_external_risk_signals

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def get_risk_dashboard(
    agent: RiskManagementAgent,
    project_id: str | None,
    portfolio_id: str | None,
    *,
    tenant_id: str,
    external_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get risk dashboard data.

    Returns dashboard data and visualizations.
    """
    # Import sibling actions for internal delegation
    from actions.generate_risk_matrix import generate_risk_matrix
    from actions.get_top_risks import get_top_risks
    from actions.prioritize_risks import prioritize_risks
    from actions.research_risks import research_risks_action

    agent.logger.info(
        "Getting risk dashboard for project=%s, portfolio=%s", project_id, portfolio_id
    )

    external_risk_research: dict[str, Any] | None = None
    if (
        agent.enable_external_risk_research
        and project_id
        and external_context
        and external_context.get("domain")
    ):
        try:
            external_risk_research = await research_risks_action(
                agent,
                project_id=project_id,
                domain=external_context.get("domain", ""),
                region=external_context.get("region"),
                categories=external_context.get("categories", []),
                tenant_id=tenant_id,
                correlation_id=external_context.get("correlation_id", "n/a"),
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
                "External risk research failed",
                extra={"error": str(exc), "project_id": project_id},
            )

    # Prioritize risks
    prioritization = await prioritize_risks(agent, project_id, portfolio_id)

    # Get top risks
    top_risks = await get_top_risks(agent, project_id, 10)

    # Generate risk matrix
    risk_matrix = await generate_risk_matrix(agent, project_id, portfolio_id)

    # Get mitigation status
    mitigation_status = await _get_mitigation_status(agent, project_id)
    external_risk_signals = []
    if project_id:
        external_risk_signals = await collect_external_risk_signals(agent, project_id)

    return {
        "project_id": project_id,
        "portfolio_id": portfolio_id,
        "risk_summary": {
            "total_risks": prioritization["total_risks"],
            "high_risks": prioritization["high_risks"],
            "medium_risks": prioritization["medium_risks"],
            "low_risks": prioritization["low_risks"],
        },
        "top_risks": top_risks,
        "risk_matrix": risk_matrix,
        "mitigation_status": mitigation_status,
        "external_risk_research": external_risk_research,
        "external_risk_signals": external_risk_signals,
        "risk_data": {
            "project_id": project_id,
            "project_risk_level": (
                "high"
                if prioritization.get("high_risks", 0)
                else "medium" if prioritization.get("medium_risks", 0) else "low"
            ),
            "task_risks": [
                {
                    "task_id": item.get("task_id"),
                    "risk_id": item.get("risk_id"),
                    "risk_level": str(item.get("risk_level", "low")).lower(),
                    "score": item.get("score", 0),
                }
                for item in prioritization.get("ranked_risks", [])
                if item.get("task_id")
            ],
        },
        "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _get_mitigation_status(
    agent: RiskManagementAgent, project_id: str | None
) -> dict[str, Any]:
    """Get mitigation plan status summary."""
    plans = list(agent.mitigation_plans.values())
    if agent.db_service:
        try:
            plans = await agent.db_service.query("mitigation_plans", limit=500)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            plans = plans
    if project_id:
        valid_risks = {
            risk_id
            for risk_id, risk in agent.risk_register.items()
            if risk.get("project_id") == project_id
        }
        plans = [plan for plan in plans if plan.get("risk_id") in valid_risks]

    status_counts = {"planned": 0, "in_progress": 0, "completed": 0, "total_plans": len(plans)}
    for plan in plans:
        status = str(plan.get("status", "planned")).lower().replace(" ", "_")
        if status in status_counts:
            status_counts[status] += 1
    return status_counts
