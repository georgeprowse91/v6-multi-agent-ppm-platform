"""Vendor research endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

router = APIRouter()


class VendorResearchRequest(BaseModel):
    domain: str = Field(..., min_length=2, description="Procurement domain or category.")
    vendor_name: str | None = Field(default=None, description="Optional vendor name override.")


class VendorResearchResponse(BaseModel):
    vendor_id: str | None
    vendor_name: str | None
    summary: str
    insights: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    used_external_research: bool
    notice: str | None = None
    correlation_id: str | None = None


@router.post("/vendors/{vendor_id}/research", response_model=VendorResearchResponse)
async def research_vendor(vendor_id: str, request: VendorResearchRequest) -> VendorResearchResponse:
    """Trigger external vendor research using the Vendor & Procurement agent."""
    orchestrator = request.app.state.orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("vendor-procurement-agent") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Vendor & Procurement agent not available")

    try:
        result = await agent.process(
            {
                "action": "research_vendor",
                "vendor_id": vendor_id,
                "vendor_name": request.vendor_name,
                "domain": request.domain,
            }
        )
        return VendorResearchResponse.model_validate(result)
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Invalid vendor research response") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
