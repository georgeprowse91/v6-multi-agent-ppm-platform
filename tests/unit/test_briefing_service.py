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
