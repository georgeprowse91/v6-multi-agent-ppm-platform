"""Action handler for AI-generated insights."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import summarize_health_portfolio

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_get_insights(
    agent: AnalyticsInsightsAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Get AI-generated insights.

    Returns insights and recommendations.
    """
    agent.logger.info("Generating insights")

    # Collect relevant data
    data = await collect_insights_data(agent, filters)

    # Apply anomaly detection
    anomalies = await detect_anomalies(data)

    # Identify patterns
    patterns = await identify_patterns(data)

    # Generate insights
    insights = await generate_insights(data, anomalies, patterns)

    # Generate recommendations
    recommendations = await generate_recommendations(insights)

    response = {
        "insights": insights,
        "anomalies": anomalies,
        "patterns": patterns,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    tenant_id = filters.get("tenant_id", "default")
    if agent.event_bus:
        await agent.event_bus.publish(
            "analytics.insights.generated",
            {
                "tenant_id": tenant_id,
                "insights": insights,
                "recommendations": recommendations,
                "generated_at": response["generated_at"],
            },
        )
    return response


# ---------------------------------------------------------------------------
# Shared insight helpers (also used by periodic_report)
# ---------------------------------------------------------------------------

async def collect_insights_data(agent: AnalyticsInsightsAgent, filters: dict[str, Any]) -> dict[str, Any]:
    """Collect data for insights generation."""
    tenant_id = filters.get("tenant_id", "default")
    health_summary = await summarize_health_portfolio(agent, tenant_id)
    return {
        "health_summary": health_summary,
        "project_metrics": filters.get("project_metrics", []),
    }


async def detect_anomalies(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect anomalies in data."""
    anomalies: list[dict[str, Any]] = []
    for metric in data.get("project_metrics", []):
        cycle_time_days = metric.get("cycle_time_days")
        if isinstance(cycle_time_days, (int, float)) and cycle_time_days > 20:
            anomalies.append(
                {
                    "project_id": metric.get("project_id"),
                    "metric": "cycle_time_days",
                    "value": cycle_time_days,
                    "reason": "Consistently high cycle time",
                }
            )
        budget_variance_pct = metric.get("budget_variance_pct")
        if isinstance(budget_variance_pct, (int, float)) and abs(budget_variance_pct) > 0.15:
            anomalies.append(
                {
                    "project_id": metric.get("project_id"),
                    "metric": "budget_variance_pct",
                    "value": budget_variance_pct,
                    "reason": "Budget variance outside tolerated range",
                }
            )
    return anomalies


async def identify_patterns(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Identify patterns in data."""
    patterns: list[dict[str, Any]] = []
    project_metrics = data.get("project_metrics", [])
    if not project_metrics:
        return patterns
    delayed_projects = [
        item for item in project_metrics if float(item.get("late_task_ratio", 0)) >= 0.25
    ]
    if delayed_projects:
        patterns.append(
            {
                "pattern": "recurring_late_tasks",
                "count": len(delayed_projects),
                "description": "Multiple projects have high late-task ratios",
            }
        )
    scope_creep_projects = [
        item for item in project_metrics if float(item.get("scope_creep_count", 0)) >= 2
    ]
    if scope_creep_projects:
        patterns.append(
            {
                "pattern": "recurring_scope_creep",
                "count": len(scope_creep_projects),
                "description": "Scope creep appears repeatedly across projects",
            }
        )
    return patterns


async def generate_insights(
    data: dict[str, Any], anomalies: list[dict[str, Any]], patterns: list[dict[str, Any]]
) -> list[str]:
    """Generate AI insights."""
    insights = []
    if anomalies:
        insights.append(f"Detected {len(anomalies)} anomalies requiring investigation")
    if patterns:
        insights.append(f"Identified {len(patterns)} recurring patterns")
    health_summary = data.get("health_summary", {})
    concerns = health_summary.get("concerns", [])
    if concerns:
        insights.append(f"{len(concerns)} portfolio health concerns identified")
    return insights


async def generate_recommendations(insights: list[str]) -> list[str]:
    """Generate recommendations from insights."""
    recommendations = []
    for insight in insights:
        lowered = insight.lower()
        if "anomal" in lowered:
            recommendations.append("Investigate anomalies with the delivery leads")
        if "concerns" in lowered:
            recommendations.append("Schedule a portfolio health review and mitigation planning")
    if not recommendations:
        recommendations.append("Maintain current monitoring cadence")
    return recommendations
