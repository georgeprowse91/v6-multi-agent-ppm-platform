"""Action handlers for cost tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def track_costs(
    agent: FinancialManagementAgent,
    cost_data: dict[str, Any],
    *,
    tenant_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Track actual costs and accruals.

    Returns cost tracking confirmation.
    """
    agent.logger.info("Tracking costs for project: %s", cost_data.get("project_id"))

    # Import cost transactions from ERP
    transactions = await agent._import_cost_transactions(cost_data.get("project_id"))  # type: ignore

    # Match costs to WBS elements and classify costs
    matched_costs = await agent._match_costs_to_wbs(transactions)
    enriched_costs = await agent._enrich_cost_transactions(matched_costs)

    # Calculate accrued expenses
    accruals = await agent._calculate_accruals(
        cost_data.get("project_id"), tenant_id=tenant_id  # type: ignore
    )

    # Update actuals
    project_id = cost_data.get("project_id")
    if project_id not in agent.actuals:
        agent.actuals[project_id] = {"transactions": [], "total_actual": 0, "by_category": {}}

    total_actual = sum(t.get("amount", 0) for t in enriched_costs)
    agent.actuals[project_id]["transactions"].extend(enriched_costs)
    agent.actuals[project_id]["total_actual"] = total_actual

    # Calculate by category
    by_category = {}
    for transaction in enriched_costs:
        category = transaction.get("category", "other")
        if category not in by_category:
            by_category[category] = 0
        by_category[category] += transaction.get("amount", 0)

    agent.actuals[project_id]["by_category"] = by_category

    if project_id:
        agent.actuals_store.upsert(tenant_id, project_id, agent.actuals[project_id])

    agent._emit_budget_audit(
        action="budget.costs.tracked",
        budget={
            "project_id": project_id,
            "amount": total_actual,
            "currency": agent.default_currency,
        },
        tenant_id=tenant_id,
        correlation_id=None,
        actor_id=actor_id,
    )

    await agent._publish_financial_event(
        "finance.costs.tracked",
        {
            "project_id": project_id,
            "total_actual": total_actual,
            "currency": agent.default_currency,
            "accruals": accruals,
        },
    )

    return {
        "project_id": project_id,
        "transactions_imported": len(enriched_costs),
        "total_actual": total_actual,
        "by_category": by_category,
        "accruals": accruals,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
