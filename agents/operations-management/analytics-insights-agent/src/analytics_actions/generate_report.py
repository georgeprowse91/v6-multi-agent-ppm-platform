"""Action handler for report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import generate_report_id, summarize_health_portfolio

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_generate_report(
    agent: AnalyticsInsightsAgent, tenant_id: str, report_spec: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate analytical report.

    Returns report content.
    """
    agent.logger.info("Generating report: %s", report_spec.get("title"))

    # Generate report ID
    report_id = await generate_report_id()

    # Collect data for report
    data = await _collect_report_data(agent, tenant_id, report_spec)

    # Generate visualizations
    visualizations = await _generate_visualizations(data, report_spec)

    # Generate narrative summary
    from actions.generate_narrative import handle_generate_narrative

    narrative = await handle_generate_narrative(agent, tenant_id, data)

    # Create report record
    report = {
        "report_id": report_id,
        "title": report_spec.get("title"),
        "type": report_spec.get("type", "analytical"),
        "data": data,
        "visualizations": visualizations,
        "narrative": narrative,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": report_spec.get("requester"),
    }

    # Store report
    agent.reports[report_id] = report
    agent.analytics_output_store.upsert(tenant_id, report_id, report.copy())
    await agent.report_repository.store_report(report.copy())

    return {
        "report_id": report_id,
        "title": report["title"],
        "visualizations": len(visualizations),
        "narrative": narrative,
        "download_url": f"/reports/{report_id}/download",
    }


async def _collect_report_data(
    agent: AnalyticsInsightsAgent, tenant_id: str, report_spec: dict[str, Any]
) -> dict[str, Any]:
    """Collect data for report."""
    report_type = report_spec.get("type", "analytical")
    if report_type in {"health_summary", "portfolio_health"}:
        return await summarize_health_portfolio(agent, tenant_id)
    if report_type == "kpi_summary":
        return {
            "kpis": list(agent.kpis.values()),
            "kpi_count": len(agent.kpis),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    return {}


async def _generate_visualizations(
    data: dict[str, Any], report_spec: dict[str, Any]
) -> list[dict[str, Any]]:
    """Generate visualizations for report."""
    report_type = report_spec.get("type", "analytical")
    visualizations: list[dict[str, Any]] = []
    if report_type in {"health_summary", "portfolio_health"}:
        visualizations.append(
            {
                "type": "status_distribution",
                "title": "Health Status Distribution",
                "data": data.get("status_counts", {}),
            }
        )
        visualizations.append(
            {
                "type": "average_metrics",
                "title": "Average Health Metrics",
                "data": data.get("average_metrics", {}),
            }
        )
    elif report_type == "kpi_summary":
        visualizations.append(
            {
                "type": "kpi_table",
                "title": "Tracked KPIs",
                "data": data.get("kpis", []),
            }
        )
    return visualizations
