"""Compliance research endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

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
    project_id: str, request: ComplianceResearchRequest
) -> ComplianceResearchResponse:
    """Trigger external regulatory monitoring using the Compliance agent."""
    orchestrator = request.app.state.orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("agent_016") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Compliance agent not available")

    try:
        result = await agent.process(
            {
                "action": "monitor_regulatory_changes",
                "project_id": project_id,
                "domain": request.domain,
                "region": request.region,
            }
        )
        return ComplianceResearchResponse.model_validate(result)
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Invalid compliance response") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
