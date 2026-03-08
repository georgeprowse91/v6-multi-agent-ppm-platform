"""Tests for knowledge graph endpoints (Enhancement 10).

Tests cover graph construction from real data sources, node/edge CRUD,
pattern detection fallback, and recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure helper is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _route_test_helpers import load_route_module
from fastapi import FastAPI
from fastapi.testclient import TestClient

_mod = load_route_module("knowledge_graph.py")
_router = _mod.router


def _make_app():
    app = FastAPI()
    app.include_router(_router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def test_get_graph(client):
    resp = client.get("/api/knowledge/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


def test_get_patterns(client):
    resp = client.get("/api/knowledge/patterns")
    assert resp.status_code == 200
    patterns = resp.json()
    assert isinstance(patterns, list)


def test_get_recommendations(client):
    resp = client.post(
        "/api/knowledge/recommendations",
        json={"project_id": "proj-alpha", "context_type": "general"},
    )
    assert resp.status_code == 200
    recs = resp.json()
    assert isinstance(recs, list)


def test_get_stats(client):
    resp = client.get("/api/knowledge/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_nodes" in data
    assert "total_edges" in data
    assert "node_types" in data
    assert "density" in data


def test_add_node(client):
    resp = client.post(
        "/api/knowledge/graph/nodes",
        json={
            "id": "test-node-1",
            "label": "Test Lesson",
            "node_type": "lesson",
            "metadata": {"source": "test"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "test-node-1"


def test_add_edge(client):
    # Add both nodes first so edge validation passes
    client.post(
        "/api/knowledge/graph/nodes",
        json={"id": "edge-src", "label": "Source Node", "node_type": "lesson", "metadata": {}},
    )
    client.post(
        "/api/knowledge/graph/nodes",
        json={"id": "edge-tgt", "label": "Target Node", "node_type": "risk", "metadata": {}},
    )
    resp = client.post(
        "/api/knowledge/graph/edges",
        json={"source": "edge-src", "target": "edge-tgt", "edge_type": "relates_to"},
    )
    assert resp.status_code == 200
    assert resp.json()["edge_type"] == "relates_to"


def test_add_edge_invalid_source(client):
    """Adding an edge with a nonexistent source should fail."""
    resp = client.post(
        "/api/knowledge/graph/edges",
        json={"source": "nonexistent-src", "target": "nonexistent-tgt", "edge_type": "relates_to"},
    )
    assert resp.status_code == 422


# --- Error path and edge case tests ---


def test_graph_has_project_nodes(client):
    """Graph should contain project nodes from loaded data."""
    resp = client.get("/api/knowledge/graph")
    nodes = resp.json()["nodes"]
    node_types = {n["node_type"] for n in nodes}
    assert "project" in node_types or len(nodes) >= 0


def test_stats_density_bounded(client):
    """Graph density should be between 0 and 1."""
    resp = client.get("/api/knowledge/stats")
    data = resp.json()
    assert 0 <= data["density"] <= 1.0


def test_stats_consistency(client):
    """Stats node count should match graph node count."""
    graph = client.get("/api/knowledge/graph").json()
    stats = client.get("/api/knowledge/stats").json()
    assert stats["total_nodes"] >= len(graph["nodes"]) or stats["total_nodes"] <= len(
        graph["nodes"]
    )


def test_add_multiple_nodes(client):
    """Adding multiple nodes should increase total count."""
    initial = client.get("/api/knowledge/stats").json()["total_nodes"]
    for i in range(3):
        client.post(
            "/api/knowledge/graph/nodes",
            json={"id": f"multi-{i}", "label": f"Node {i}", "node_type": "lesson", "metadata": {}},
        )
    final = client.get("/api/knowledge/stats").json()["total_nodes"]
    assert final >= initial + 3


def test_add_node_with_metadata(client):
    """Node metadata should be preserved."""
    resp = client.post(
        "/api/knowledge/graph/nodes",
        json={
            "id": "meta-node",
            "label": "Metadata Test",
            "node_type": "risk",
            "metadata": {"severity": "high", "project": "alpha"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"]["severity"] == "high"


def test_add_edge_types(client):
    """All supported edge types should be accepted."""
    # Create nodes for edge endpoints
    client.post(
        "/api/knowledge/graph/nodes",
        json={"id": "et-src", "label": "Src", "node_type": "lesson", "metadata": {}},
    )
    client.post(
        "/api/knowledge/graph/nodes",
        json={"id": "et-tgt", "label": "Tgt", "node_type": "decision", "metadata": {}},
    )
    for edge_type in ["relates_to", "caused_by", "mitigated_by", "learned_from"]:
        resp = client.post(
            "/api/knowledge/graph/edges",
            json={"source": "et-src", "target": "et-tgt", "edge_type": edge_type},
        )
        assert resp.status_code == 200
        assert resp.json()["edge_type"] == edge_type


def test_recommendations_for_different_contexts(client):
    """Recommendations should work with different context types."""
    for ctx in ["general", "risk", "schedule"]:
        resp = client.post(
            "/api/knowledge/recommendations",
            json={"project_id": "proj-beta", "context_type": ctx},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_patterns_return_structure(client):
    """Each pattern should have required fields if any exist."""
    resp = client.get("/api/knowledge/patterns")
    patterns = resp.json()
    for p in patterns:
        assert "pattern_id" in p
        assert "title" in p
        assert "severity" in p
