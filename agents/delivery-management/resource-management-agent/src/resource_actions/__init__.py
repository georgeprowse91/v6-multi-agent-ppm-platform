"""
Resource & Capacity Management Agent - Action Handlers

Each sub-module contains one or more action handler functions extracted from
the monolithic ResourceCapacityAgent class.
"""

from resource_actions.allocation import (
    handle_add_resource,
    handle_allocate_resource,
    handle_delete_resource,
    handle_update_resource,
)
from resource_actions.analytics import (
    handle_get_availability,
    handle_get_utilization,
    handle_identify_conflicts,
)
from resource_actions.demand_management import (
    handle_approve_request,
    handle_request_resource,
)
from resource_actions.helpers import (
    adjust_capacity_forecast,
    adjust_demand_forecast,
    apply_training_record,
    average_cost_rate,
    build_capacity_demand_history,
    build_risk_capacity_recommendations,
    calculate_day_availability,
    calculate_total_capacity,
    calculate_total_demand,
    check_allocation_overlap,
    create_baseline_scenario,
    determine_approver,
    find_matching_resources,
    forecast_capacity_for_scenario,
    generate_conflict_recommendations,
    get_performance_score,
    index_skills,
    load_risk_adjustments_config,
    merge_profiles,
    optimize_resource_allocations,
    pipeline_demand_adjustments,
    seasonality_multiplier,
    skill_development_multiplier,
    store_canonical_profile,
    store_model_in_azure_ml,
    train_forecasting_models,
    training_capacity_adjustments,
    update_resource_availability,
    validate_allocation,
)
from resource_actions.planning import (
    handle_forecast_capacity,
    handle_plan_capacity,
    handle_scenario_analysis,
)
from resource_actions.reporting import (
    handle_get_resource_pool,
    handle_match_skills,
    handle_search_resources,
)
from resource_actions.sync import (
    fetch_azure_ad_profiles,
    fetch_jira_tempo_allocations,
    fetch_planview_allocations,
    fetch_sap_profiles,
    fetch_workday_profiles,
    refresh_capacity_allocations,
    sync_hr_systems,
    sync_training_records,
)

__all__ = [
    # allocation
    "handle_add_resource",
    "handle_allocate_resource",
    "handle_delete_resource",
    "handle_update_resource",
    # demand_management
    "handle_approve_request",
    "handle_request_resource",
    # analytics
    "handle_get_availability",
    "handle_get_utilization",
    "handle_identify_conflicts",
    # planning
    "handle_forecast_capacity",
    "handle_plan_capacity",
    "handle_scenario_analysis",
    # reporting
    "handle_get_resource_pool",
    "handle_match_skills",
    "handle_search_resources",
    # sync
    "fetch_azure_ad_profiles",
    "fetch_jira_tempo_allocations",
    "fetch_planview_allocations",
    "fetch_sap_profiles",
    "fetch_workday_profiles",
    "refresh_capacity_allocations",
    "sync_hr_systems",
    "sync_training_records",
    # helpers
    "adjust_capacity_forecast",
    "adjust_demand_forecast",
    "apply_training_record",
    "average_cost_rate",
    "build_capacity_demand_history",
    "build_risk_capacity_recommendations",
    "calculate_day_availability",
    "calculate_total_capacity",
    "calculate_total_demand",
    "check_allocation_overlap",
    "create_baseline_scenario",
    "determine_approver",
    "find_matching_resources",
    "forecast_capacity_for_scenario",
    "generate_conflict_recommendations",
    "get_performance_score",
    "index_skills",
    "load_risk_adjustments_config",
    "merge_profiles",
    "optimize_resource_allocations",
    "pipeline_demand_adjustments",
    "seasonality_multiplier",
    "skill_development_multiplier",
    "store_canonical_profile",
    "store_model_in_azure_ml",
    "train_forecasting_models",
    "training_capacity_adjustments",
    "update_resource_availability",
    "validate_allocation",
]
