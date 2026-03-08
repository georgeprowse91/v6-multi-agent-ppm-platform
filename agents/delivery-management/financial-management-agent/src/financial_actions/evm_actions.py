"""Action handlers for Earned Value Management calculations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def calculate_evm(
    agent: FinancialManagementAgent,
    project_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Calculate Earned Value Management metrics.

    Returns EV, PV, AC, CPI, SPI, and other EVM metrics.
    """
    agent.logger.info("Calculating EVM metrics for project: %s", project_id)

    # Get budget and actuals
    budget = await agent._get_budget_for_project(project_id, tenant_id=tenant_id)
    actuals = agent.actuals.get(project_id) or agent.actuals_store.get(tenant_id, project_id) or {}

    # Get schedule progress from Schedule Agent
    schedule_progress = await agent._get_schedule_progress(project_id)
    percent_complete = schedule_progress.get("percent_complete", 0)

    # Calculate EVM metrics
    budget_at_completion = budget.get("total_amount", 0) if budget else 0
    actual_cost = actuals.get("total_actual", 0)

    # Planned Value (PV) - should be based on schedule baseline
    planned_value = budget_at_completion * schedule_progress.get(
        "planned_percent", percent_complete
    )

    # Earned Value (EV) - based on work completed
    earned_value = budget_at_completion * percent_complete

    # Cost Performance Index (CPI)
    cpi = earned_value / actual_cost if actual_cost > 0 else 1.0

    # Schedule Performance Index (SPI)
    spi = earned_value / planned_value if planned_value > 0 else 1.0

    # Cost Variance (CV)
    cv = earned_value - actual_cost

    # Schedule Variance (SV)
    sv = earned_value - planned_value

    # Estimate at Completion (EAC)
    eac = budget_at_completion / cpi if cpi > 0 else budget_at_completion

    # Estimate to Complete (ETC)
    etc = eac - actual_cost

    # Variance at Completion (VAC)
    vac = budget_at_completion - eac

    # To Complete Performance Index (TCPI)
    tcpi = (
        (budget_at_completion - earned_value) / (budget_at_completion - actual_cost)
        if (budget_at_completion - actual_cost) > 0
        else 1.0
    )

    return {
        "project_id": project_id,
        "budget_at_completion": budget_at_completion,
        "actual_cost": actual_cost,
        "planned_value": planned_value,
        "earned_value": earned_value,
        "percent_complete": percent_complete,
        "cost_performance_index": cpi,
        "schedule_performance_index": spi,
        "cost_variance": cv,
        "schedule_variance": sv,
        "estimate_at_completion": eac,
        "estimate_to_complete": etc,
        "variance_at_completion": vac,
        "to_complete_performance_index": tcpi,
        "performance_status": await agent._assess_performance_status(cpi, spi),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
