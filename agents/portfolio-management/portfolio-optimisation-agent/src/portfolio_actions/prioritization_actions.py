"""
Portfolio Prioritization Action Handlers

Handlers for:
- prioritize_portfolio
- calculate_alignment_score
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from portfolio_strategy_agent import PortfolioStrategyAgent


async def prioritize_portfolio(
    agent: PortfolioStrategyAgent,
    projects: list[dict[str, Any]],
    criteria_weights: dict[str, float],
    *,
    tenant_id: str,
    correlation_id: str,
    portfolio_id: str | None = None,
    cycle: str = "ad-hoc",
) -> dict[str, Any]:
    """
    Apply multi-criteria decision analysis to rank portfolio projects.

    Returns ranked portfolio with scores and justification.
    """
    agent.logger.info("Prioritizing portfolio with %s projects", len(projects))

    ranked_projects = []
    portfolio_id = portfolio_id or await agent._generate_portfolio_id()

    for project in projects:
        strategic_score = await agent._score_strategic_alignment(project)
        roi_score = await agent._score_roi(project)
        risk_score = await agent._score_risk(project)
        resource_score = await agent._score_resource_feasibility(project)
        compliance_score = await agent._score_compliance(project)

        overall_score = (
            strategic_score * criteria_weights.get("strategic_alignment", 0.30)
            + roi_score * criteria_weights.get("roi", 0.25)
            + risk_score * criteria_weights.get("risk", 0.20)
            + resource_score * criteria_weights.get("resource_feasibility", 0.15)
            + compliance_score * criteria_weights.get("compliance", 0.10)
        )

        recommendation = (
            "approve" if overall_score >= 0.7 else "defer" if overall_score >= 0.5 else "reject"
        )
        policy_outcome = await agent._apply_policy_guardrails(
            project_id=str(project.get("project_id")),
            recommendation=recommendation,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        if policy_outcome["decision"] == "deny" and recommendation == "approve":
            recommendation = "defer"

        ranked_projects.append(
            {
                "project_id": project.get("project_id"),
                "project_name": project.get("name"),
                "overall_score": overall_score,
                "scores": {
                    "strategic_alignment": strategic_score,
                    "roi": roi_score,
                    "risk": risk_score,
                    "resource_feasibility": resource_score,
                    "compliance": compliance_score,
                },
                "recommendation": recommendation,
                "policy_decision": policy_outcome,
            }
        )

    ranked_projects.sort(key=lambda x: x["overall_score"], reverse=True)

    for idx, project in enumerate(ranked_projects, start=1):
        project["rank"] = idx

    portfolio_record = {
        "portfolio_id": portfolio_id,
        "cycle": cycle,
        "ranked_projects": ranked_projects,
        "criteria_weights": criteria_weights,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.portfolio_store.upsert(tenant_id, portfolio_id, portfolio_record)
    if agent.db_service:
        await agent.db_service.store("portfolio_strategy", portfolio_id, portfolio_record)

    await agent._publish_portfolio_prioritized(
        portfolio_record,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    agent._emit_audit_event(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        portfolio_id=portfolio_id,
        approved_count=len([p for p in ranked_projects if p["recommendation"] == "approve"]),
    )

    return {
        "portfolio_id": portfolio_id,
        "ranked_projects": ranked_projects,
        "criteria_weights": criteria_weights,
        "total_projects": len(ranked_projects),
        "approved_count": len([p for p in ranked_projects if p["recommendation"] == "approve"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def calculate_alignment_score(
    agent: PortfolioStrategyAgent,
    project: dict[str, Any],
    objectives: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate strategic alignment scores for a project.

    Returns alignment scores for each strategic objective.
    """
    agent.logger.info("Calculating alignment score for project: %s", project.get("project_id"))

    alignment_details = []

    for objective in objectives:
        score = await agent._calculate_objective_alignment(project, objective)
        alignment_details.append(
            {
                "objective_id": objective.get("id"),
                "objective_name": objective.get("name"),
                "alignment_score": score,
                "contribution": objective.get("weight", 1.0) * score,
            }
        )

    total_weight = sum(obj.get("weight", 1.0) for obj in objectives)
    overall_score = sum(detail["contribution"] for detail in alignment_details)
    if total_weight > 0:
        overall_score /= total_weight

    return {
        "project_id": project.get("project_id"),
        "overall_alignment_score": overall_score,
        "objective_alignments": alignment_details,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
