"""
Stateless utility functions for the Continuous Improvement & Process Mining Agent.

All helpers here are pure or near-pure functions with no dependency on agent state.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


async def generate_log_id() -> str:
    """Generate unique log ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"LOG-{timestamp}"


async def generate_improvement_id() -> str:
    """Generate unique improvement ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"IMP-{timestamp}"


# ---------------------------------------------------------------------------
# Timestamp handling
# ---------------------------------------------------------------------------


def safe_parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-format timestamp, returning ``None`` on failure."""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


async def calculate_time_range(events: list[dict[str, Any]]) -> dict[str, str | None]:
    """Calculate time range of events."""
    if not events:
        return {"start": None, "end": None}

    timestamps = []
    for event in events:
        timestamp = event.get("timestamp")
        if not timestamp:
            continue
        parsed = safe_parse_timestamp(timestamp)
        if parsed:
            timestamps.append(parsed)
    if not timestamps:
        return {"start": None, "end": None}

    return {"start": min(timestamps).isoformat(), "end": max(timestamps).isoformat()}


# ---------------------------------------------------------------------------
# Event normalization / mapping
# ---------------------------------------------------------------------------


async def normalize_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a raw event dict, returning ``None`` when invalid."""
    if not event.get("activity"):
        return None
    timestamp = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
    normalized = {
        **event,
        "timestamp": timestamp,
        "process_id": event.get("process_id") or "unknown",
    }
    if safe_parse_timestamp(normalized.get("timestamp")) is None:
        return None
    return normalized


async def validate_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate event log entries."""
    valid_events = []
    for event in events:
        normalized = await normalize_event(event)
        if normalized:
            valid_events.append(normalized)
    return valid_events


async def map_events_to_cases(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map events to process cases."""
    for event in events:
        if "case_id" not in event:
            event["case_id"] = event.get("request_id", "unknown")
    return events


# ---------------------------------------------------------------------------
# Trace building
# ---------------------------------------------------------------------------


async def build_traces(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build ordered activity traces keyed by case_id."""
    traces: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        case_id = event.get("case_id", "unknown")
        traces.setdefault(case_id, []).append(event)
    ordered_traces: dict[str, list[str]] = {}
    for case_id, case_events in traces.items():
        ordered = sorted(
            case_events,
            key=lambda e: safe_parse_timestamp(e.get("timestamp")) or datetime.min,
        )
        ordered_traces[case_id] = [e.get("activity") for e in ordered if e.get("activity")]
    return ordered_traces


def get_start_end_activities(
    traces: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """Return sorted unique start and end activities from traces."""
    start_activities: list[str] = []
    end_activities: list[str] = []
    for activities in traces.values():
        if activities:
            start_activities.append(activities[0])
            end_activities.append(activities[-1])
    return sorted(set(start_activities)), sorted(set(end_activities))


# ---------------------------------------------------------------------------
# Waiting-time / cycle-time helpers
# ---------------------------------------------------------------------------


async def calculate_average_waiting_time(events: list[dict[str, Any]]) -> float:
    """Calculate average waiting time across all traces."""
    traces = await build_traces(events)
    wait_times: list[float] = []
    for case_id in traces:
        case_events = [e for e in events if e.get("case_id") == case_id]
        case_events = sorted(
            case_events,
            key=lambda e: safe_parse_timestamp(e.get("timestamp")) or datetime.min,
        )
        for idx in range(1, len(case_events)):
            prev_ts = safe_parse_timestamp(case_events[idx - 1].get("timestamp"))
            curr_ts = safe_parse_timestamp(case_events[idx].get("timestamp"))
            if prev_ts and curr_ts:
                wait_times.append((curr_ts - prev_ts).total_seconds() / 3600)
    if not wait_times:
        return 0.0
    return round(sum(wait_times) / len(wait_times), 2)


# ---------------------------------------------------------------------------
# Compliance scoring
# ---------------------------------------------------------------------------


async def calculate_compliance_rate(
    deviations: list[dict[str, Any]],
    total_expected_activities: int | None = None,
    total_cases: int | None = None,
) -> float:
    """
    Calculate a normalized process compliance score (0-100).

    Formula assumptions:
    - Each deviation contributes weighted penalty units based on category and severity.
      This allows critical misses (e.g., skipped activities) to degrade compliance more
      than low-severity additions (e.g., extra activities).
    - Penalties are normalized by process opportunity size
      (``total_expected_activities * total_cases``) so large process volumes are not
      over-penalized for small absolute deviation counts.
    - If process context is missing, fallback denominator uses deviation count to avoid
      divide-by-zero and to preserve meaningful scaling.
    - Final score is clamped to [0, 100] and rounded to 2 decimals.
    """
    if not deviations:
        return 100.0

    severity_weights: dict[str, float] = {
        "critical": 2.0,
        "high": 1.5,
        "medium": 1.0,
        "low": 0.5,
    }
    category_weights: dict[str, float] = {
        "skipped_activities": 1.4,
        "unexpected_transition": 1.2,
        "wrong_sequence": 1.1,
        "excessive_loops": 0.9,
        "extra_activities": 0.6,
    }
    default_severity_by_category: dict[str, str] = {
        "skipped_activities": "high",
        "unexpected_transition": "medium",
        "wrong_sequence": "medium",
        "excessive_loops": "medium",
        "extra_activities": "low",
    }

    weighted_penalty = 0.0
    for deviation in deviations:
        category = str(deviation.get("category") or "")
        severity = str(
            deviation.get("severity") or default_severity_by_category.get(category, "medium")
        )
        weighted_penalty += category_weights.get(category, 1.0) * severity_weights.get(
            severity, 1.0
        )

    process_opportunities = (total_expected_activities or 0) * (total_cases or 0)
    denominator = max(1, process_opportunities, len(deviations))
    penalty_ratio = min(1.0, weighted_penalty / denominator)
    compliance_rate = (1.0 - penalty_ratio) * 100
    return round(min(100.0, max(0.0, compliance_rate)), 2)


# ---------------------------------------------------------------------------
# Iteration helpers
# ---------------------------------------------------------------------------


def pairwise(sequence: Iterable[str]) -> Iterable[tuple[str, str]]:
    """Yield consecutive pairs from *sequence*."""
    items = list(sequence)
    for idx in range(len(items) - 1):
        yield items[idx], items[idx + 1]


# ---------------------------------------------------------------------------
# Dimension extraction (for KPI grouping)
# ---------------------------------------------------------------------------


def extract_dimension(event: dict[str, Any], key: str) -> str | None:
    """Extract a grouping dimension from an event."""
    if key == "process_id":
        return event.get("process_id")
    metadata = event.get("metadata", {})
    return metadata.get(key) if isinstance(metadata, dict) else event.get(key)


# ---------------------------------------------------------------------------
# Owner resolution
# ---------------------------------------------------------------------------


def resolve_improvement_owner(recommendation: Any, index: int, default_owner: str) -> str:
    """Determine the improvement owner based on keyword hints."""
    owner_hints = {
        "training": "l&d-lead",
        "scope": "pmo-lead",
        "budget": "finance-partner",
        "risk": "risk-manager",
    }
    lowered = str(recommendation).lower()
    for hint, owner in owner_hints.items():
        if hint in lowered:
            return owner
    return default_owner if index % 2 == 0 else "delivery-manager"


# ---------------------------------------------------------------------------
# Store-path resolution
# ---------------------------------------------------------------------------


def resolve_store_path(config: dict[str, Any] | None, key: str, fallback: str) -> Path:
    """Resolve a ``TenantStateStore`` file path from config or fallback."""
    if config and config.get(key):
        return Path(config.get(key))
    return Path(fallback)


# ---------------------------------------------------------------------------
# Event-log loading
# ---------------------------------------------------------------------------


async def load_all_event_logs(event_log_store: Any) -> list[dict[str, Any]]:
    """Load all event logs from the store file on disk."""
    if not event_log_store.path.exists():
        return []
    try:
        data = event_log_store.path.read_text()
        if not data:
            return []
        parsed: dict[str, Any] = json.loads(data)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        return []
    logs: list[dict[str, Any]] = []
    for tenant_records in parsed.values():
        if isinstance(tenant_records, dict):
            logs.extend(record for record in tenant_records.values() if isinstance(record, dict))
    return logs


async def get_process_events(
    process_id: str,
    event_logs: dict[str, Any],
    event_log_store: Any,
) -> list[dict[str, Any]]:
    """Get events for a specific process."""
    all_events: list[dict[str, Any]] = []
    if not event_logs:
        stored_logs = await load_all_event_logs(event_log_store)
        for log in stored_logs:
            all_events.extend(log.get("events", []))
    else:
        for log in event_logs.values():
            all_events.extend(log.get("events", []))

    return [e for e in all_events if e.get("process_id") == process_id]
