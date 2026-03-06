"""Tests for project setup wizard (Enhancement 7).

Tests cover methodology recommendation, template loading/filtering,
workspace configuration, and persistence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure helper is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _route_test_helpers import load_route_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

_mod = load_route_module("project_setup.py")
_router = _mod.router


def _make_app():
    app = FastAPI()
    app.include_router(_router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def test_recommend_methodology(client):
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={
            "industry": "technology",
            "team_size": 10,
            "duration_months": 6,
            "risk_level": "medium",
        },
    )
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) == 3
    methodologies = {r["methodology"] for r in recs}
    assert methodologies == {"predictive", "adaptive", "hybrid"}
    assert all(0 < r["match_score"] < 1 for r in recs)


def test_recommend_methodology_high_risk(client):
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={
            "industry": "pharma",
            "team_size": 50,
            "duration_months": 24,
            "risk_level": "high",
            "regulatory": ["GxP", "FDA"],
        },
    )
    assert resp.status_code == 200
    recs = resp.json()
    # Predictive should score highest for high-risk regulated pharma
    assert recs[0]["methodology"] == "predictive"


def test_list_templates_all(client):
    resp = client.get("/api/project-setup/templates")
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) >= 3


def test_list_templates_filtered(client):
    resp = client.get("/api/project-setup/templates?methodology=adaptive")
    assert resp.status_code == 200
    templates = resp.json()
    assert all(t["methodology"] == "adaptive" for t in templates)


def test_configure_workspace(client):
    resp = client.post(
        "/api/project-setup/configure-workspace?project_name=My%20New%20Project&template_id=tmpl-agile-tech"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_name"] == "My New Project"
    assert data["project_id"].startswith("proj-")
    assert data["methodology"] == "adaptive"
    assert data["created_at"]  # Should have a timestamp


def test_configure_workspace_persisted(client):
    resp = client.post(
        "/api/project-setup/configure-workspace?project_name=Persisted%20Project&template_id=tmpl-waterfall-construct"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["methodology"] == "predictive"
    assert "persisted" in data
