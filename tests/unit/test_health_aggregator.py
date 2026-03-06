"""Tests for connector health aggregator (Enhancement 4).

Tests cover registry loading, manifest-based health derivation,
conflict management, and fallback behavior.
"""

from __future__ import annotations

import health_aggregator as ha_mod
from health_aggregator import ConnectorHealthAggregator


def _reset_state():
    """Reset module-level caches between tests."""
    ha_mod._registry_cache = None
    ha_mod._registry_cache_time = 0.0
    ha_mod._manifest_cache.clear()
    ha_mod._conflict_store.clear()
    ha_mod._conflict_initialized = False


def test_get_all_status():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    statuses = aggregator.get_all_status("tenant-1")
    assert len(statuses) > 0
    for s in statuses:
        assert s.connector_id
        assert s.status in ("healthy", "degraded", "down")
        assert s.circuit_state in ("closed", "half_open", "open")


def test_get_all_status_no_mcp_duplicates():
    """Verify MCP variants are filtered out."""
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    statuses = aggregator.get_all_status("tenant-1")
    ids = [s.connector_id for s in statuses]
    assert not any(cid.endswith("_mcp") for cid in ids)


def test_get_data_freshness():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    freshness = aggregator.get_data_freshness("tenant-1")
    assert len(freshness) > 0
    for f in freshness:
        assert f.freshness_status in ("fresh", "stale", "critical")
        assert f.record_count >= 0


def test_get_conflict_queue():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    conflicts = aggregator.get_conflict_queue("tenant-1")
    assert len(conflicts) > 0
    for c in conflicts:
        assert c.conflict_id
        assert c.status == "unresolved"


def test_resolve_conflict():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    # Ensure conflicts are loaded
    aggregator.get_conflict_queue("tenant-1")
    result = aggregator.resolve_conflict("tenant-1", "cf-001", "accept_source")
    assert result.status == "resolved"
    assert result.resolution == "accept_source"


def test_resolve_conflict_manual():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    aggregator.get_conflict_queue("tenant-1")
    result = aggregator.resolve_conflict("tenant-1", "cf-002", "manual", manual_value="$1,225,000")
    assert result.status == "resolved"
    assert result.resolution == "manual"
    assert result.canonical_value == "$1,225,000"


def test_resolved_conflicts_not_in_queue():
    _reset_state()
    aggregator = ConnectorHealthAggregator()
    initial = aggregator.get_conflict_queue("tenant-1")
    initial_count = len(initial)
    aggregator.resolve_conflict("tenant-1", "cf-001", "accept_source")
    remaining = aggregator.get_conflict_queue("tenant-1")
    assert len(remaining) == initial_count - 1


def test_status_deterministic():
    """Verify health derivation is deterministic (same input → same output)."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    statuses1 = agg.get_all_status("tenant-1")
    _reset_state()
    statuses2 = agg.get_all_status("tenant-1")
    # Status values should be the same (though last_sync timestamps will differ)
    ids1 = {s.connector_id: s.status for s in statuses1}
    ids2 = {s.connector_id: s.status for s in statuses2}
    assert ids1 == ids2
