"""Template listing, detail, apply, and instantiate routes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from routes._deps import (
    CanonicalTemplateDefinition,
    CanonicalTemplateSummary,
    ColumnCreate,
    RowCreate,
    SheetCreate,
    TemplateInstantiateRequest,
    TemplateInstantiateResponse,
    TemplateType,
    _document_client,
    _load_projects,
    _raise_upstream_error,
    _require_roles,
    _require_session,
    _tenant_id_from_request,
    build_event,
    build_forward_headers,
    get_audit_log_store,
    get_catalog_template,
    get_deliverable_template,
    get_methodology_map,
    get_template_mapping,
    list_catalog_templates,
    list_templates_for_methodology_node,
    logger,
    render_template_value_with_unresolved,
    spreadsheet_store,
)
from routes._models import (
    ProjectRecord,
    TemplateApplyRequest,
    TemplateApplyResponse,
    TemplateDefinition,
    TemplateSummary,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_templates():
    from routes._deps import TEMPLATES_PATH, _load_json

    raw = _load_json(TEMPLATES_PATH, {"templates": []})
    templates = raw.get("templates", [])
    return [TemplateDefinition.model_validate(t) for t in templates]


def _select_project_template(template_id: str, *, version: str | None = None):
    templates = _load_templates()
    matches = [t for t in templates if t.id == template_id]
    if not matches:
        return None
    if version:
        match = next((t for t in matches if t.version == version), None)
        return match or matches[0]
    return matches[0]


def _resolve_template_methodology_id(template) -> str:
    methodology = template.methodology
    return str(methodology.get("id") or methodology.get("type") or "hybrid")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _unique_project_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for i in range(1, 1000):
        candidate = f"{base}-{i}"
        if candidate not in existing:
            return candidate
    return f"{base}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _persist_projects(projects):
    from routes._deps import PROJECTS_PATH, _write_json

    _write_json(PROJECTS_PATH, {"projects": [p.model_dump() for p in projects]})


def _template_context(
    *,
    project_id: str,
    tenant_id: str,
    session: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from routes._deps import build_placeholder_context

    context = build_placeholder_context(
        project_id=project_id, tenant_id=tenant_id, user_id=session.get("subject")
    )
    if parameters:
        context.update(parameters)
    return context


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/api/templates/{template_id}/instantiate", response_model=TemplateInstantiateResponse)
async def instantiate_template(
    template_id: str, payload: TemplateInstantiateRequest, request: Request
) -> TemplateInstantiateResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    template = get_deliverable_template(template_id)
    if template is None:
        catalog_template = get_catalog_template(template_id)
        if catalog_template:
            legacy_template_id = catalog_template.template_id.split(".", 1)[0]
            template = get_deliverable_template(legacy_template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    context = _template_context(
        project_id=payload.project_id,
        tenant_id=tenant_id,
        session=session,
        parameters=payload.parameters,
    )
    logger.info(
        "templates.instantiate",
        extra={
            "tenant_id": tenant_id,
            "project_id": payload.project_id,
            "template_id": template_id,
        },
    )
    if template.type == TemplateType.document:
        if template.defaults is None:
            raise HTTPException(status_code=500, detail="Document template defaults missing")
        advisories: set[str] = set()
        classification = context.get("classification") or template.defaults.classification
        retention_days = int(context.get("retention_days") or template.defaults.retention_days)
        payload_model = template.payload
        name, unresolved = render_template_value_with_unresolved(
            payload_model.name_template, context
        )
        advisories.update(unresolved)
        content, unresolved = render_template_value_with_unresolved(
            payload_model.content_template, context
        )
        advisories.update(unresolved)
        metadata = {}
        if payload_model.metadata_template:
            metadata, unresolved = render_template_value_with_unresolved(
                payload_model.metadata_template, context
            )
            advisories.update(unresolved)
        headers = build_forward_headers(request, session)
        response = await _document_client().create_document(
            {
                "name": name,
                "content": content,
                "classification": classification,
                "retention_days": retention_days,
                "metadata": metadata,
            },
            headers=headers,
        )
        if response.status_code == 403:
            return JSONResponse(status_code=403, content=response.json())
        if response.status_code >= 400:
            _raise_upstream_error(response)
        body = response.json()
        upstream_advisories = body.get("advisories") or []
        combined = [*upstream_advisories]
        if advisories:
            combined.append(
                "Unresolved placeholders left unchanged: " + ", ".join(sorted(advisories))
            )
        return TemplateInstantiateResponse(
            created_type=TemplateType.document,
            document_id=body.get("document_id"),
            name=body.get("name"),
            advisories=combined or None,
        )
    if template.type == TemplateType.spreadsheet:
        advisories: set[str] = set()
        payload_model = template.payload
        sheet_name, unresolved = render_template_value_with_unresolved(
            payload_model.sheet_name_template, context
        )
        advisories.update(unresolved)
        columns = [
            ColumnCreate(name=c.name, type=c.type, required=c.required)
            for c in payload_model.columns
        ]
        try:
            sheet = spreadsheet_store.create_sheet(
                tenant_id, payload.project_id, SheetCreate(name=sheet_name, columns=columns)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload_model.seed_rows:
            column_map = {c.name: c.column_id for c in sheet.columns}
            for row in payload_model.seed_rows:
                rendered, unresolved = render_template_value_with_unresolved(row.values, context)
                advisories.update(unresolved)
                values = {column_map[n]: v for n, v in rendered.items() if n in column_map}
                try:
                    spreadsheet_store.add_row(
                        tenant_id, payload.project_id, sheet.sheet_id, RowCreate(values=values)
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
        resp_advisories = None
        if advisories:
            resp_advisories = [
                "Unresolved placeholders left unchanged: " + ", ".join(sorted(advisories))
            ]
        return TemplateInstantiateResponse(
            created_type=TemplateType.spreadsheet,
            sheet_id=sheet.sheet_id,
            sheet_name=sheet.name,
            advisories=resp_advisories,
        )
    raise HTTPException(status_code=400, detail="Unsupported template type")


@router.get("/api/templates", response_model=list[TemplateSummary | CanonicalTemplateSummary])
async def list_templates(
    request: Request,
    type: str | None = None,
    artefact: str | None = None,
    methodology: str | None = None,
    compliance_tag: str | None = None,
    q: str | None = None,
    gallery: bool | None = None,
    tag: str | None = None,
) -> list[TemplateSummary | CanonicalTemplateSummary]:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    wants_gallery = (
        gallery is True
        or "type" in request.query_params
        or "artefact" in request.query_params
        or "methodology" in request.query_params
        or "compliance_tag" in request.query_params
        or "q" in request.query_params
    )
    if wants_gallery:
        mapped_artefact = artefact
        if type and not mapped_artefact:
            mapped_artefact = type
        templates = list_catalog_templates(
            artefact=mapped_artefact,
            methodology=methodology,
            compliance_tag=compliance_tag or tag,
            query=q,
        )
        logger.info(
            "templates.list",
            extra={
                "tenant_id": tenant_id,
                "project_id": request.query_params.get("project_id"),
                "template_id": None,
            },
        )
        return templates
    _require_roles(
        request,
        {
            "PMO_ADMIN",
            "PM",
            "TEAM_MEMBER",
            "AUDITOR",
            "tenant_owner",
            "portfolio_admin",
            "project_manager",
            "analyst",
            "auditor",
        },
    )
    templates = _load_templates()
    summaries: list[TemplateSummary] = []
    for t in templates:
        m = t.methodology
        summaries.append(
            TemplateSummary(
                id=t.id,
                name=t.name,
                version=t.version,
                available_versions=t.available_versions,
                summary=t.summary,
                description=t.description,
                methodology_name=str(m.get("name", "Methodology")),
                methodology_type=str(m.get("type", "custom")),
            )
        )
    return summaries


@router.get(
    "/api/templates/{template_id}", response_model=TemplateDefinition | CanonicalTemplateDefinition
)
async def get_template(
    template_id: str, request: Request, gallery: bool | None = None, version: str | None = None
) -> TemplateDefinition | CanonicalTemplateDefinition:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    catalog_template = get_catalog_template(template_id)
    if gallery is True or catalog_template is not None:
        if not catalog_template:
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info(
            "templates.get",
            extra={
                "tenant_id": tenant_id,
                "project_id": request.query_params.get("project_id"),
                "template_id": template_id,
            },
        )
        return catalog_template
    _require_roles(
        request,
        {
            "PMO_ADMIN",
            "PM",
            "TEAM_MEMBER",
            "AUDITOR",
            "tenant_owner",
            "portfolio_admin",
            "project_manager",
            "analyst",
            "auditor",
        },
    )
    template = _select_project_template(template_id, version=version)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/api/templates/{template_id}/apply", response_model=TemplateApplyResponse)
async def apply_template(
    template_id: str, payload: TemplateApplyRequest, request: Request
) -> TemplateApplyResponse:
    session = _require_roles(
        request, {"PMO_ADMIN", "PM", "tenant_owner", "portfolio_admin", "project_manager"}
    )
    template = _select_project_template(template_id, version=payload.version)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    selected_version = payload.version or template.version
    if selected_version not in template.available_versions:
        raise HTTPException(status_code=422, detail="Template version not available")
    projects = _load_projects()
    existing_ids = {p.id for p in projects}
    base_slug = _slugify(payload.project_name) or "project"
    project_id = _unique_project_id(base_slug, existing_ids)
    methodology_id = _resolve_template_methodology_id(template)
    methodology_map = get_methodology_map(methodology_id)
    template_mapping = get_template_mapping(template.id)
    project = ProjectRecord(
        id=project_id,
        name=payload.project_name,
        template_id=template.id,
        template_version=selected_version,
        created_at=datetime.now(timezone.utc).isoformat() + "Z",
        methodology=methodology_map,
        agent_config=template.agent_config,
        connector_config=template.connector_config,
        initial_tabs=template.initial_tabs,
        dashboards=template.dashboards,
    )
    projects.append(project)
    _persist_projects(projects)
    get_audit_log_store().record_event(
        build_event(
            tenant_id=session.get("tenant_id", "unknown"),
            actor_id=session.get("subject") or "ui-user",
            actor_type="user",
            roles=session.get("roles") or [],
            action="template.applied",
            resource_type="template",
            resource_id=template_id,
            outcome="success",
            metadata={"project_id": project_id},
        )
    )
    response_template = template.model_copy(
        update={"version": selected_version, "methodology": methodology_map}
    )
    related_templates = []
    stage_id = activity_id = None
    if methodology_map.get("stages"):
        first_stage = methodology_map["stages"][0]
        stage_id = first_stage.get("id")
        first_activity = (first_stage.get("activities") or [{}])[0]
        activity_id = first_activity.get("id")
    if stage_id and activity_id:
        related_templates = list_templates_for_methodology_node(
            methodology_id, stage_id, activity_id, task_id=None, lifecycle_event=None
        )
    return TemplateApplyResponse(
        project=project,
        template=response_template,
        methodology=methodology_map,
        template_mapping=template_mapping,
        related_templates=related_templates,
    )
