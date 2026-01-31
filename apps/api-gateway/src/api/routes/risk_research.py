"""Risk research endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class RiskResearchRequest(BaseModel):
    context: str = Field(..., min_length=3, description="Project domain or context.")
    region: str | None = Field(default=None, description="Geographic region for the project.")
    categories: list[str] | None = Field(default=None, description="High-level risk categories.")


class RiskResearchResponse(BaseModel):
    project_id: str | None
    external_risks: list[dict[str, Any]]
    added_risks: list[dict[str, Any]]
    used_external_research: bool
    notice: str | None = None
    correlation_id: str | None = None


@router.post("/projects/{project_id}/risks/research", response_model=RiskResearchResponse)
async def research_project_risks(project_id: str, request: RiskResearchRequest):
    """Trigger external risk research using the Risk & Issue Management agent."""
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("agent_015") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Risk Management agent not available")

    try:
        result = await agent.process(
            {
                "action": "research_risks",
                "project_id": project_id,
                "domain": request.context,
                "region": request.region,
                "categories": request.categories or [],
            }
        )
        return RiskResearchResponse.model_validate(result).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
