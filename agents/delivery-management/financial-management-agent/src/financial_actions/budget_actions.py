"""Action handlers for budget lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from financial_utils import generate_budget_id

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def create_budget(
    agent: FinancialManagementAgent,
    budget_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Create a new budget baseline.

    Returns budget ID and baseline confirmation.
    """
    agent.logger.info("Creating budget for project: %s", budget_data.get("project_id"))

    # Generate budget ID
    budget_id = generate_budget_id()

    # Validate cost breakdown
    cost_breakdown = budget_data.get("cost_breakdown", {})
    total_from_breakdown = sum(cost_breakdown.values())
    total_amount = budget_data.get("total_amount", 0)

    if abs(total_from_breakdown - total_amount) > 0.01:
        agent.logger.warning(
            "Cost breakdown sum (%s) doesn't match total (%s)",
            total_from_breakdown,
            total_amount,
        )

    # Create budget structure aligned to WBS
    budget = {
        "budget_id": budget_id,
        "project_id": budget_data.get("project_id"),
        "portfolio_id": budget_data.get("portfolio_id"),
        "total_amount": total_amount,
        "currency": budget_data.get("currency", agent.default_currency),
        "fiscal_year": budget_data.get("fiscal_year", datetime.now(timezone.utc).year),
        "cost_breakdown": cost_breakdown,
        "cost_type": budget_data.get("cost_type", "mixed"),  # capex, opex, or mixed
        "status": "Draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": budget_data.get("owner", "unknown"),
        "baseline_date": None,  # Set when approved
        "wbs_allocation": budget_data.get("wbs_allocation", {}),
    }

    validation = await agent._validate_budget_record(
        budget, tenant_id=tenant_id, portfolio_id=budget_data.get("portfolio_id")
    )

    # Store budget
    agent.budgets[budget_id] = budget
    agent.budget_store.upsert(tenant_id, budget_id, budget)

    approval = await agent._request_budget_approval(
        budget_id=budget_id,
        budget=budget,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        requester=actor_id,
    )

    agent._emit_budget_audit(
        action="budget.created",
        budget=budget,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    await agent._publish_financial_event(
        "finance.budget.created",
        {
            "budget_id": budget_id,
            "project_id": budget.get("project_id"),
            "total_amount": total_amount,
            "currency": budget.get("currency"),
            "status": budget.get("status"),
        },
    )

    await agent.db_service.store("budgets", budget_id, budget)
    erp_validation = await agent._validate_funding_with_erp(budget)

    return {
        "budget_id": budget_id,
        "status": "Draft",
        "total_amount": total_amount,
        "currency": budget["currency"],
        "cost_breakdown": cost_breakdown,
        "next_steps": "Submit budget for approval via Approval Workflow Agent",
        "created_at": budget["created_at"],
        "data_quality": validation,
        "approval": approval,
        "erp_validation": erp_validation,
    }


async def update_budget(
    agent: FinancialManagementAgent,
    budget_id: str,
    updates: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Update an existing budget (requires approval for baseline changes)."""
    agent.logger.info("Updating budget: %s", budget_id)

    budget = agent.budgets.get(budget_id) or agent.budget_store.get(tenant_id, budget_id)
    if not budget:
        raise ValueError(f"Budget not found: {budget_id}")

    # Check if this is a baseline change
    is_baseline_change = "total_amount" in updates or "cost_breakdown" in updates
    approval = None
    if is_baseline_change:
        agent.logger.info("Budget change requires approval for budget: %s", budget_id)
        approval = await agent._request_budget_approval(
            budget_id=budget_id,
            budget={**budget, **updates},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            requester=actor_id,
        )
        budget["status"] = "Pending Approval"

    # Apply updates
    for key, value in updates.items():
        if key in budget:
            budget[key] = value

    budget["last_updated"] = datetime.now(timezone.utc).isoformat()

    validation = await agent._validate_budget_record(
        budget, tenant_id=tenant_id, portfolio_id=budget.get("portfolio_id")
    )

    agent.budgets[budget_id] = budget
    agent.budget_store.upsert(tenant_id, budget_id, budget)
    if agent.db_service:
        await agent.db_service.store("budgets", budget_id, budget)

    agent._emit_budget_audit(
        action="budget.updated",
        budget=budget,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    await agent._publish_financial_event(
        "finance.budget.updated",
        {
            "budget_id": budget_id,
            "status": budget["status"],
            "updated_at": budget["last_updated"],
        },
    )

    return {
        "budget_id": budget_id,
        "status": budget["status"],
        "updated_at": budget["last_updated"],
        "approval": approval,
        "data_quality": validation,
    }


async def approve_budget(
    agent: FinancialManagementAgent,
    budget_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Approve a budget and lock it as baseline."""
    agent.logger.info("Approving budget: %s", budget_id)

    budget = agent.budgets.get(budget_id) or agent.budget_store.get(tenant_id, budget_id)
    if not budget:
        raise ValueError(f"Budget not found: {budget_id}")

    budget["status"] = "Approved"
    budget["baseline_date"] = datetime.now(timezone.utc).isoformat()

    agent.budgets[budget_id] = budget
    agent.budget_store.upsert(tenant_id, budget_id, budget)

    agent._emit_budget_audit(
        action="budget.approved",
        budget=budget,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    await agent._publish_financial_event(
        "finance.budget.approved",
        {
            "budget_id": budget_id,
            "baseline_date": budget["baseline_date"],
        },
    )

    return {
        "budget_id": budget_id,
        "status": "Approved",
        "baseline_date": budget["baseline_date"],
    }
