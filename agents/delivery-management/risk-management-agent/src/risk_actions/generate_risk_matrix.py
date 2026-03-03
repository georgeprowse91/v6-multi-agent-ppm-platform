"""Action handler for risk matrix generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from risk_utils import classify_risk_level

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def generate_risk_matrix(
    agent: RiskManagementAgent, project_id: str | None, portfolio_id: str | None
) -> dict[str, Any]:
    """
    Generate risk matrix (probability vs impact).

    Returns risk matrix visualization data.
    """
    agent.logger.info(
        "Generating risk matrix for project=%s, portfolio=%s", project_id, portfolio_id
    )

    # Filter risks
    risks_to_plot = []
    for risk_id, risk in agent.risk_register.items():
        if project_id and risk.get("project_id") != project_id:
            continue
        if portfolio_id and risk.get("portfolio_id") != portfolio_id:
            continue
        risks_to_plot.append(risk)

    # Create matrix data
    matrix_data = []
    for risk in risks_to_plot:
        matrix_data.append(
            {
                "risk_id": risk["risk_id"],
                "title": risk["title"],
                "probability": risk.get("probability", 0),
                "impact": risk.get("impact", 0),
                "score": risk.get("score", 0),
                "category": risk.get("category"),
                "status": risk.get("status"),
                "risk_level": await classify_risk_level(agent, float(risk.get("score", 0) or 0)),
                "project_id": risk.get("project_id"),
                "task_id": risk.get("task_id"),
            }
        )

    return {
        "matrix_data": matrix_data,
        "total_risks": len(matrix_data),
        "probability_scale": agent.probability_scale,
        "impact_scale": agent.impact_scale,
    }
