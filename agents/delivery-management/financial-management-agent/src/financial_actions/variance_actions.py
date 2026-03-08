"""Action handlers for variance analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def analyze_variance(
    agent: FinancialManagementAgent,
    project_id: str,
    time_period: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Analyze cost and schedule variances.

    Returns variance analysis with trends and alerts.
    """
    agent.logger.info("Analyzing variance for project: %s", project_id)

    # Get budget baseline
    budget = await agent._get_budget_for_project(project_id, tenant_id=tenant_id)
    if not budget:
        raise ValueError(f"No budget found for project: {project_id}")

    # Get actual costs
    actuals = agent.actuals.get(project_id) or agent.actuals_store.get(tenant_id, project_id) or {}
    total_actual = actuals.get("total_actual", 0)

    # Get forecast/EAC
    forecast = (
        agent.forecasts.get(project_id) or agent.forecast_store.get(tenant_id, project_id) or {}
    )
    eac = forecast.get("eac", budget.get("total_amount", 0))

    # Calculate variances
    budget_variance = total_actual - budget.get("total_amount", 0)
    budget_variance_pct = budget_variance / budget.get("total_amount", 1)

    forecast_variance = eac - budget.get("total_amount", 0)
    forecast_variance_pct = forecast_variance / budget.get("total_amount", 1)

    # Analyze variance by category
    variance_by_category = await agent._analyze_variance_by_category(
        project_id, budget, tenant_id=tenant_id
    )

    # Identify variance drivers
    resource_plans = await agent._get_resource_plans(project_id)
    schedule_progress = await agent._get_schedule_progress(project_id)
    drivers = await agent._identify_variance_drivers(
        project_id, variance_by_category, resource_plans, schedule_progress
    )

    # Generate alerts if thresholds exceeded
    alerts = []
    if (
        abs(budget_variance_pct) > agent.variance_threshold_pct
        or abs(budget_variance) > agent.variance_threshold_abs
    ):
        alerts.append(
            {
                "severity": "high" if abs(budget_variance_pct) > 0.20 else "medium",
                "type": "budget_variance",
                "message": f"Budget variance of {budget_variance_pct:.1%} exceeds threshold",
                "recommended_actions": await agent._suggest_corrective_actions(budget_variance_pct),
            }
        )

    narrative = await agent._generate_variance_narrative(
        budget_variance_pct, forecast_variance_pct, drivers
    )

    await agent._publish_financial_event(
        "finance.variance.analyzed",
        {
            "project_id": project_id,
            "budget_variance": budget_variance,
            "forecast_variance": forecast_variance,
            "variance_drivers": drivers,
        },
    )

    return {
        "project_id": project_id,
        "budget_baseline": budget.get("total_amount", 0),
        "total_actual": total_actual,
        "eac": eac,
        "budget_variance": budget_variance,
        "budget_variance_pct": budget_variance_pct,
        "forecast_variance": forecast_variance,
        "forecast_variance_pct": forecast_variance_pct,
        "variance_by_category": variance_by_category,
        "variance_drivers": drivers,
        "alerts": alerts,
        "narrative": narrative,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
