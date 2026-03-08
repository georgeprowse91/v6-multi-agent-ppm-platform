"""Scope research endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


class ScopeResearchRequest(BaseModel):
    objective: str = Field(..., min_length=3)
    enable_external_research: bool | None = None
    search_result_limit: int | None = Field(default=None, ge=1, le=10)


class ScopeResearchResponse(BaseModel):
    project_id: str
    objective: str
    scope: dict[str, Any]
    requirements: list[str]
    wbs: list[str]
    sources: list[str]
    summary: str | None = None
    used_external_research: bool
    notice: str | None = None
    requested_by: str | None = None
    generated_at: str
    correlation_id: str | None = None


@router.post("/projects/{project_id}/scope/research", response_model=ScopeResearchResponse)
async def generate_scope_research(
    project_id: str,
    payload: ScopeResearchRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> ScopeResearchResponse:
    """Trigger scope research using the Project Definition & Scope agent."""
    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("scope-definition-agent")
    if not agent:
        raise HTTPException(status_code=404, detail="Project Definition agent not available")

    try:
        result = await agent.process(
            {
                "action": "generate_scope_research",
                "project_id": project_id,
                "objective": payload.objective,
                "enable_external_research": payload.enable_external_research,
                "search_result_limit": payload.search_result_limit,
            }
        )
        return ScopeResearchResponse.model_validate(result)
    except ValidationError as exc:
        logger.error(
            "Scope agent returned invalid response for project %s: %s",
            project_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Scope agent returned an invalid response",
        ) from exc
    except Exception as exc:
        logger.error("Scope research failed for project %s: %s", project_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Scope research failed: {exc}",
        ) from exc
