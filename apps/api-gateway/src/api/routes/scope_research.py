"""Scope research endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
async def generate_scope_research(project_id: str, request: ScopeResearchRequest):
    """Trigger scope research using the Project Definition & Scope agent."""
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("project-definition") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Project Definition agent not available")

    try:
        result = await agent.process(
            {
                "action": "generate_scope_research",
                "project_id": project_id,
                "objective": request.objective,
                "enable_external_research": request.enable_external_research,
                "search_result_limit": request.search_result_limit,
            }
        )
        return ScopeResearchResponse.model_validate(result).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
