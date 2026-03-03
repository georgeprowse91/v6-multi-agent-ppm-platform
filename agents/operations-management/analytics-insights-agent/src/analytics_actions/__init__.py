"""Action handlers for the Analytics & Insights Agent."""

from analytics_actions.aggregate_data import handle_aggregate_data
from analytics_actions.compute_kpis import handle_compute_kpis_batch, update_kpis_from_definitions
from analytics_actions.create_dashboard import handle_create_dashboard
from analytics_actions.data_lineage import handle_update_data_lineage
from analytics_actions.generate_narrative import handle_generate_narrative
from analytics_actions.generate_report import handle_generate_report
from analytics_actions.infrastructure import (
    handle_get_powerbi_report,
    handle_ingest_realtime_event,
    handle_ingest_sources,
    handle_monitor_etl,
    handle_orchestrate_etl,
    handle_provision_analytics_stack,
    handle_train_kpi_model,
)
from analytics_actions.insights import handle_get_insights
from analytics_actions.periodic_report import handle_generate_periodic_report
from analytics_actions.query_data import handle_get_dashboard, handle_natural_language_query, handle_query_data
from analytics_actions.run_prediction import handle_run_prediction
from analytics_actions.scenario_analysis import handle_scenario_analysis
from analytics_actions.track_kpi import handle_track_kpi

__all__ = [
    "handle_aggregate_data",
    "handle_compute_kpis_batch",
    "handle_create_dashboard",
    "handle_generate_narrative",
    "handle_generate_periodic_report",
    "handle_generate_report",
    "handle_get_dashboard",
    "handle_get_insights",
    "handle_get_powerbi_report",
    "handle_ingest_realtime_event",
    "handle_ingest_sources",
    "handle_monitor_etl",
    "handle_natural_language_query",
    "handle_orchestrate_etl",
    "handle_provision_analytics_stack",
    "handle_run_prediction",
    "handle_scenario_analysis",
    "handle_track_kpi",
    "handle_train_kpi_model",
    "handle_update_data_lineage",
    "update_kpis_from_definitions",
]
