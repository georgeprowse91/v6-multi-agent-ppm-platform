"""Vendor management endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

router = APIRouter()


class VendorProfileResponse(BaseModel):
    vendor: dict[str, Any]
    correlation_id: str | None = None


class VendorUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(..., description="Vendor fields to update.")


class VendorUpdateResponse(BaseModel):
    vendor_id: str
    status: str | None = None
    updates: dict[str, Any]


class VendorListResponse(BaseModel):
    total_results: int
    vendors: list[dict[str, Any]]
    search_criteria: dict[str, Any]
    tenant_id: str | None = None


@router.get("/vendors/{vendor_id}", response_model=VendorProfileResponse)
async def get_vendor_profile(vendor_id: str):
    """Get a vendor profile by ID."""
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("agent_013") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Vendor & Procurement agent not available")

    try:
        result = await agent.process({"action": "get_vendor_profile", "vendor_id": vendor_id})
        return VendorProfileResponse.model_validate(result).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Invalid vendor profile response") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/vendors/{vendor_id}", response_model=VendorUpdateResponse)
async def update_vendor_profile(vendor_id: str, request: VendorUpdateRequest):
    """Update fields on a vendor profile."""
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("agent_013") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Vendor & Procurement agent not available")

    try:
        result = await agent.process(
            {
                "action": "update_vendor_profile",
                "vendor_id": vendor_id,
                "updates": request.updates,
            }
        )
        return VendorUpdateResponse.model_validate(result).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Invalid vendor update response") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/vendors", response_model=VendorListResponse)
async def list_vendors(
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    max_risk_score: float | None = Query(default=None),
):
    """List vendor profiles with optional filtering."""
    from api.main import orchestrator

    if not orchestrator or not orchestrator.initialized:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent("agent_013") if orchestrator else None
    if not agent:
        raise HTTPException(status_code=404, detail="Vendor & Procurement agent not available")

    criteria = {}
    if category:
        criteria["category"] = category
    if status:
        criteria["status"] = status
    if min_rating is not None:
        criteria["min_rating"] = min_rating
    if max_risk_score is not None:
        criteria["max_risk_score"] = max_risk_score

    try:
        result = await agent.process({"action": "list_vendor_profiles", "criteria": criteria})
        return VendorListResponse.model_validate(result).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Invalid vendor list response") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
