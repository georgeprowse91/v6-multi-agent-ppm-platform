"""Intent Router Agent - Pure utility functions."""

from __future__ import annotations

from typing import Any


def build_entity_patterns() -> list[dict[str, Any]]:
    """Return spaCy EntityRuler patterns for project domain entities."""
    return [
        {"label": "SCHEDULE_FOCUS", "pattern": "critical path"},
        {"label": "SCHEDULE_FOCUS", "pattern": "milestone"},
        {"label": "SCHEDULE_FOCUS", "pattern": "milestones"},
        {"label": "CURRENCY", "pattern": [{"LOWER": {"IN": ["usd", "eur", "gbp", "jpy"]}}]},
        {
            "label": "PROJECT_ID",
            "pattern": [{"LOWER": "project"}, {"IS_ASCII": True, "OP": "+"}],
        },
        {
            "label": "PORTFOLIO_ID",
            "pattern": [{"LOWER": "portfolio"}, {"IS_ASCII": True, "OP": "+"}],
        },
    ]
