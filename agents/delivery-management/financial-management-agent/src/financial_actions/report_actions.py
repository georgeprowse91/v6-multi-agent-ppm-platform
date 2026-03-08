"""Action handlers for financial reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from financial_management_agent import FinancialManagementAgent


async def generate_report(
    agent: FinancialManagementAgent,
    report_type: str,
    filters: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Generate financial reports.

    Returns report data for visualization.
    """
    agent.logger.info("Generating %s report", report_type)

    if report_type == "summary":
        return await agent._generate_summary_report(filters, tenant_id=tenant_id)
    elif report_type == "variance":
        return await agent._generate_variance_report(filters, tenant_id=tenant_id)
    elif report_type == "forecast":
        return await agent._generate_forecast_report(filters, tenant_id=tenant_id)
    elif report_type == "cash_flow":
        return await agent._generate_cash_flow_report(filters, tenant_id=tenant_id)
    elif report_type == "profitability":
        return await agent._generate_profitability_report(filters, tenant_id=tenant_id)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


async def get_financial_summary(
    agent: FinancialManagementAgent,
    project_id: str | None,
    portfolio_id: str | None,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Get financial summary for a project or portfolio.

    Returns comprehensive financial overview.
    """
    agent.logger.info(
        "Getting financial summary for project=%s, portfolio=%s", project_id, portfolio_id
    )

    if project_id:
        return await agent._get_project_financial_summary(project_id, tenant_id=tenant_id)
    elif portfolio_id:
        return await agent._get_portfolio_financial_summary(portfolio_id, tenant_id=tenant_id)
    else:
        raise ValueError("Either project_id or portfolio_id must be provided")
