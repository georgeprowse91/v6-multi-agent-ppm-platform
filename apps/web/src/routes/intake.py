"""Intake / merge-review routes."""
from __future__ import annotations

import base64
from typing import Any, Literal

import yaml
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from routes._deps import (
    DEMAND_PROMPT_PATH,
    INTAKE_ASSISTANT_PROMPTS,
    PROJECT_PROMPT_PATH,
    _data_service_client,
    _demo_mode_enabled,
    _document_client,
    _load_prompt,
    _raise_upstream_error,
    _render_prompt,
    _require_multimodal_intake,
    _require_duplicate_resolution,
    _require_session,
    _tenant_id_from_request,
    build_audit_event,
    build_forward_headers,
    emit_audit_event,
    intake_store,
    logger,
    merge_review_store,
    permission_required,
)
from routes._deps import LLMGateway, LLMProviderError, get_trace_id
from routes._models import (
    IntakeAssistantRequest,
    IntakeAssistantResponse,
    IntakeExtractionEntity,
    IntakeExtractionResponse,
)
from routes._deps import (
    IntakeDecision,
    IntakeRequest as IntakeRequestModel,
    IntakeRequestCreate,
    MergeDecision,
    MergeReviewCase,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_upload_content(content_bytes: bytes) -> tuple[str, str]:
    try:
        return content_bytes.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return base64.b64encode(content_bytes).decode("ascii"), "base64"


async def _extract_intake_fields(prompt_path, document_name: str, document_content: str) -> dict[str, Any]:
    prompt_payload = _load_prompt(prompt_path)
    system_prompt = prompt_payload.get("system", "")
    user_template = prompt_payload.get("user", "")
    user_prompt = _render_prompt(user_template, document_name=document_name, document_content=document_content)
    llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
    response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt, json_mode=True)
    import json
    data = json.loads(response.content)
    if not isinstance(data, dict):
        raise ValueError("Extraction did not produce a dictionary")
    return data


def _normalize_demand_payload(raw: dict[str, Any], *, document_name: str) -> dict[str, Any]:
    from routes._deps import _coerce_str
    return {
        "title": _coerce_str(raw.get("title")) or document_name,
        "description": _coerce_str(raw.get("description")),
        "requested_by": _coerce_str(raw.get("requested_by")),
        "priority": _coerce_str(raw.get("priority")) or "Medium",
        "source": _coerce_str(raw.get("source")),
        "tags": list(raw.get("tags") or []),
    }


def _normalize_project_payload(raw: dict[str, Any], *, tenant_id: str, document_name: str, owner_fallback: str) -> dict[str, Any]:
    from routes._deps import _coerce_str
    return {
        "name": _coerce_str(raw.get("name")) or document_name,
        "description": _coerce_str(raw.get("description")),
        "owner": _coerce_str(raw.get("owner")) or owner_fallback,
        "tenant_id": tenant_id,
        "status": _coerce_str(raw.get("status")) or "Proposed",
        "tags": list(raw.get("tags") or []),
    }


def _non_empty(value: str | None) -> bool:
    return bool(value and value.strip())


def _load_intake_assistant_prompt(step_id: str) -> dict[str, Any]:
    prompt_path = INTAKE_ASSISTANT_PROMPTS.get(step_id)
    if not prompt_path or not prompt_path.exists():
        return {}
    try:
        raw = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _build_intake_assistant_response(payload: IntakeAssistantRequest) -> IntakeAssistantResponse:
    form_state = payload.form_state
    errors = payload.validation_errors
    proposals: dict[str, str] = {}
    questions: list[str] = []
    apply_hints: list[str] = []
    _load_intake_assistant_prompt(payload.step_id)
    if payload.step_id == "sponsor":
        if not _non_empty(form_state.get("sponsorName")):
            questions.append("Who is the executive sponsor and what is their role?")
        if not _non_empty(form_state.get("sponsorEmail")):
            questions.append("What is the sponsor's best contact email?")
        if not _non_empty(form_state.get("sponsorDepartment")):
            questions.append("Which business unit is accountable for this request?")
    if payload.step_id == "business":
        if not _non_empty(form_state.get("businessSummary")) and _non_empty(payload.user_answer):
            proposals["businessSummary"] = payload.user_answer.strip()
        if not _non_empty(form_state.get("businessJustification")):
            proposals["businessJustification"] = "This initiative addresses a validated business need and aligns to current portfolio priorities."
        if not _non_empty(form_state.get("expectedBenefits")):
            proposals["expectedBenefits"] = "Reduce manual effort by 20% within two quarters and improve stakeholder response time by 30%."
        if not _non_empty(form_state.get("businessSummary")):
            questions.append("What business problem should this intake solve in one sentence?")
    if payload.step_id == "success":
        if not _non_empty(form_state.get("successMetrics")):
            proposals["successMetrics"] = "Achieve a 25% reduction in cycle time by Q4, maintain >=95% SLA adherence, and report monthly adoption above 80%."
            questions.append("Which baseline metric should we compare against to prove value?")
        if not _non_empty(form_state.get("riskNotes")):
            proposals["riskNotes"] = "Dependency on data quality improvements and availability of SME reviewers during pilot phase."
    if payload.step_id == "attachments":
        if not _non_empty(form_state.get("attachmentSummary")):
            questions.append("Which supporting documents should reviewers inspect first?")
            proposals["attachmentSummary"] = "Includes current-state process notes, stakeholder feedback summary, and budget assumptions worksheet."
    for field in proposals:
        if _non_empty(form_state.get(field)):
            apply_hints.append(f"{field}: confirmation required because the field already contains a value.")
        else:
            apply_hints.append(f"{field}: safe to apply directly (field is empty).")
    for field_name, message in errors.items():
        questions.append(f"Validation issue on {field_name}: {message}")
    return IntakeAssistantResponse(step_id=payload.step_id, questions=questions, proposals=proposals, apply_hints=apply_hints)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/intake/uploads")
async def upload_intake_document(request: Request, file: UploadFile = File(...), classification: str = Form("internal"), retention_days: int = Form(90)) -> JSONResponse:
    _require_multimodal_intake()
    session = _require_session(request)
    content_bytes = await file.read()
    content, encoding = _decode_upload_content(content_bytes)
    document_name = file.filename or "intake-document"
    metadata = {"filename": document_name, "content_type": file.content_type, "encoding": encoding, "size_bytes": len(content_bytes), "source": "multimodal_intake"}
    payload = {"name": document_name, "content": content, "classification": classification, "retention_days": retention_days, "metadata": metadata}
    response = await _document_client().create_document(payload, headers=build_forward_headers(request, session))
    if response.status_code >= 400:
        _raise_upstream_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.post("/api/intake/extract", response_model=IntakeExtractionResponse)
async def extract_intake_document(request: Request, file: UploadFile = File(...), target: Literal["demand", "project", "both"] = Form("both"), document_id: str | None = Form(None)) -> IntakeExtractionResponse:
    _require_multimodal_intake()
    session = _require_session(request)
    content_bytes = await file.read()
    content, encoding = _decode_upload_content(content_bytes)
    if encoding == "base64":
        try:
            content = base64.b64decode(content).decode("utf-8", errors="ignore")
        except (ValueError, UnicodeDecodeError):
            content = ""
    document_name = file.filename or "intake-document"
    tenant_id = session.get("tenant_id") or "default"
    owner_fallback = session.get("subject") or "unknown"
    headers = build_forward_headers(request, session)
    data_client = _data_service_client()
    response = IntakeExtractionResponse(document_id=document_id)
    entities: dict[str, IntakeExtractionEntity] = {}
    try:
        if target in {"demand", "both"}:
            raw_demand = await _extract_intake_fields(prompt_path=DEMAND_PROMPT_PATH, document_name=document_name, document_content=content)
            demand_payload = _normalize_demand_payload(raw_demand, document_name=document_name)
            if document_id and not demand_payload.get("source"):
                demand_payload["source"] = f"document:{document_id}"
            demand_response = await data_client.store_entity("demand", {"tenant_id": tenant_id, "data": demand_payload}, headers=headers)
            if demand_response.status_code >= 400:
                _raise_upstream_error(demand_response)
            stored = demand_response.json()
            entities["demand"] = IntakeExtractionEntity(schema_name=stored.get("schema_name", "demand"), entity_id=stored.get("id", ""))
            response.demand = demand_payload
        if target in {"project", "both"}:
            raw_project = await _extract_intake_fields(prompt_path=PROJECT_PROMPT_PATH, document_name=document_name, document_content=content)
            project_payload = _normalize_project_payload(raw_project, tenant_id=tenant_id, document_name=document_name, owner_fallback=owner_fallback)
            project_response = await data_client.store_entity("project", {"tenant_id": tenant_id, "data": project_payload}, headers=headers)
            if project_response.status_code >= 400:
                _raise_upstream_error(project_response)
            stored_project = project_response.json()
            entities["project"] = IntakeExtractionEntity(schema_name=stored_project.get("schema_name", "project"), entity_id=stored_project.get("id", ""))
            response.project = project_payload
    except (ValueError, LLMProviderError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response.entities = entities
    return response


@router.post("/api/intake/assistant", response_model=IntakeAssistantResponse)
def intake_assistant(payload: IntakeAssistantRequest) -> IntakeAssistantResponse:
    return _build_intake_assistant_response(payload)


@router.get("/api/intake", response_model=list[IntakeRequestModel])
def list_intake_requests(status: str | None = None) -> list[IntakeRequestModel]:
    return intake_store.list_requests(status=status)


@router.post("/api/intake", response_model=IntakeRequestModel, status_code=201)
def create_intake_request(payload: IntakeRequestCreate) -> IntakeRequestModel:
    return intake_store.create_request(payload)


@router.get("/api/intake/{request_id}", response_model=IntakeRequestModel)
def get_intake_request(request_id: str) -> IntakeRequestModel:
    request = intake_store.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Intake request not found")
    return request


@router.post("/api/intake/{request_id}/decision", response_model=IntakeRequestModel)
@permission_required("intake.approve")
def decide_intake_request(request_id: str, payload: IntakeDecision) -> IntakeRequestModel:
    try:
        request = intake_store.update_decision(request_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not request:
        raise HTTPException(status_code=404, detail="Intake request not found")
    return request


@router.get("/api/merge-review", response_model=list[MergeReviewCase])
def list_merge_review_cases(status: str | None = None) -> list[MergeReviewCase]:
    _require_duplicate_resolution()
    return merge_review_store.list_cases(status=status)


@router.post("/api/merge-review/{case_id}/decision", response_model=MergeReviewCase)
def decide_merge_review_case(request: Request, case_id: str, payload: MergeDecision) -> MergeReviewCase:
    _require_duplicate_resolution()
    session = _require_session(request)
    case = merge_review_store.update_decision(case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Merge review case not found")
    tenant_id = _tenant_id_from_request(request, session) or "default"
    from routes._deps import _roles_from_request, get_trace_id
    event = build_audit_event(tenant_id=tenant_id, action="duplicate_resolution.merge_decision", outcome="success" if payload.decision == "approved" else "denied", actor_id=payload.reviewer_id, actor_type="user", actor_roles=session.get("roles") or [], resource_id=case.case_id, resource_type=f"{case.entity_type}_merge_review", metadata={"decision": payload.decision, "comments": payload.comments, "primary_record_id": case.primary_record.record_id, "duplicate_record_id": case.duplicate_record.record_id}, trace_id=get_trace_id() or "unknown", correlation_id=session.get("correlation_id"))
    emit_audit_event(event)
    return case
