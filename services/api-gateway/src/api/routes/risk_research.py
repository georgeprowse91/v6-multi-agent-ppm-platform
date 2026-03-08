"""Risk research endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

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
async def research_project_risks(
    project_id: str,
    payload: RiskResearchRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> RiskResearchResponse:
    """Trigger external risk research using the Risk & Issue Management agent."""
    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("risk-management-agent")
    if not agent:
        raise HTTPException(status_code=404, detail="Risk Management agent not available")

    try:
        result = await agent.process(
            {
                "action": "research_risks",
                "project_id": project_id,
                "domain": payload.context,
                "region": payload.region,
                "categories": payload.categories or [],
            }
        )
        return RiskResearchResponse.model_validate(result)
    except ValidationError as exc:
        logger.error(
            "Risk agent returned invalid response for project %s: %s",
            project_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Risk agent returned an invalid response",
        ) from exc
    except Exception as exc:
        logger.error(
            "Risk research failed for project %s: %s", project_id, exc
        )
        raise HTTPException(
            status_code=502,
            detail=f"Risk research failed: {exc}",
        ) from exc
