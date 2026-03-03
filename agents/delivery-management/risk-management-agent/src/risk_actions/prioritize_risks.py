"""Action handler for risk prioritization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from risk_utils import classify_risk_level

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def prioritize_risks(
    agent: RiskManagementAgent, project_id: str | None, portfolio_id: str | None
) -> dict[str, Any]:
    """
    Prioritize and rank risks.

    Returns ranked risk list.
    """
    agent.logger.info(
        "Prioritizing risks for project=%s, portfolio=%s", project_id, portfolio_id
    )

    # Filter risks
    risks_to_prioritize = []
    for risk_id, risk in agent.risk_register.items():
        if project_id and risk.get("project_id") != project_id:
            continue
        if portfolio_id and risk.get("portfolio_id") != portfolio_id:
            continue
        risks_to_prioritize.append(risk)

    # Calculate risk exposure (probability x impact)
    for risk in risks_to_prioritize:
        risk["exposure"] = risk.get("probability", 0) * risk.get("impact", 0)

    # Rank by exposure
    ranked_risks = sorted(risks_to_prioritize, key=lambda x: x.get("exposure", 0), reverse=True)

    # Categorize by risk level
    high_risks = [r for r in ranked_risks if r["exposure"] >= agent.high_risk_threshold]
    medium_risks = [r for r in ranked_risks if 5 <= r["exposure"] < agent.high_risk_threshold]
    low_risks = [r for r in ranked_risks if r["exposure"] < 5]

    return {
        "total_risks": len(ranked_risks),
        "high_risks": len(high_risks),
        "medium_risks": len(medium_risks),
        "low_risks": len(low_risks),
        "ranked_risks": [
            {
                "risk_id": r["risk_id"],
                "title": r["title"],
                "category": r["category"],
                "score": r["exposure"],
                "probability": r.get("probability"),
                "impact": r.get("impact"),
                "status": r.get("status"),
                "risk_level": await classify_risk_level(agent, float(r.get("exposure", 0) or 0)),
                "project_id": r.get("project_id"),
                "task_id": r.get("task_id"),
            }
            for r in ranked_risks
        ],
    }
