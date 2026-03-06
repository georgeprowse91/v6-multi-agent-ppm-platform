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
    resp = client.post(
        "/api/knowledge/graph/edges",
        json={
            "source": "test-node-1",
            "target": "test-node-2",
            "edge_type": "relates_to",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["edge_type"] == "relates_to"
