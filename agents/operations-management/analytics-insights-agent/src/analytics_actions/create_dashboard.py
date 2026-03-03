"""Action handler for dashboard creation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import configure_widgets, generate_dashboard_id, setup_refresh_schedule

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_create_dashboard(
    agent: AnalyticsInsightsAgent, tenant_id: str, dashboard_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Create interactive dashboard.

    Returns dashboard ID and configuration.
    """
    agent.logger.info("Creating dashboard: %s", dashboard_config.get("name"))

    # Generate dashboard ID
    dashboard_id = await generate_dashboard_id()

    # Validate widgets
    widgets = dashboard_config.get("widgets", [])
    if len(widgets) > agent.max_dashboard_widgets:
        raise ValueError(f"Maximum {agent.max_dashboard_widgets} widgets allowed")

    # Create widget configurations
    configured_widgets = await configure_widgets(widgets)

    # Set up data refresh schedule
    refresh_schedule = await setup_refresh_schedule(
        dashboard_config.get("refresh_interval", agent.refresh_interval_minutes)
    )

    # Create dashboard record
    dashboard = {
        "dashboard_id": dashboard_id,
        "name": dashboard_config.get("name"),
        "description": dashboard_config.get("description"),
        "widgets": configured_widgets,
        "filters": dashboard_config.get("filters", {}),
        "refresh_schedule": refresh_schedule,
        "owner": dashboard_config.get("owner"),
        "shared_with": dashboard_config.get("shared_with", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store dashboard
    agent.dashboards[dashboard_id] = dashboard
    agent.analytics_output_store.upsert(tenant_id, dashboard_id, dashboard.copy())

    return {
        "dashboard_id": dashboard_id,
        "name": dashboard["name"],
        "widgets": len(configured_widgets),
        "refresh_schedule": refresh_schedule,
        "url": f"/dashboards/{dashboard_id}",
    }
