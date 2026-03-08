"""Tests for briefing document renderer (PDF / PPTX export)."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

# Ensure document-service src is on path
_doc_service_src = Path(__file__).resolve().parents[2] / "services" / "document-service" / "src"
sys.path.insert(0, str(_doc_service_src))

from briefing_renderer import (
    _markdown_to_html,
    _strip_markdown,
    render_briefing,
    render_briefing_pdf,
    render_briefing_pptx,
)

# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def test_markdown_to_html_headings():
    md = "# Title\n\n## Subtitle"
    html = _markdown_to_html(md)
    assert "<h1>Title</h1>" in html
    assert "<h2>Subtitle</h2>" in html


def test_markdown_to_html_lists():
    md = "- Item 1\n- Item 2\n\n1. First\n2. Second"
    html = _markdown_to_html(md)
    assert "<li>Item 1</li>" in html
    assert "<li>Item 2</li>" in html
    assert "<li>First</li>" in html
    assert "<li>Second</li>" in html


def test_markdown_to_html_inline():
    md = "**bold** and *italic* text"
    html = _markdown_to_html(md)
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_strip_markdown():
    text = "## Heading\n**bold** and *italic*"
    result = _strip_markdown(text)
    assert "##" not in result
    assert "**" not in result
    assert "bold" in result
    assert "italic" in result


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------


def test_render_briefing_pdf_produces_bytes():
    result = render_briefing_pdf(
        title="Test Briefing",
        content="# Test\n\n## Overview\n- Point 1\n- Point 2",
        audience="c_suite",
        generated_at="2026-03-07T00:00:00Z",
    )
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Should start with PDF header
    assert result[:5] == b"%PDF-"


def test_render_briefing_pdf_all_audiences():
    for audience in ["board", "c_suite", "pmo", "delivery_team"]:
        result = render_briefing_pdf(
            title=f"{audience} Briefing",
            content="## Section\nContent",
            audience=audience,
            generated_at="2026-03-07T00:00:00Z",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# PPTX rendering
# ---------------------------------------------------------------------------


def test_render_briefing_pptx_produces_bytes():
    result = render_briefing_pptx(
        title="Test Briefing",
        sections=[
            {"title": "Highlights", "content": "## Highlights\n- Item 1"},
            {"title": "Risks", "content": "## Risks\n- Risk 1"},
        ],
        audience="board",
        generated_at="2026-03-07T00:00:00Z",
    )
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_render_briefing_pptx_empty_sections():
    result = render_briefing_pptx(
        title="Empty Briefing",
        sections=[],
        audience="pmo",
        generated_at="2026-03-07T00:00:00Z",
    )
    assert isinstance(result, bytes)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Top-level render_briefing
# ---------------------------------------------------------------------------


def test_render_briefing_pdf_format():
    result = render_briefing(
        title="Export Test",
        content="## Section\nContent here",
        sections=[{"title": "Section", "content": "Content here"}],
        audience="c_suite",
        generated_at="2026-03-07T00:00:00Z",
        export_format="pdf",
    )
    assert result["filename"].endswith(".pdf")
    assert result["content_type"] == "application/pdf"
    # content_base64 should be valid base64
    decoded = base64.b64decode(result["content_base64"])
    assert decoded[:5] == b"%PDF-"


def test_render_briefing_pptx_format():
    result = render_briefing(
        title="Export Test",
        content="## Section\nContent here",
        sections=[{"title": "Section", "content": "Content here"}],
        audience="board",
        generated_at="2026-03-07T00:00:00Z",
        export_format="pptx",
    )
    assert result["filename"].endswith(".pptx")
    assert "presentationml" in result["content_type"] or result["content_type"]
    assert len(result["content_base64"]) > 0


def test_render_briefing_invalid_format():
    with pytest.raises(ValueError, match="Unsupported export format"):
        render_briefing(
            title="Bad Format",
            content="content",
            sections=[],
            audience="c_suite",
            generated_at="2026-03-07T00:00:00Z",
            export_format="docx",
        )


def test_render_briefing_special_characters():
    """Renderer should handle special characters in title and content."""
    result = render_briefing(
        title="Briefing — Q1 (Draft) & Review",
        content="## Overview\n- Budget: $1,500,000\n- CPI: 0.98 < 1.0",
        sections=[{"title": "Overview", "content": "Budget: $1,500,000"}],
        audience="c_suite",
        generated_at="2026-03-07T00:00:00Z",
        export_format="pdf",
    )
    assert result["filename"]
    assert len(result["content_base64"]) > 0
