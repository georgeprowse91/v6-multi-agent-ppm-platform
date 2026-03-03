"""
Action handlers for the Change & Configuration Management Agent.

Each module contains closely related action handlers that are dispatched
from the main ChangeConfigurationAgent.process() method.
"""

from change_actions.approve_and_review import approve_change, review_change
from change_actions.classify_and_assess import assess_impact, classify_change, predict_impact
from change_actions.cmdb_actions import (
    create_baseline,
    query_impacted_cis,
    register_ci,
    track_change_implementation,
)
from change_actions.implement_change import (
    implement_change,
    rollback_change,
    run_automated_tests,
    run_staging_validation,
    update_change_request,
)
from change_actions.reporting import (
    audit_changes,
    generate_change_report,
    get_change_dashboard,
    get_change_metrics,
    matches_filters,
    visualize_dependencies,
)
from change_actions.submit_change import (
    analyze_iac_changes,
    identify_impacted_cis,
    notify_stakeholders,
    publish_event,
    record_change_audit,
    submit_change_request,
)
from change_actions.webhook_and_monitoring import (
    handle_cicd_webhook,
    monitor_change,
    subscribe_cicd_webhooks,
)

__all__ = [
    "approve_change",
    "assess_impact",
    "audit_changes",
    "classify_change",
    "create_baseline",
    "generate_change_report",
    "get_change_dashboard",
    "get_change_metrics",
    "handle_cicd_webhook",
    "identify_impacted_cis",
    "implement_change",
    "matches_filters",
    "monitor_change",
    "notify_stakeholders",
    "predict_impact",
    "publish_event",
    "query_impacted_cis",
    "record_change_audit",
    "register_ci",
    "review_change",
    "rollback_change",
    "run_automated_tests",
    "run_staging_validation",
    "submit_change_request",
    "subscribe_cicd_webhooks",
    "track_change_implementation",
    "update_change_request",
    "visualize_dependencies",
    "analyze_iac_changes",
]
