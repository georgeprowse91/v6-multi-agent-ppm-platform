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
    ids1 = {s.connector_id: s.status for s in statuses1}
    ids2 = {s.connector_id: s.status for s in statuses2}
    assert ids1 == ids2


# --- Error path and edge case tests ---


def test_resolve_nonexistent_conflict():
    """Resolving a conflict that doesn't exist should return a resolved record."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    result = agg.resolve_conflict("tenant-1", "cf-nonexistent", "accept_source")
    assert result.status == "resolved"
    assert result.conflict_id == "cf-nonexistent"


def test_multiple_resolve_same_conflict():
    """Resolving the same conflict twice should be idempotent."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    agg.get_conflict_queue("tenant-1")
    agg.resolve_conflict("tenant-1", "cf-001", "accept_source")
    result = agg.resolve_conflict("tenant-1", "cf-001", "manual", manual_value="$999")
    assert result.status == "resolved"


def test_all_statuses_have_required_fields():
    """All health records should have non-empty required fields."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    statuses = agg.get_all_status("tenant-1")
    for s in statuses:
        assert s.connector_id, "connector_id must be non-empty"
        assert s.name, "name must be non-empty"
        assert s.last_sync, "last_sync must be non-empty"
        assert s.error_rate_1h >= 0, "error_rate must be non-negative"


def test_error_rate_bounded():
    """Error rates should be between 0 and 1."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    statuses = agg.get_all_status("tenant-1")
    for s in statuses:
        assert 0 <= s.error_rate_1h <= 1.0, f"{s.connector_id} has error_rate {s.error_rate_1h}"


def test_data_freshness_record_counts_positive():
    """All data freshness record counts should be positive."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    records = agg.get_data_freshness("tenant-1")
    for r in records:
        assert r.record_count > 0


def test_connector_ids_no_duplicates():
    """Health status should not contain duplicate connector IDs."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    statuses = agg.get_all_status("tenant-1")
    ids = [s.connector_id for s in statuses]
    assert len(ids) == len(set(ids)), "Duplicate connector IDs found"


def test_circuit_state_matches_health():
    """Circuit state should correlate with health status."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    statuses = agg.get_all_status("tenant-1")
    for s in statuses:
        if s.status == "healthy":
            assert s.circuit_state == "closed"
        elif s.status == "degraded":
            assert s.circuit_state == "half_open"
        elif s.status == "down":
            assert s.circuit_state == "open"


def test_different_tenants_same_results():
    """Different tenants should get same static registry-based results."""
    _reset_state()
    agg = ConnectorHealthAggregator()
    s1 = {s.connector_id: s.status for s in agg.get_all_status("tenant-1")}
    _reset_state()
    s2 = {s.connector_id: s.status for s in agg.get_all_status("tenant-2")}
    assert s1 == s2
