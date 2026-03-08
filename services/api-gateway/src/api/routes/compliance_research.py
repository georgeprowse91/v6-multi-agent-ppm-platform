"""Compliance research endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


class ComplianceResearchRequest(BaseModel):
    domain: str = Field(..., min_length=2, description="Project domain or industry.")
    region: str | None = Field(default=None, description="Region for regulatory monitoring.")


class ComplianceResearchResponse(BaseModel):
    changes_detected: int
    regulations_impacted: int
    impacted_regulations: list[dict[str, Any]]
    external_monitoring: dict[str, Any] | None = None
    last_check: str


@router.post(
    "/projects/{project_id}/compliance/research", response_model=ComplianceResearchResponse
)
async def research_compliance(
    project_id: str,
    payload: ComplianceResearchRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> ComplianceResearchResponse:
    """Trigger external regulatory monitoring using the Compliance agent."""
    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("compliance-governance-agent")
    if not agent:
        raise HTTPException(status_code=404, detail="Compliance agent not available")

    try:
        result = await agent.process(
            {
                "action": "monitor_regulatory_changes",
                "project_id": project_id,
                "domain": payload.domain,
                "region": payload.region,
            }
        )
        return ComplianceResearchResponse.model_validate(result)
    except ValidationError as exc:
        logger.error(
            "Compliance agent returned invalid response for project %s: %s",
            project_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Compliance agent returned an invalid response",
        ) from exc
    except Exception as exc:
        logger.error("Compliance research failed for project %s: %s", project_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Compliance research failed: {exc}",
        ) from exc
