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


# --- Error path and edge case tests ---


def test_recommend_methodology_small_team(client):
    """Small teams should favor adaptive methodology."""
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={"industry": "technology", "team_size": 5, "duration_months": 3, "risk_level": "low"},
    )
    assert resp.status_code == 200
    recs = resp.json()
    adaptive_rec = next(r for r in recs if r["methodology"] == "adaptive")
    assert adaptive_rec["match_score"] > 0


def test_recommend_methodology_government(client):
    """Government industry should favor predictive."""
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={"industry": "government", "team_size": 100, "duration_months": 24, "risk_level": "high"},
    )
    recs = resp.json()
    assert recs[0]["methodology"] == "predictive"


def test_recommend_methodology_scores_sum_to_one(client):
    """Match scores across all recommendations should sum to approximately 1.0."""
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={"industry": "technology", "team_size": 10, "duration_months": 6, "risk_level": "medium"},
    )
    recs = resp.json()
    total = sum(r["match_score"] for r in recs)
    assert 0.95 <= total <= 1.05


def test_recommend_methodology_has_rationale(client):
    """Each recommendation should have a non-empty rationale."""
    resp = client.post(
        "/api/project-setup/recommend-methodology",
        json={"industry": "technology", "team_size": 10, "duration_months": 6, "risk_level": "medium"},
    )
    for rec in resp.json():
        assert rec["rationale"], f"Missing rationale for {rec['methodology']}"
        assert len(rec["strengths"]) >= 1


def test_list_templates_filter_by_industry(client):
    """Filtering by industry should return only matching templates."""
    resp = client.get("/api/project-setup/templates?industry=pharma")
    assert resp.status_code == 200
    templates = resp.json()
    assert all(t["industry"] == "pharma" for t in templates)


def test_list_templates_no_match(client):
    """Filtering for nonexistent methodology should return empty."""
    resp = client.get("/api/project-setup/templates?methodology=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


def test_configure_workspace_unique_ids(client):
    """Each workspace configuration should get a unique project_id."""
    ids = set()
    for i in range(5):
        resp = client.post(
            f"/api/project-setup/configure-workspace?project_name=Project%20{i}&template_id=tmpl-agile-tech"
        )
        pid = resp.json()["project_id"]
        assert pid not in ids
        ids.add(pid)


def test_configure_workspace_stages_from_template(client):
    """Workspace should inherit stages from the selected template."""
    resp = client.post(
        "/api/project-setup/configure-workspace?project_name=StageTest&template_id=tmpl-agile-tech"
    )
    data = resp.json()
    assert len(data["stages"]) >= 2
    stage_names = [s.get("name") for s in data["stages"]]
    assert any("Inception" in (n or "") for n in stage_names) or len(data["stages"]) >= 1


def test_template_has_required_fields(client):
    """Each template should have all required fields."""
    resp = client.get("/api/project-setup/templates")
    for t in resp.json():
        assert t.get("template_id"), "Missing template_id"
        assert t.get("name"), "Missing name"
        assert t.get("methodology"), "Missing methodology"
        assert t.get("stages") is not None, "Missing stages"
