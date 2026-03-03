"""Action handler for periodic report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from actions.insights import (
    collect_insights_data,
    detect_anomalies,
    generate_insights,
    generate_recommendations,
    identify_patterns,
)
from analytics_utils import generate_report_id

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_generate_periodic_report(
    agent: AnalyticsInsightsAgent, tenant_id: str, period: str, filters: dict[str, Any]
) -> dict[str, Any]:
    """Generate periodic analytics report used by continuous improvement workflows."""
    report_id = await generate_report_id()
    metrics = filters.get("project_metrics", [])
    cycle_times = [float(metric.get("cycle_time_days", 0)) for metric in metrics]
    risk_occurrences = [int(metric.get("risk_occurrences", 0)) for metric in metrics]
    budget_variances = [float(metric.get("budget_variance_pct", 0)) for metric in metrics]

    insights_data = await collect_insights_data(agent, {"tenant_id": tenant_id, **filters})
    anomalies = await detect_anomalies(insights_data)
    patterns = await identify_patterns(insights_data)
    insights = await generate_insights(insights_data, anomalies, patterns)
    recommendations = await generate_recommendations(insights)

    report = {
        "report_id": report_id,
        "type": "periodic_performance",
        "period": period,
        "summary": {
            "project_count": len(metrics),
            "avg_cycle_time_days": (
                round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0
            ),
            "risk_occurrences_total": sum(risk_occurrences),
            "avg_budget_variance_pct": (
                round(sum(budget_variances) / len(budget_variances), 4)
                if budget_variances
                else 0
            ),
        },
        "trends": patterns,
        "anomalies": anomalies,
        "insights": insights,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.reports[report_id] = report
    agent.analytics_output_store.upsert(tenant_id, report_id, report.copy())
    await agent.report_repository.store_report(report.copy())

    if agent.event_bus:
        await agent.event_bus.publish(
            "analytics.periodic_report.generated",
            {
                "tenant_id": tenant_id,
                "report": report,
            },
        )

    return report
