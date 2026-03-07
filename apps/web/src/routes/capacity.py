"""Capacity planning API routes.

Provides portfolio-level demand aggregation and skill gap analysis
by delegating to the Resource Management agent.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["capacity"])


@router.get("/api/capacity/portfolio-demand")
async def get_portfolio_demand(
    portfolio_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return portfolio-level resource demand aggregation with skill gaps.

    In production this delegates to the Resource Management agent's
    ``aggregate_portfolio_demand`` action.  For now it returns a
    structured response envelope so the frontend can integrate.
    """
    try:
        # Attempt to call the resource management agent
        from agents.runtime.src.agent_catalog import AgentCatalog

        catalog = AgentCatalog()
        agent = catalog.get_agent("resource_management")
        if agent:
            result = await agent.process(
                {
                    "action": "aggregate_portfolio_demand",
                    "portfolio_id": portfolio_id,
                    "project_id": project_id,
                },
            )
            return {"status": "ok", "data": result}
    except Exception:
        logger.debug("Agent catalog not available; returning scaffold response")

    # Scaffold response when agent runtime is not available
    return {
        "status": "ok",
        "data": {
            "summary": {
                "total_demand_hours": 0,
                "total_supply_hours": 0,
                "capacity_ratio": 0,
                "total_skill_gaps": 0,
                "total_role_gaps": 0,
                "projects_analysed": 0,
            },
            "skill_gaps": [],
            "role_gaps": [],
            "skill_supply": [],
            "recommendations": [],
        },
    }


@router.get("/api/capacity/skills")
async def list_skills(
    category: str | None = Query(default=None),
    framework: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return available skills from the taxonomy."""
    return {
        "status": "ok",
        "data": {
            "skills": [],
            "frameworks": ["SFIA", "ESCO", "ONET", "custom"],
            "categories": [
                "technical",
                "leadership",
                "domain",
                "methodology",
                "tool",
                "language",
                "certification",
                "soft_skill",
            ],
        },
    }
