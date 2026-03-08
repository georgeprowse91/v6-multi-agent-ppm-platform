"""
Business Case Analysis Action Handlers

Handlers for:
- compare_to_historical
- generate_recommendation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from business_case_utils import calculate_confidence

if TYPE_CHECKING:
    from business_case_investment_agent import BusinessCaseInvestmentAgent


async def compare_to_historical(
    agent: BusinessCaseInvestmentAgent,
    request_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare proposed initiative to historical projects for benchmarking.

    Returns similar projects with outcomes.
    """
    agent.logger.info("Comparing to historical projects")

    query_text = (
        f"{request_data.get('title','')} {request_data.get('description','')} "
        f"{request_data.get('project_type','')}"
    )
    similar_projects: list[dict[str, Any]] = []
    for match in agent.vector_index.search(query_text, top_k=5):
        similar_projects.append(
            {
                "business_case_id": match.doc_id,
                "title": match.metadata.get("title"),
                "roi": match.metadata.get("financial_metrics", {}).get("roi_percentage", 0),
                "payback_period": match.metadata.get("financial_metrics", {}).get(
                    "payback_period_months", 0
                ),
                "similarity": round(match.score, 3),
            }
        )

    benchmark_roi = 0.0
    benchmark_payback = 0.0
    if similar_projects:
        benchmark_roi = sum(item.get("roi", 0.0) for item in similar_projects) / len(
            similar_projects
        )
        benchmark_payback = sum(item.get("payback_period", 0.0) for item in similar_projects) / len(
            similar_projects
        )

    return {
        "similar_projects": similar_projects,
        "benchmark_roi": benchmark_roi,
        "benchmark_payback": benchmark_payback,
        "comparison_window_years": agent.comparison_window_years,
    }


async def generate_recommendation(
    agent: BusinessCaseInvestmentAgent,
    business_case_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Generate investment recommendation with confidence level.

    Returns recommendation (approve/defer/reject) with rationale.
    """
    agent.logger.info("Generating recommendation for business case: %s", business_case_id)

    business_case = agent.business_case_store.get(tenant_id, business_case_id)
    if not business_case:
        raise ValueError(f"Business case not found: {business_case_id}")

    metrics = business_case.get("financial_metrics", {})
    roi = metrics.get("roi_percentage", 0)
    payback_period = metrics.get("payback_period_months", 999)
    npv = metrics.get("npv", 0)

    historical_comparison = await compare_to_historical(agent, business_case)
    confidence = calculate_confidence(metrics, historical_comparison, agent.min_roi_threshold)

    if roi >= agent.min_roi_threshold and payback_period <= agent.max_payback_period and npv > 0:
        recommendation = "approve"
        rationale = (
            f"Strong financial metrics: ROI {roi:.1%}, "
            f"payback period {payback_period} months, positive NPV"
        )
    elif roi >= agent.min_roi_threshold * 0.7:
        recommendation = "defer"
        rationale = "Moderate financial metrics. Consider phased approach or MVP to reduce risk."
    else:
        recommendation = "reject"
        rationale = (
            f"Financial metrics below thresholds: ROI {roi:.1%} "
            f"(required: {agent.min_roi_threshold:.1%})"
        )

    narrative = await agent._generate_recommendation_narrative(
        business_case, recommendation, rationale
    )

    recommendation_payload = {
        "business_case_id": business_case_id,
        "recommendation": recommendation,
        "confidence_level": confidence,
        "rationale": rationale,
        "narrative": narrative,
        "phasing_suggestion": "Consider MVP approach" if recommendation == "defer" else None,
        "comparable_projects": historical_comparison.get("similar_projects", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await agent._publish_investment_recommendation(
        business_case,
        recommendation_payload,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    return recommendation_payload
