"""Action handlers for data queries and dashboard retrieval."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import summarize_health_portfolio

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_query_data(
    agent: AnalyticsInsightsAgent, query: str, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute data query.

    Returns query results.
    """
    agent.logger.info("Executing query: %s", query)

    parsed_query = await _parse_query(query)
    results = await _execute_query(parsed_query, filters)
    formatted_results = await _format_query_results(results)

    return {
        "query": query,
        "result_count": len(results),
        "results": formatted_results,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


async def handle_get_dashboard(
    agent: AnalyticsInsightsAgent, dashboard_id: str
) -> dict[str, Any]:
    """
    Get dashboard data.

    Returns dashboard with current data.
    """
    agent.logger.info("Retrieving dashboard: %s", dashboard_id)

    dashboard = agent.dashboards.get(dashboard_id)
    if not dashboard:
        raise ValueError(f"Dashboard not found: {dashboard_id}")

    # Refresh widget data
    widget_data = await _refresh_widget_data(agent, dashboard.get("widgets", []))

    return {
        "dashboard_id": dashboard_id,
        "name": dashboard.get("name"),
        "description": dashboard.get("description"),
        "widgets": widget_data,
        "last_refreshed": datetime.now(timezone.utc).isoformat(),
    }


async def handle_natural_language_query(
    agent: AnalyticsInsightsAgent, question: str | None, context: dict[str, Any]
) -> dict[str, Any]:
    """Answer natural language analytics queries."""
    if not question:
        raise ValueError("question is required")
    response = await agent.language_service.answer(question, context)
    return {
        "question": question,
        "response": response,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _parse_query(query: str) -> dict[str, Any]:
    """Parse natural language query."""
    return {"parsed": query}


async def _execute_query(
    parsed_query: dict[str, Any], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Execute data query."""
    return []


async def _format_query_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format query results."""
    return results


async def _refresh_widget_data(
    agent: AnalyticsInsightsAgent, widgets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Refresh data for dashboard widgets."""
    refreshed = []
    for widget in widgets:
        widget_data = widget.copy()
        widget_type = widget.get("type")
        if widget_type in {"health_summary", "portfolio_health"}:
            widget_data["data"] = await summarize_health_portfolio(
                agent, widget.get("tenant_id", "default")
            )
        elif widget_type == "kpi_summary":
            widget_data["data"] = list(agent.kpis.values())
        else:
            widget_data["data"] = []
        widget_data["last_refreshed"] = datetime.now(timezone.utc).isoformat()
        refreshed.append(widget_data)
    return refreshed
