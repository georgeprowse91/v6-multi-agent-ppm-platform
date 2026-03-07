"""Tests for briefing generator (Enhancement 7).

Tests cover briefing generation with LLM fallback, cross-agent data aggregation,
section parsing, audience-specific content, briefing history, PDF/PPTX export,
scheduled delivery, and notification integration.
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


# ---------------------------------------------------------------------------
# Basic briefing generation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Cross-agent data aggregation
# ---------------------------------------------------------------------------


def test_briefing_contains_cross_agent_sources(client):
    """Briefing metadata should list cross-agent data sources."""
    resp = client.post(
        "/api/briefings/generate",
        json={"audience": "c_suite"},
    )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert "cross_agent_sources" in metadata
    sources = metadata["cross_agent_sources"]
    assert "financial" in sources
    assert "risk" in sources
    assert "resource" in sources
    assert "analytics" in sources


def test_briefing_financials_section_has_metrics(client):
    """Financial section should contain budget/cost metrics from cross-agent data."""
    resp = client.post(
        "/api/briefings/generate",
        json={"sections": ["financials"]},
    )
    assert resp.status_code == 200
    content = resp.json()["content"]
    # Fallback content uses cross-agent data for financials
    assert "Financial" in content or "financial" in content


def test_briefing_risk_section_has_data(client):
    """Risk section should contain risk counts from cross-agent data."""
    resp = client.post(
        "/api/briefings/generate",
        json={"sections": ["risks"]},
    )
    assert resp.status_code == 200
    content = resp.json()["content"]
    assert "Risk" in content or "risk" in content


def test_briefing_resources_section_has_data(client):
    """Resource section should contain utilization data from cross-agent data."""
    resp = client.post(
        "/api/briefings/generate",
        json={"sections": ["resources"]},
    )
    assert resp.status_code == 200
    content = resp.json()["content"]
    assert "Resource" in content or "resource" in content


def test_briefing_recommendations_with_cross_agent_data(client):
    """Recommendations should be data-driven when cross-agent data is available."""
    resp = client.post(
        "/api/briefings/generate",
        json={"sections": ["recommendations"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sections"]) >= 1
    assert data["content"]


# ---------------------------------------------------------------------------
# Export (PDF / PPTX)
# ---------------------------------------------------------------------------


def test_export_briefing_pdf(client):
    """Should be able to export a briefing to PDF."""
    gen_resp = client.post(
        "/api/briefings/generate",
        json={"audience": "c_suite", "sections": ["highlights", "risks"]},
    )
    briefing_id = gen_resp.json()["briefing_id"]

    resp = client.post(
        "/api/briefings/export",
        json={"briefing_id": briefing_id, "export_format": "pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["export_format"] == "pdf"
    assert data["filename"].endswith(".pdf")
    assert len(data["content_base64"]) > 0
    assert data["content_type"] == "application/pdf"


def test_export_briefing_pptx(client):
    """Should be able to export a briefing to PPTX."""
    gen_resp = client.post(
        "/api/briefings/generate",
        json={"audience": "board", "sections": ["highlights", "financials"]},
    )
    briefing_id = gen_resp.json()["briefing_id"]

    resp = client.post(
        "/api/briefings/export",
        json={"briefing_id": briefing_id, "export_format": "pptx"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["export_format"] == "pptx"
    assert data["filename"].endswith(".pptx")
    assert len(data["content_base64"]) > 0


def test_export_briefing_not_found(client):
    """Exporting a non-existent briefing should return 404."""
    resp = client.post(
        "/api/briefings/export",
        json={"briefing_id": "nonexistent", "export_format": "pdf"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------


def test_create_briefing_schedule(client):
    """Should create a recurring briefing schedule."""
    resp = client.post(
        "/api/briefings/schedule",
        json={
            "portfolio_id": "default",
            "audience": "c_suite",
            "tone": "formal",
            "sections": ["highlights", "risks"],
            "frequency": "weekly",
            "recipients": ["ceo@company.com", "cfo@company.com"],
            "channels": ["email"],
            "export_format": "pdf",
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["schedule_id"].startswith("sched-")
    assert data["frequency"] == "weekly"
    assert len(data["recipients"]) == 2
    assert data["enabled"] is True


def test_list_briefing_schedules(client):
    """Should list all created schedules."""
    client.post(
        "/api/briefings/schedule",
        json={
            "frequency": "monthly",
            "recipients": ["pmo@company.com"],
            "channels": ["teams"],
        },
    )
    resp = client.get("/api/briefings/schedules")
    assert resp.status_code == 200
    schedules = resp.json()
    assert len(schedules) >= 1


def test_delete_briefing_schedule(client):
    """Should delete an existing schedule."""
    create_resp = client.post(
        "/api/briefings/schedule",
        json={
            "frequency": "daily",
            "recipients": ["test@company.com"],
            "channels": ["slack"],
        },
    )
    schedule_id = create_resp.json()["schedule_id"]

    resp = client.delete(f"/api/briefings/schedules/{schedule_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


def test_delete_nonexistent_schedule(client):
    """Deleting a non-existent schedule should return 404."""
    resp = client.delete("/api/briefings/schedules/nonexistent")
    assert resp.status_code == 404


def test_schedule_frequency_validation(client):
    """Invalid frequency should be rejected."""
    resp = client.post(
        "/api/briefings/schedule",
        json={
            "frequency": "hourly",
            "recipients": ["test@company.com"],
            "channels": ["email"],
        },
    )
    assert resp.status_code == 422


def test_schedule_channel_validation(client):
    """Invalid channel should be rejected."""
    resp = client.post(
        "/api/briefings/schedule",
        json={
            "frequency": "weekly",
            "recipients": ["test@company.com"],
            "channels": ["sms"],
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------


def test_parse_sections():
    """Section parser should extract ## headings correctly."""
    content = "# Title\n\n## Section One\nContent 1\n\n## Section Two\nContent 2"
    sections = _mod._parse_sections(content)
    assert len(sections) == 2
    assert sections[0]["title"] == "Section One"
    assert sections[1]["title"] == "Section Two"


def test_strip_markdown():
    """Strip markdown should remove formatting."""
    text = "## Title\n**bold** and *italic*"
    stripped = _mod._strip_markdown(text)
    assert "##" not in stripped
    assert "**" not in stripped
    assert "*" not in stripped
    assert "bold" in stripped
    assert "italic" in stripped


def test_markdown_to_html():
    """Markdown to HTML converter should handle basic patterns."""
    md = "# Title\n\n- Item 1\n- Item 2\n\n**bold** text"
    html = _mod._markdown_to_html(md)
    assert "<h1>" in html
    assert "<li>" in html
    assert "<strong>" in html


def test_gather_cross_agent_data():
    """Cross-agent data aggregation should return all four domains."""
    import asyncio

    data = asyncio.get_event_loop().run_until_complete(
        _mod._gather_cross_agent_data("test-portfolio")
    )
    assert "financial" in data
    assert "risk" in data
    assert "resource" in data
    assert "analytics" in data


def test_generate_local_export_pdf():
    """Local PDF export should produce valid output."""
    briefing_data = {
        "title": "Test Briefing",
        "content": "# Test\n\n## Highlights\n- Item 1",
        "sections": [{"title": "Highlights", "content": "- Item 1"}],
        "generated_at": "2026-03-07T00:00:00Z",
    }
    result = _mod._generate_local_export(briefing_data, "pdf")
    assert result["filename"].endswith(".pdf")
    assert len(result["content_base64"]) > 0
    assert result["content_type"] == "application/pdf"


def test_generate_local_export_pptx():
    """Local PPTX export should produce valid output."""
    briefing_data = {
        "title": "Test Briefing",
        "content": "# Test",
        "sections": [{"title": "Overview", "content": "Content here"}],
        "generated_at": "2026-03-07T00:00:00Z",
    }
    result = _mod._generate_local_export(briefing_data, "pptx")
    assert result["filename"].endswith(".pptx")
    assert len(result["content_base64"]) > 0
