"""Action handlers for profitability and currency conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from financial_utils import calculate_irr, calculate_npv, calculate_payback_period

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def calculate_profitability(
    agent: FinancialManagementAgent,
    project_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Calculate profitability metrics including ROI, NPV, and IRR."""
    agent.logger.info("Calculating profitability for project: %s", project_id)

    # Get budget and actuals
    budget = await agent._get_budget_for_project(project_id, tenant_id=tenant_id)
    agent.actuals.get(project_id) or agent.actuals_store.get(tenant_id, project_id) or {}
    forecast = (
        agent.forecasts.get(project_id) or agent.forecast_store.get(tenant_id, project_id) or {}
    )

    # Get benefit cash flows
    benefits = await agent._get_project_benefits(project_id)

    # Calculate metrics
    total_cost = (
        forecast.get("eac", budget.get("total_amount", 0))  # type: ignore
        if forecast
        else budget.get("total_amount", 0)  # type: ignore
    )
    total_benefits = sum(benefits.get("cash_flows", []))

    # Calculate NPV
    discount_rate = agent.config.get("discount_rate", 0.10) if agent.config else 0.10
    npv = calculate_npv(total_cost, benefits.get("cash_flows", []), discount_rate)

    # Calculate IRR
    irr = calculate_irr(total_cost, benefits.get("cash_flows", []))

    # Calculate ROI
    roi = (total_benefits - total_cost) / total_cost if total_cost > 0 else 0

    # Calculate payback period
    payback_period = calculate_payback_period(total_cost, benefits.get("cash_flows", []))

    return {
        "project_id": project_id,
        "total_cost": total_cost,
        "total_benefits": total_benefits,
        "npv": npv,
        "irr": irr,
        "roi": roi,
        "roi_percentage": roi * 100,
        "payback_period_months": payback_period,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def convert_currency(
    agent: FinancialManagementAgent,
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict[str, Any]:
    """Convert amount between currencies."""
    agent.logger.info("Converting %s %s to %s", amount, from_currency, to_currency)

    exchange_rates = await agent.exchange_rate_provider.get_rates()

    if from_currency not in exchange_rates["rates"] or to_currency not in exchange_rates["rates"]:
        raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")

    # Convert to AUD first, then to target currency
    base_amount = amount / exchange_rates["rates"][from_currency]
    converted_amount = base_amount * exchange_rates["rates"][to_currency]

    return {
        "original_amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": converted_amount,
        "exchange_rate": exchange_rates["rates"][to_currency]
        / exchange_rates["rates"][from_currency],
        "conversion_date": datetime.now(timezone.utc).isoformat(),
        "rate_as_of": exchange_rates["as_of"],
    }
