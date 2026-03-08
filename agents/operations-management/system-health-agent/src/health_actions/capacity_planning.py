"""Action handlers for capacity planning and forecasting."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from health_utils import linear_regression_forecast, summarize_trend

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent


async def get_capacity_recommendations(
    agent: SystemHealthAgent, service_name: str | None = None
) -> dict[str, Any]:
    """Get capacity planning recommendations.  Returns scaling recommendations."""
    agent.logger.info("Getting capacity recommendations for: %s", service_name or "all services")

    utilization_trends = await analyze_utilization_trends(agent, service_name)

    forecasts = await forecast_capacity_needs(utilization_trends)

    recommendations = await _generate_capacity_recommendations(forecasts)

    return {
        "service_name": service_name,
        "utilization_trends": utilization_trends,
        "forecasts": forecasts,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def forecast_capacity(agent: SystemHealthAgent, service_name: str | None) -> dict[str, Any]:
    utilization_trends = await analyze_utilization_trends(agent, service_name)
    forecasts = await forecast_capacity_needs(utilization_trends)
    return {
        "service_name": service_name,
        "trends": utilization_trends,
        "forecasts": forecasts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def analyze_utilization_trends(
    agent: SystemHealthAgent, service_name: str | None
) -> dict[str, Any]:
    """Analyze resource utilization trends."""
    trends: dict[str, Any] = {}
    target_service = service_name or "platform"
    for metric in ("cpu_usage", "memory_usage", "storage_usage"):
        values = await agent._query_metrics(target_service, metric, {"days": 7})
        trend_data = summarize_trend(values)
        trends[f"{metric}_trend"] = trend_data["direction"]
        trends[f"{metric}_series"] = trend_data["series"]
    return trends


async def forecast_capacity_needs(trends: dict[str, Any]) -> dict[str, Any]:
    """Forecast future capacity needs."""
    forecasts: dict[str, Any] = {}
    for metric in ("cpu_usage", "memory_usage", "storage_usage"):
        series = trends.get(f"{metric}_series", [])
        forecast = linear_regression_forecast(series, horizon_days=30)
        if forecast is not None:
            forecasts[f"{metric}_forecast_30d"] = forecast
    return forecasts


async def _generate_capacity_recommendations(forecasts: dict[str, Any]) -> list[str]:
    """Generate capacity recommendations."""
    recommendations: list[str] = []

    if forecasts.get("cpu_usage_forecast_30d", 0) > 80:
        recommendations.append("Consider scaling up CPU resources within 30 days")

    if forecasts.get("memory_usage_forecast_30d", 0) > 80:
        recommendations.append("Consider scaling up memory resources within 30 days")

    if forecasts.get("storage_usage_forecast_30d", 0) > 80:
        recommendations.append("Plan for storage expansion within 30 days")

    if not recommendations:
        recommendations.append("Current capacity is adequate for forecasted needs")

    return recommendations
