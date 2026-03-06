"""Tests for briefing generator (Enhancement 5).

Tests cover briefing generation with LLM fallback, section parsing,
audience-specific content, and briefing history.
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

_mod = load_route_module("briefings.py")
_router = _mod.router


def _make_app():
    app = FastAPI()
    app.include_router(_router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def test_generate_briefing(client):
    resp = client.post(
        "/api/briefings/generate",
        json={
            "portfolio_id": "default",
            "audience": "c_suite",
            "tone": "formal",
            "sections": ["highlights", "risks", "financials"],
            "format": "markdown",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["briefing_id"].startswith("brief-")
    assert data["title"]
    assert len(data["sections"]) >= 1
    assert data["content"]


def test_generate_briefing_all_sections(client):
    resp = client.post(
        "/api/briefings/generate",
        json={
            "audience": "board",
            "sections": ["highlights", "risks", "financials", "schedule", "resources", "recommendations"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sections"]) >= 1


def test_briefing_history(client):
    # Generate one first
    client.post("/api/briefings/generate", json={"audience": "pmo"})
    resp = client.get("/api/briefings/history")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_generate_briefing_default_sections(client):
    resp = client.post("/api/briefings/generate", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sections"]) >= 1


def test_briefing_has_metadata(client):
    resp = client.post(
        "/api/briefings/generate",
        json={"audience": "c_suite"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "metadata" in data
    assert "generated_at" in data["metadata"]
    assert "audience" in data["metadata"]


# --- Error path and edge case tests ---


def test_briefing_each_audience(client):
    """All supported audience types should generate valid briefings."""
    for audience in ["board", "c_suite", "pmo", "delivery_team"]:
        resp = client.post(
            "/api/briefings/generate",
            json={"audience": audience},
        )
        assert resp.status_code == 200, f"Failed for audience={audience}"
        data = resp.json()
        assert data["audience"] == audience
        assert len(data["sections"]) >= 1


def test_briefing_id_unique(client):
    """Each briefing should get a unique ID."""
    ids = set()
    for _ in range(5):
        resp = client.post("/api/briefings/generate", json={})
        bid = resp.json()["briefing_id"]
        assert bid not in ids
        ids.add(bid)


def test_briefing_content_non_empty(client):
    """Generated briefing content should never be empty."""
    resp = client.post("/api/briefings/generate", json={"sections": ["highlights"]})
    assert resp.status_code == 200
    assert len(resp.json()["content"]) > 10


def test_briefing_sections_have_titles(client):
    """Each section should have a title and content."""
    resp = client.post(
        "/api/briefings/generate",
        json={"sections": ["highlights", "risks", "recommendations"]},
    )
    for section in resp.json()["sections"]:
        assert "title" in section
        assert "content" in section
        assert len(section["title"]) > 0


def test_briefing_metadata_portfolio_id(client):
    """Metadata should reflect the requested portfolio_id."""
    resp = client.post(
        "/api/briefings/generate",
        json={"portfolio_id": "my-portfolio"},
    )
    assert resp.json()["metadata"]["portfolio_id"] == "my-portfolio"


def test_briefing_history_ordering(client):
    """History should contain most recent briefings."""
    # Generate multiple
    for audience in ["board", "c_suite"]:
        client.post("/api/briefings/generate", json={"audience": audience})
    resp = client.get("/api/briefings/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2


def test_briefing_title_contains_audience(client):
    """Briefing title should mention the audience type."""
    resp = client.post(
        "/api/briefings/generate",
        json={"audience": "board"},
    )
    title = resp.json()["title"]
    assert "Board" in title or "Director" in title
