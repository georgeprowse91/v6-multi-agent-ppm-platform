"""
Action handler modules for the Data Synchronization Agent.

Each module contains the handler functions for a related group of actions.
"""

from sync_actions.conflicts import (
    apply_conflict_resolution,
    detect_update_conflicts,
    handle_detect_conflicts,
    handle_resolve_conflict,
    record_conflicts,
)
from sync_actions.connectors import governed_connector_write
from sync_actions.duplicates import handle_detect_duplicates, handle_merge_duplicates
from sync_actions.master_records import (
    handle_create_master_record,
    handle_get_master_record,
    handle_update_master_record,
)
from sync_actions.monitoring import (
    evaluate_quality_thresholds,
    handle_get_dashboard,
    handle_get_metrics,
    handle_get_quality_report,
    handle_get_sync_status,
    record_quality_metrics,
    store_quality_report,
)
from sync_actions.retry import (
    enqueue_retry,
    handle_get_retry_queue,
    handle_process_retry_queue,
    handle_reprocess_retry,
)
from sync_actions.schema import handle_get_schema, handle_register_schema
from sync_actions.sync_data import handle_run_sync, handle_sync_data
from sync_actions.validation import (
    apply_validation_rule,
    get_validation_rules,
    handle_define_mapping,
    handle_validate_data,
)

__all__ = [
    # sync_data
    "handle_sync_data",
    "handle_run_sync",
    # master_records
    "handle_create_master_record",
    "handle_update_master_record",
    "handle_get_master_record",
    # conflicts
    "handle_detect_conflicts",
    "handle_resolve_conflict",
    "detect_update_conflicts",
    "record_conflicts",
    "apply_conflict_resolution",
    # duplicates
    "handle_detect_duplicates",
    "handle_merge_duplicates",
    # validation
    "handle_validate_data",
    "handle_define_mapping",
    "get_validation_rules",
    "apply_validation_rule",
    # schema
    "handle_get_schema",
    "handle_register_schema",
    # monitoring
    "handle_get_sync_status",
    "handle_get_metrics",
    "handle_get_quality_report",
    "handle_get_dashboard",
    "record_quality_metrics",
    "store_quality_report",
    "evaluate_quality_thresholds",
    # retry
    "enqueue_retry",
    "handle_process_retry_queue",
    "handle_reprocess_retry",
    "handle_get_retry_queue",
    # connectors
    "governed_connector_write",
]
