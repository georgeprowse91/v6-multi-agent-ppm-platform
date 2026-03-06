"""Executive briefing generator API routes.

Generates real AI-powered briefings by fetching live portfolio data
and using LLM to produce audience-tailored narratives.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from routes._deps import _load_projects, logger
from routes._llm_helpers import llm_complete

router = APIRouter(tags=["briefings"])

_BRIEFING_STORE: list[dict[str, Any]] = []
_BRIEFING_STORE_MAX = 100

_AUDIENCE_SYSTEM_PROMPTS = {
    "board": (
        "You are a briefing writer for a Board of Directors audience. "
        "Focus on strategic alignment, portfolio ROI, high-level risk posture, "
        "and investment decisions. Use formal tone, avoid operational detail."
    ),
    "c_suite": (
        "You are a briefing writer for C-Suite executives. "
        "Emphasize financial metrics, budget variance, business value delivery, "
        "and strategic risks. Be concise and data-driven."
    ),
    "pmo": (
        "You are a briefing writer for PMO leadership. "
        "Provide operational detail: schedule adherence, resource utilization, "
        "governance compliance, process health, and delivery velocity."
    ),
    "delivery_team": (
        "You are a briefing writer for delivery teams. "
        "Tactical focus: sprint progress, blockers, upcoming milestones, "
        "team capacity, and technical risks. Be specific and actionable."
    ),
}


_VALID_AUDIENCES = {"board", "c_suite", "pmo", "delivery_team"}
_VALID_TONES = {"formal", "informal", "technical", "executive"}
_VALID_FORMATS = {"markdown", "html", "text"}


class BriefingRequest(BaseModel):
    portfolio_id: str = "default"
    audience: str = "c_suite"
    tone: str = "formal"
    sections: list[str] = Field(
        default_factory=lambda: [
            "highlights", "risks", "financials", "schedule", "resources", "recommendations",
        ],
        min_length=1,
    )
    format: str = "markdown"

    @field_validator("audience")
    @classmethod
    def _validate_audience(cls, v: str) -> str:
        if v not in _VALID_AUDIENCES:
            raise ValueError(
                f"audience must be one of {sorted(_VALID_AUDIENCES)}, got '{v}'"
            )
        return v

    @field_validator("tone")
    @classmethod
    def _validate_tone(cls, v: str) -> str:
        if v not in _VALID_TONES:
            raise ValueError(
                f"tone must be one of {sorted(_VALID_TONES)}, got '{v}'"
            )
        return v

    @field_validator("format")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        if v not in _VALID_FORMATS:
            raise ValueError(
                f"format must be one of {sorted(_VALID_FORMATS)}, got '{v}'"
            )
        return v


class BriefingResponse(BaseModel):
    briefing_id: str
    title: str
    generated_at: str
    audience: str
    content: str
    sections: list[dict[str, str]]
    metadata: dict[str, Any] = Field(default_factory=dict)


def _gather_portfolio_data(portfolio_id: str) -> dict[str, Any]:
    """Gather real portfolio data from available sources."""
    projects = _load_projects()
    project_summaries = []
    for p in projects[:20]:
        project_summaries.append({
            "id": getattr(p, "id", ""),
            "name": getattr(p, "name", ""),
            "status": getattr(p, "status", "active"),
            "health": getattr(p, "health", "green"),
            "methodology": getattr(p, "methodology", ""),
        })

    return {
        "portfolio_id": portfolio_id,
        "project_count": len(projects),
        "projects": project_summaries,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.post("/api/briefings/generate")
async def generate_briefing(request: BriefingRequest) -> BriefingResponse:
    """Generate an AI-powered executive briefing using real portfolio data."""
    logger.info(
        "Briefing request: audience=%s, tone=%s, format=%s, portfolio=%s",
        request.audience, request.tone, request.format, request.portfolio_id,
    )
    briefing_id = f"brief-{uuid.uuid4().hex[:8]}"
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    audience_label = {
        "board": "Board of Directors",
        "c_suite": "C-Suite Executive",
        "pmo": "PMO Leadership",
        "delivery_team": "Delivery Team",
    }.get(request.audience, "Executive")

    portfolio_data = _gather_portfolio_data(request.portfolio_id)

    system_prompt = _AUDIENCE_SYSTEM_PROMPTS.get(
        request.audience,
        _AUDIENCE_SYSTEM_PROMPTS["c_suite"],
    )

    user_prompt = (
        f"Generate a portfolio briefing for the {audience_label} audience.\n"
        f"Tone: {request.tone}\n"
        f"Requested sections: {', '.join(request.sections)}\n"
        f"Format: {request.format}\n\n"
        f"Portfolio data:\n{json.dumps(portfolio_data, indent=2)}\n\n"
        "For each requested section, generate a markdown section with ## heading. "
        "Include specific metrics, trend indicators, and actionable insights. "
        "If project data is limited, provide realistic analysis based on the available data "
        "and clearly note assumptions."
    )

    try:
        llm_content = await llm_complete(
            system_prompt,
            user_prompt,
            tenant_id=request.portfolio_id,
            temperature=0.4,
        )
    except Exception:
        logger.exception("LLM call failed for briefing %s", briefing_id)
        llm_content = None

    if llm_content:
        content = f"# Portfolio Briefing — {audience_label}\n\n*Generated: {generated_at}*\n\n{llm_content}"
    else:
        content = _generate_fallback_briefing(
            audience_label, generated_at, request.sections, portfolio_data,
        )

    sections = _parse_sections(content)

    # If LLM content had no parseable sections, regenerate with structured fallback
    if not sections:
        content = _generate_fallback_briefing(
            audience_label, generated_at, request.sections, portfolio_data,
        )
        sections = _parse_sections(content)

    briefing = BriefingResponse(
        briefing_id=briefing_id,
        title=f"Portfolio Briefing — {audience_label}",
        generated_at=generated_at,
        audience=request.audience,
        content=content,
        sections=sections,
        metadata={
            "generated_at": generated_at,
            "audience": request.audience,
            "portfolio_id": request.portfolio_id,
            "tone": request.tone,
            "format": request.format,
            "project_count": portfolio_data["project_count"],
            "llm_generated": bool(llm_content and sections),
        },
    )

    _BRIEFING_STORE.append(briefing.model_dump())
    if len(_BRIEFING_STORE) > _BRIEFING_STORE_MAX:
        del _BRIEFING_STORE[: len(_BRIEFING_STORE) - _BRIEFING_STORE_MAX]
    return briefing


@router.get("/api/briefings/history")
async def briefing_history() -> list[dict[str, Any]]:
    return _BRIEFING_STORE[-20:]


def _parse_sections(content: str) -> list[dict[str, str]]:
    """Parse ## headings from generated markdown into section objects."""
    sections: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_title:
                sections.append({"title": current_title, "content": "\n".join(current_lines)})
            current_title = line[3:].strip()
            current_lines = [line]
        elif current_title:
            current_lines.append(line)

    if current_title:
        sections.append({"title": current_title, "content": "\n".join(current_lines)})

    return sections


def _generate_fallback_briefing(
    audience_label: str,
    generated_at: str,
    sections: list[str],
    portfolio_data: dict[str, Any],
) -> str:
    """Fallback briefing when LLM is unavailable — uses real portfolio data."""
    parts = [
        f"# Portfolio Briefing — {audience_label}\n",
        f"*Generated: {generated_at} | Portfolio: {portfolio_data['portfolio_id']}*\n",
        f"*Projects in portfolio: {portfolio_data['project_count']}*\n",
    ]

    project_names = [p.get("name", "Unknown") for p in portfolio_data.get("projects", [])]
    health_counts: dict[str, int] = {}
    for p in portfolio_data.get("projects", []):
        h = p.get("health", "unknown")
        health_counts[h] = health_counts.get(h, 0) + 1

    if "highlights" in sections:
        parts.append("## Key Highlights\n")
        parts.append(f"- Portfolio contains **{portfolio_data['project_count']}** active projects")
        if health_counts:
            health_str = ", ".join(f"{v} {k}" for k, v in sorted(health_counts.items()))
            parts.append(f"- Health distribution: {health_str}")
        if project_names:
            parts.append(f"- Active projects: {', '.join(project_names[:5])}")
        parts.append("")

    if "risks" in sections:
        parts.append("## Risk Summary\n")
        parts.append("- Enable an LLM provider (set LLM_PROVIDER) for AI-generated risk analysis\n")

    if "financials" in sections:
        parts.append("## Financial Overview\n")
        parts.append("- Connect data service for real budget and cost data\n")

    if "schedule" in sections:
        parts.append("## Schedule Status\n")
        parts.append(f"- Tracking {portfolio_data['project_count']} projects\n")

    if "resources" in sections:
        parts.append("## Resource Utilization\n")
        parts.append("- Resource data available with data service integration\n")

    if "recommendations" in sections:
        parts.append("## AI Recommendations\n")
        parts.append("1. **Enable LLM provider** — Set LLM_PROVIDER for AI recommendations")
        parts.append("2. **Connect data sources** — Wire portfolio data for real-time insights\n")

    return "\n".join(parts)
