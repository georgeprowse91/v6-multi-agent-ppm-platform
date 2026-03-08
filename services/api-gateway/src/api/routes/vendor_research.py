"""Vendor research endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

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
async def research_vendor(
    vendor_id: str,
    payload: VendorResearchRequest,
    orchestrator: Any = Depends(get_orchestrator),
) -> VendorResearchResponse:
    """Trigger external vendor research using the Vendor & Procurement agent."""
    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("vendor-procurement-agent")
    if not agent:
        raise HTTPException(status_code=404, detail="Vendor & Procurement agent not available")

    try:
        result = await agent.process(
            {
                "action": "research_vendor",
                "vendor_id": vendor_id,
                "vendor_name": payload.vendor_name,
                "domain": payload.domain,
            }
        )
        return VendorResearchResponse.model_validate(result)
    except ValidationError as exc:
        logger.error(
            "Vendor agent returned invalid response for vendor %s: %s",
            vendor_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Vendor agent returned an invalid response",
        ) from exc
    except Exception as exc:
        logger.error("Vendor research failed for vendor %s: %s", vendor_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Vendor research failed: {exc}",
        ) from exc
