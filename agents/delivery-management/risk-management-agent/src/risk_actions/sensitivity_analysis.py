"""Action handler for sensitivity analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from risk_utils import (
    calculate_quantitative_impact,
    publish_risk_event,
    store_risk_dataset,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def perform_sensitivity_analysis(
    agent: RiskManagementAgent, project_id: str
) -> dict[str, Any]:
    """
    Perform sensitivity analysis on project risks.

    Returns sensitivity analysis results.
    """
    agent.logger.info("Performing sensitivity analysis for project: %s", project_id)

    # Get project risks
    project_risks = [r for r in agent.risk_register.values() if r.get("project_id") == project_id]

    # Analyze sensitivity to each risk factor
    sensitivity_results = []
    for risk in project_risks:
        sensitivity = await _analyze_risk_sensitivity(agent, risk)
        sensitivity_results.append(
            {
                "risk_id": risk["risk_id"],
                "title": risk["title"],
                "sensitivity_score": sensitivity.get("score"),
                "impact_on_schedule": sensitivity.get("schedule_impact"),
                "impact_on_cost": sensitivity.get("cost_impact"),
                "tornado_range": sensitivity.get("tornado_range"),
            }
        )

    # Sort by sensitivity score
    sorted_results = sorted(sensitivity_results, key=lambda x: x["sensitivity_score"], reverse=True)

    results = {
        "project_id": project_id,
        "sensitivity_analysis": sorted_results,
        "most_sensitive_risk": sorted_results[0] if sorted_results else None,
    }
    if sorted_results:
        await store_risk_dataset(
            agent,
            "sensitivity_analysis",
            [{"project_id": project_id, "results": sorted_results}],
            domain="analytics",
        )
        await publish_risk_event(
            agent,
            "risk.sensitivity_analyzed",
            {"project_id": project_id, "risk_count": len(sorted_results)},
        )
    return results


async def _analyze_risk_sensitivity(
    agent: RiskManagementAgent, risk: dict[str, Any]
) -> dict[str, Any]:
    """Analyze sensitivity of outcomes to this risk."""
    quantitative = await calculate_quantitative_impact(agent, risk)
    schedule = quantitative.get("schedule_impact_days", 0)
    cost = quantitative.get("cost_impact", 0)
    low_factor = 0.7
    high_factor = 1.3
    return {
        "score": risk.get("score", 0) * 2,
        "schedule_impact": schedule,
        "cost_impact": cost,
        "tornado_range": {
            "schedule_low": round(schedule * low_factor, 2),
            "schedule_high": round(schedule * high_factor, 2),
            "cost_low": round(cost * low_factor, 2),
            "cost_high": round(cost * high_factor, 2),
        },
    }
