"""LLM model listing and preference routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from routes._deps import (
    _can_manage_llm,
    _demo_mode_enabled,
    _require_session,
    _resolve_llm_selection,
    _tenant_id_from_request,
    get_enabled_models,
    llm_preferences_store,
)
from routes._models import LLMPreferenceRequest, LLMPreferenceResponse

router = APIRouter()


@router.get("/api/llm/models")
async def list_llm_models(request: Request) -> JSONResponse:
    _require_session(request)
    models = get_enabled_models(demo_mode=_demo_mode_enabled())
    return JSONResponse(status_code=200, content={"models": [{"provider": m.provider, "model_id": m.model_id, "display_name": m.display_name, "capabilities": list(m.capabilities), "allow_in_demo": m.allow_in_demo} for m in models]})


@router.get("/api/llm/preferences")
async def get_llm_preferences(request: Request, project_id: str | None = None) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    provider, model_id = _resolve_llm_selection(tenant_id, project_id, session.get("subject"))
    return JSONResponse(status_code=200, content={"provider": provider, "model_id": model_id})


@router.post("/api/llm/preferences", response_model=LLMPreferenceResponse)
async def set_llm_preferences(payload: LLMPreferenceRequest, request: Request) -> LLMPreferenceResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if payload.scope in {"tenant", "project"} and not _can_manage_llm(request, session):
        raise HTTPException(status_code=403, detail="RBAC denied")
    user_id = session.get("subject") if payload.scope == "user" else None
    preference = llm_preferences_store.set_preference(scope=payload.scope, tenant_id=tenant_id, project_id=payload.project_id, user_id=user_id, provider=payload.provider, model_id=payload.model_id)
    return LLMPreferenceResponse(**preference)
