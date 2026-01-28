from __future__ import annotations

import json
import logging
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
for root in (OBSERVABILITY_ROOT, SECURITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from knowledge_store import KnowledgeStore  # noqa: E402
from security.audit_log import build_event, get_audit_log_store  # noqa: E402
from gating import evaluate_activity_access, next_required_activity, stage_progress  # noqa: E402
from methodologies import available_methodologies, get_methodology_map  # noqa: E402
from workspace_state import (  # noqa: E402
    ActivityCompletionUpdate,
    CanvasTab,
    WorkspaceSelectionUpdate,
    WorkspaceState,
)
from workspace_state_store import WorkspaceStateStore  # noqa: E402
from timeline_models import (  # noqa: E402
    Milestone,
    MilestoneCreate,
    MilestoneUpdate,
    TimelineExportResponse,
    TimelineResponse,
)
from timeline_store import TimelineStore  # noqa: E402
from document_proxy import DocumentServiceClient, build_forward_headers  # noqa: E402

WEB_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = WEB_ROOT / "static"
DATA_DIR = WEB_ROOT / "data"
STORAGE_DIR = WEB_ROOT / "storage"
TEMPLATES_PATH = DATA_DIR / "templates.json"
PROJECTS_PATH = DATA_DIR / "projects.json"
KNOWLEDGE_DB_PATH = DATA_DIR / "knowledge.db"
WORKSPACE_STATE_PATH = STORAGE_DIR / "workspace_state.json"
TIMELINES_PATH = STORAGE_DIR / "timelines.json"

SESSION_COOKIE = "ppm_session"
SESSION_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(title="PPM Web Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
configure_tracing("web-ui")
configure_metrics("web-ui")
app.add_middleware(TraceMiddleware, service_name="web-ui")
app.add_middleware(RequestMetricsMiddleware, service_name="web-ui")

knowledge_store: KnowledgeStore | None = None
workspace_state_store = WorkspaceStateStore(WORKSPACE_STATE_PATH)
timeline_store = TimelineStore(TIMELINES_PATH)
logger = logging.getLogger("web-ui")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "web-ui"


class UIConfig(BaseModel):
    api_gateway_url: str
    workflow_engine_url: str
    oidc_enabled: bool
    login_url: str
    logout_url: str


class SessionInfo(BaseModel):
    authenticated: bool
    subject: str | None = None
    tenant_id: str | None = None
    roles: list[str] | None = None


class WorkflowStartRequest(BaseModel):
    workflow_id: str


class WorkflowStartResponse(BaseModel):
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    created_at: str
    updated_at: str


class ActivityAccessSummary(BaseModel):
    allowed: bool
    reasons: list[str]
    missing_prereqs: list[str]


class ActivitySummary(BaseModel):
    id: str
    name: str
    description: str
    prerequisites: list[str]
    category: str
    recommended_canvas_tab: CanvasTab
    access: ActivityAccessSummary
    completed: bool


class StageProgressSummary(BaseModel):
    complete_count: int
    total_count: int
    percent: float


class StageSummary(BaseModel):
    id: str
    name: str
    progress: StageProgressSummary
    activities: list[ActivitySummary]


class MethodologyMapSummary(BaseModel):
    id: str
    name: str
    description: str
    stages: list[StageSummary]
    monitoring: list[ActivitySummary]


class GatingSummary(BaseModel):
    current_activity_access: ActivityAccessSummary
    next_required_activity_id: str | None = None


class SelectedActivitySummary(BaseModel):
    id: str
    name: str
    description: str
    assistant_prompts: list[str]
    recommended_canvas_tab: CanvasTab
    category: str


class WorkspaceStateResponse(BaseModel):
    version: int
    tenant_id: str
    project_id: str
    methodology: str | None = None
    current_stage_id: str | None = None
    current_activity_id: str | None = None
    activity_completion: dict[str, bool]
    current_canvas_tab: CanvasTab
    updated_at: str
    available_methodologies: list[str]
    methodology_map_summary: MethodologyMapSummary
    gating: GatingSummary
    selected_activity: SelectedActivitySummary | None = None


class TemplateAgentConfig(BaseModel):
    enabled: list[str]
    disabled: list[str]


class TemplateConnectorConfig(BaseModel):
    enabled: list[str]
    disabled: list[str]


class TemplateTab(BaseModel):
    activity_id: str | None = None
    type: str
    title: str


class TemplateDefinition(BaseModel):
    id: str
    name: str
    version: str
    available_versions: list[str]
    summary: str
    description: str
    methodology: dict[str, Any]
    agent_config: TemplateAgentConfig
    connector_config: TemplateConnectorConfig
    initial_tabs: list[TemplateTab]
    dashboards: list[TemplateTab]


class TemplateSummary(BaseModel):
    id: str
    name: str
    version: str
    available_versions: list[str]
    summary: str
    description: str
    methodology_name: str
    methodology_type: str


class ProjectRecord(BaseModel):
    id: str
    name: str
    template_id: str
    created_at: str
    methodology: dict[str, Any]
    agent_config: TemplateAgentConfig
    connector_config: TemplateConnectorConfig
    initial_tabs: list[TemplateTab]
    dashboards: list[TemplateTab]


class TemplateApplyRequest(BaseModel):
    project_name: str


class TemplateApplyResponse(BaseModel):
    project: ProjectRecord
    template: TemplateDefinition


class DocumentVersionRequest(BaseModel):
    project_id: str
    document_key: str
    name: str
    doc_type: str
    classification: str
    status: str
    content: str
    metadata: dict[str, Any] = {}


class DocumentVersionResponse(BaseModel):
    document_id: str
    document_key: str
    project_id: str
    name: str
    doc_type: str
    classification: str
    version: int
    status: str
    content: str
    created_at: str
    metadata: dict[str, Any]


class DocumentSummaryResponse(BaseModel):
    document_id: str
    document_key: str
    project_id: str
    name: str
    doc_type: str
    classification: str
    latest_version: int
    latest_status: str
    created_at: str
    updated_at: str


class LessonRequest(BaseModel):
    project_id: str
    stage_id: str | None = None
    stage_name: str | None = None
    title: str
    description: str
    tags: list[str] = []
    topics: list[str] = []


class LessonResponse(BaseModel):
    lesson_id: str
    project_id: str
    stage_id: str | None = None
    stage_name: str | None = None
    title: str
    description: str
    tags: list[str]
    topics: list[str]
    created_at: str
    updated_at: str


class LessonRecommendationRequest(BaseModel):
    project_id: str
    tags: list[str] = []
    topics: list[str] = []
    limit: int = 5


class DocumentCanvasRequest(BaseModel):
    name: str
    content: str
    classification: str
    retention_days: int
    metadata: dict[str, Any] = {}


@app.on_event("startup")
async def startup() -> None:
    global knowledge_store
    knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)


def _get_knowledge_store() -> KnowledgeStore:
    global knowledge_store
    if knowledge_store is None:
        knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)
    return knowledge_store


def _document_client() -> DocumentServiceClient:
    return DocumentServiceClient()


def _raise_upstream_error(response: httpx.Response) -> None:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise HTTPException(status_code=response.status_code, detail=detail)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _oidc_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing OIDC setting: {name}")
    return value


def _oidc_optional(name: str) -> str | None:
    return os.getenv(name)


def _session_from_request(request: Request) -> dict[str, Any] | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return _dev_session()
    return SESSION_STORE.get(session_id) or _dev_session()


def _require_session(request: Request) -> dict[str, Any]:
    session = _session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def _dev_session() -> dict[str, Any] | None:
    auth_dev_mode = os.getenv("AUTH_DEV_MODE", "false").lower() in {"1", "true", "yes"}
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if not (auth_dev_mode and environment in {"dev", "development", "local", "test"}):
        return None
    roles_raw = os.getenv("AUTH_DEV_ROLES", "PMO_ADMIN")
    roles = [role.strip() for role in roles_raw.split(",") if role.strip()]
    return {
        "subject": os.getenv("AUTH_DEV_SUBJECT", "dev-user"),
        "tenant_id": os.getenv("AUTH_DEV_TENANT_ID", "dev-tenant"),
        "roles": roles,
        "access_token": "dev-token",
    }


def _require_roles(request: Request, allowed_roles: set[str]) -> dict[str, Any]:
    session = _require_session(request)
    roles = session.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    if not any(role in allowed_roles for role in roles):
        raise HTTPException(status_code=403, detail="RBAC denied")
    return session


def _oidc_enabled() -> bool:
    return bool(
        os.getenv("OIDC_CLIENT_ID") and os.getenv("OIDC_AUTH_URL") and os.getenv("OIDC_TOKEN_URL")
    )


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _load_templates() -> list[TemplateDefinition]:
    payload = _load_json(TEMPLATES_PATH, {"templates": []})
    return [TemplateDefinition.model_validate(item) for item in payload.get("templates", [])]


def _load_projects() -> list[ProjectRecord]:
    payload = _load_json(PROJECTS_PATH, {"projects": []})
    return [ProjectRecord.model_validate(item) for item in payload.get("projects", [])]


def _build_workspace_response(state: WorkspaceState) -> WorkspaceStateResponse:
    methodology_map = get_methodology_map(state.methodology)

    stage_summaries: list[StageSummary] = []
    for stage in methodology_map.get("stages", []):
        activities: list[ActivitySummary] = []
        for activity in stage.get("activities", []):
            access_payload = evaluate_activity_access(methodology_map, state, activity["id"])
            activities.append(
                ActivitySummary(
                    id=activity["id"],
                    name=activity["name"],
                    description=activity["description"],
                    prerequisites=activity.get("prerequisites", []),
                    category=activity["category"],
                    recommended_canvas_tab=activity["recommended_canvas_tab"],
                    access=ActivityAccessSummary(**access_payload),
                    completed=state.activity_completion.get(activity["id"], False),
                )
            )
        stage_summaries.append(
            StageSummary(
                id=stage["id"],
                name=stage["name"],
                progress=StageProgressSummary(**stage_progress(methodology_map, state, stage["id"])),
                activities=activities,
            )
        )

    monitoring_summaries: list[ActivitySummary] = []
    for activity in methodology_map.get("monitoring", []):
        access_payload = evaluate_activity_access(methodology_map, state, activity["id"])
        monitoring_summaries.append(
            ActivitySummary(
                id=activity["id"],
                name=activity["name"],
                description=activity["description"],
                prerequisites=activity.get("prerequisites", []),
                category=activity["category"],
                recommended_canvas_tab=activity["recommended_canvas_tab"],
                access=ActivityAccessSummary(**access_payload),
                completed=state.activity_completion.get(activity["id"], False),
            )
        )

    selected_activity_payload: SelectedActivitySummary | None = None
    if state.current_activity_id:
        activity_lookup = None
        for stage in methodology_map.get("stages", []):
            activity_lookup = next(
                (
                    activity
                    for activity in stage.get("activities", [])
                    if activity["id"] == state.current_activity_id
                ),
                None,
            )
            if activity_lookup:
                break
        if not activity_lookup:
            activity_lookup = next(
                (
                    activity
                    for activity in methodology_map.get("monitoring", [])
                    if activity["id"] == state.current_activity_id
                ),
                None,
            )
        if activity_lookup:
            selected_activity_payload = SelectedActivitySummary(
                id=activity_lookup["id"],
                name=activity_lookup["name"],
                description=activity_lookup["description"],
                assistant_prompts=activity_lookup.get("assistant_prompts", []),
                recommended_canvas_tab=activity_lookup["recommended_canvas_tab"],
                category=activity_lookup["category"],
            )

    current_access = (
        evaluate_activity_access(methodology_map, state, state.current_activity_id)
        if state.current_activity_id
        else {"allowed": True, "reasons": [], "missing_prereqs": []}
    )

    return WorkspaceStateResponse(
        version=state.version,
        tenant_id=state.tenant_id,
        project_id=state.project_id,
        methodology=state.methodology,
        current_stage_id=state.current_stage_id,
        current_activity_id=state.current_activity_id,
        activity_completion=state.activity_completion,
        current_canvas_tab=state.current_canvas_tab,
        updated_at=state.updated_at,
        available_methodologies=available_methodologies(),
        methodology_map_summary=MethodologyMapSummary(
            id=methodology_map["id"],
            name=methodology_map["name"],
            description=methodology_map["description"],
            stages=stage_summaries,
            monitoring=monitoring_summaries,
        ),
        gating=GatingSummary(
            current_activity_access=ActivityAccessSummary(**current_access),
            next_required_activity_id=next_required_activity(methodology_map, state),
        ),
        selected_activity=selected_activity_payload,
    )


def _persist_projects(projects: list[ProjectRecord]) -> None:
    _write_json(PROJECTS_PATH, {"projects": [project.model_dump() for project in projects]})


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return "-".join(filter(None, slug.split("-")))


def _unique_project_id(base: str, existing: set[str]) -> str:
    candidate = base
    while candidate in existing:
        suffix = secrets.token_hex(2)
        candidate = f"{base}-{suffix}"
    return candidate


async def _exchange_code_for_token(code: str) -> dict[str, Any]:
    token_url = _oidc_required("OIDC_TOKEN_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    client_secret = _oidc_optional("OIDC_CLIENT_SECRET")
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(token_url, data=payload)
        response.raise_for_status()
        return response.json()


async def _decode_id_token(id_token: str) -> dict[str, Any]:
    jwks_url = _oidc_required("OIDC_JWKS_URL")
    audience = _oidc_optional("OIDC_AUDIENCE")
    issuer = _oidc_optional("OIDC_ISSUER")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()

    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="OIDC signing key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return jwt.decode(
        id_token,
        public_key,
        algorithms=[unverified_header.get("alg", "RS256")],
        audience=audience,
        issuer=issuer,
        options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
    )


@app.get("/config", response_model=UIConfig)
async def config() -> UIConfig:
    return UIConfig(
        api_gateway_url=os.getenv("API_GATEWAY_URL", "http://localhost:8000"),
        workflow_engine_url=os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082"),
        oidc_enabled=_oidc_enabled(),
        login_url="/login",
        logout_url="/logout",
    )


@app.get("/session", response_model=SessionInfo)
async def session_info(request: Request) -> SessionInfo:
    session = _session_from_request(request)
    if not session:
        return SessionInfo(authenticated=False)
    return SessionInfo(
        authenticated=True,
        subject=session.get("subject"),
        tenant_id=session.get("tenant_id"),
        roles=session.get("roles"),
    )


@app.get("/login")
async def login() -> RedirectResponse:
    if not _oidc_enabled():
        raise HTTPException(status_code=500, detail="OIDC not configured")

    auth_url = _oidc_required("OIDC_AUTH_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    session_id = secrets.token_urlsafe(24)
    SESSION_STORE[session_id] = {"state": state, "nonce": nonce}

    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": os.getenv("OIDC_SCOPE", "openid profile email"),
        "redirect_uri": redirect_uri,
        "state": state,
        "nonce": nonce,
    }
    response = RedirectResponse(url=f"{auth_url}?{urlencode(params)}")
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
        samesite="lax",
    )
    return response


@app.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OIDC callback parameters")

    session = _session_from_request(request)
    if not session or session.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid login state")

    token_response = await _exchange_code_for_token(code)
    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")
    if not id_token or not access_token:
        raise HTTPException(status_code=401, detail="OIDC token response missing tokens")

    claims = await _decode_id_token(id_token)
    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    roles_claim = os.getenv("OIDC_ROLES_CLAIM", "roles")
    tenant_id = claims.get(tenant_claim)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="OIDC token missing tenant claim")

    roles = claims.get(roles_claim) or []
    if isinstance(roles, str):
        roles = [roles]

    session.update(
        {
            "access_token": access_token,
            "id_token": id_token,
            "tenant_id": tenant_id,
            "subject": claims.get("sub"),
            "roles": roles,
        }
    )

    return RedirectResponse(url="/")


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        SESSION_STORE.pop(session_id, None)

    logout_url = _oidc_optional("OIDC_LOGOUT_URL")
    response = RedirectResponse(url=logout_url or "/")
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_gateway_url}/api/v1/status",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
        )
        response.raise_for_status()
        return response.json()


@app.post("/api/workflows/start", response_model=WorkflowStartResponse)
async def api_start_workflow(request: Request, payload: WorkflowStartRequest) -> dict[str, Any]:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{workflow_url}/workflows/start",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
            json={
                "workflow_id": payload.workflow_id,
                "tenant_id": session["tenant_id"],
                "classification": "internal",
                "payload": {"request": "run"},
                "actor": {
                    "id": session.get("subject") or "ui-user",
                    "type": "user",
                    "roles": session.get("roles") or ["PMO_ADMIN"],
                },
            },
        )
        response.raise_for_status()
        return response.json()


@app.get("/api/workspace/{project_id}", response_model=WorkspaceStateResponse)
async def get_workspace_state(project_id: str, request: Request) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.get_or_create(tenant_id, project_id)
    return _build_workspace_response(state)


@app.post("/api/workspace/{project_id}/select", response_model=WorkspaceStateResponse)
async def update_workspace_selection(
    project_id: str, payload: WorkspaceSelectionUpdate, request: Request
) -> WorkspaceStateResponse:
    session = _require_session(request)
    if payload.project_id and payload.project_id != project_id:
        raise HTTPException(status_code=422, detail="project_id mismatch")
    tenant_id = session["tenant_id"]
    updates = payload.model_dump(exclude={"project_id"})
    state = workspace_state_store.update_selection(tenant_id, project_id, updates)
    return _build_workspace_response(state)


@app.post("/api/workspace/{project_id}/activity-completion", response_model=WorkspaceStateResponse)
async def update_activity_completion(
    project_id: str, payload: ActivityCompletionUpdate, request: Request
) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.update_activity_completion(
        tenant_id, project_id, payload.activity_id, payload.completed
    )
    return _build_workspace_response(state)


@app.get("/api/timeline/{project_id}", response_model=TimelineResponse)
async def list_timeline_milestones(project_id: str, request: Request) -> TimelineResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestones = timeline_store.list_milestones(tenant_id, project_id)
    logger.info(
        "timeline.list",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TimelineResponse(
        tenant_id=tenant_id,
        project_id=project_id,
        milestones=milestones,
    )


@app.post("/api/timeline/{project_id}/milestones", response_model=Milestone)
async def create_timeline_milestone(
    project_id: str, payload: MilestoneCreate, request: Request
) -> Milestone:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestone = timeline_store.create_milestone(tenant_id, project_id, payload)
    logger.info(
        "timeline.create",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "milestone_id": milestone.milestone_id,
        },
    )
    return milestone


@app.patch("/api/timeline/{project_id}/milestones/{milestone_id}", response_model=Milestone)
async def update_timeline_milestone(
    project_id: str,
    milestone_id: str,
    payload: MilestoneUpdate,
    request: Request,
) -> Milestone:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestone = timeline_store.update_milestone(
        tenant_id, project_id, milestone_id, payload
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    logger.info(
        "timeline.update",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "milestone_id": milestone_id,
        },
    )
    return milestone


@app.delete("/api/timeline/{project_id}/milestones/{milestone_id}")
async def delete_timeline_milestone(
    project_id: str, milestone_id: str, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted = timeline_store.delete_milestone(tenant_id, project_id, milestone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Milestone not found")
    logger.info(
        "timeline.delete",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "milestone_id": milestone_id,
        },
    )
    return {"deleted": True, "milestone_id": milestone_id}


@app.get("/api/timeline/{project_id}/export", response_model=TimelineExportResponse)
async def export_timeline(project_id: str, request: Request) -> TimelineExportResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestones = timeline_store.list_milestones(tenant_id, project_id)
    logger.info(
        "timeline.export",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TimelineExportResponse(
        tenant_id=tenant_id,
        project_id=project_id,
        exported_at=datetime.now(timezone.utc),
        milestones=milestones,
    )


@app.get("/api/templates", response_model=list[TemplateSummary])
async def list_templates(request: Request) -> list[TemplateSummary]:
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
    for template in templates:
        methodology = template.methodology
        summaries.append(
            TemplateSummary(
                id=template.id,
                name=template.name,
                version=template.version,
                available_versions=template.available_versions,
                summary=template.summary,
                description=template.description,
                methodology_name=str(methodology.get("name", "Methodology")),
                methodology_type=str(methodology.get("type", "custom")),
            )
        )
    return summaries


@app.get("/api/templates/{template_id}", response_model=TemplateDefinition)
async def get_template(template_id: str, request: Request) -> TemplateDefinition:
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
    template = next((item for item in templates if item.id == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.post("/api/templates/{template_id}/apply", response_model=TemplateApplyResponse)
async def apply_template(
    template_id: str, payload: TemplateApplyRequest, request: Request
) -> TemplateApplyResponse:
    session = _require_roles(
        request,
        {"PMO_ADMIN", "PM", "tenant_owner", "portfolio_admin", "project_manager"},
    )
    templates = _load_templates()
    template = next((item for item in templates if item.id == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    projects = _load_projects()
    existing_ids = {project.id for project in projects}
    base_slug = _slugify(payload.project_name) or "project"
    project_id = _unique_project_id(base_slug, existing_ids)

    project = ProjectRecord(
        id=project_id,
        name=payload.project_name,
        template_id=template.id,
        created_at=datetime.utcnow().isoformat() + "Z",
        methodology=template.methodology,
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

    return TemplateApplyResponse(project=project, template=template)


@app.post("/api/knowledge/documents", response_model=DocumentVersionResponse)
async def create_document_version(
    payload: DocumentVersionRequest, request: Request
) -> DocumentVersionResponse:
    store = _get_knowledge_store()
    record = store.create_document_version(
        project_id=payload.project_id,
        document_key=payload.document_key,
        name=payload.name,
        doc_type=payload.doc_type,
        classification=payload.classification,
        status=payload.status,
        content=payload.content,
        metadata=payload.metadata,
    )
    if payload.status.lower() == "published":
        session = _session_from_request(request) or {}
        get_audit_log_store().record_event(
            build_event(
                tenant_id=session.get("tenant_id", "unknown"),
                actor_id=session.get("subject") or "ui-user",
                actor_type="user",
                roles=session.get("roles") or [],
                action="document.published",
                resource_type="document",
                resource_id=record.document_id,
                outcome="success",
                metadata={"project_id": record.project_id},
            )
        )
    return DocumentVersionResponse(
        document_id=record.document_id,
        document_key=record.document_key,
        project_id=record.project_id,
        name=record.name,
        doc_type=record.doc_type,
        classification=record.classification,
        version=record.version,
        status=record.status,
        content=record.content,
        created_at=record.created_at.isoformat(),
        metadata=record.metadata,
    )


@app.get("/api/knowledge/documents", response_model=list[DocumentSummaryResponse])
async def list_documents(project_id: str, query: str | None = None) -> list[DocumentSummaryResponse]:
    store = _get_knowledge_store()
    records = store.list_documents(project_id=project_id, query=query)
    return [
        DocumentSummaryResponse(
            document_id=record.document_id,
            document_key=record.document_key,
            project_id=record.project_id,
            name=record.name,
            doc_type=record.doc_type,
            classification=record.classification,
            latest_version=record.latest_version,
            latest_status=record.latest_status,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )
        for record in records
    ]


@app.get("/api/knowledge/documents/{document_id}/versions", response_model=list[DocumentVersionResponse])
async def list_document_versions(document_id: str) -> list[DocumentVersionResponse]:
    store = _get_knowledge_store()
    records = store.list_versions(document_id=document_id)
    return [
        DocumentVersionResponse(
            document_id=record.document_id,
            document_key=record.document_key,
            project_id=record.project_id,
            name=record.name,
            doc_type=record.doc_type,
            classification=record.classification,
            version=record.version,
            status=record.status,
            content=record.content,
            created_at=record.created_at.isoformat(),
            metadata=record.metadata,
        )
        for record in records
    ]


@app.post("/api/knowledge/lessons", response_model=LessonResponse)
async def create_lesson(payload: LessonRequest) -> LessonResponse:
    store = _get_knowledge_store()
    record = store.create_lesson(
        project_id=payload.project_id,
        stage_id=payload.stage_id,
        stage_name=payload.stage_name,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        topics=payload.topics,
    )
    return LessonResponse(
        lesson_id=record.lesson_id,
        project_id=record.project_id,
        stage_id=record.stage_id,
        stage_name=record.stage_name,
        title=record.title,
        description=record.description,
        tags=record.tags,
        topics=record.topics,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


@app.put("/api/knowledge/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(lesson_id: str, payload: LessonRequest) -> LessonResponse:
    store = _get_knowledge_store()
    record = store.update_lesson(
        lesson_id=lesson_id,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        topics=payload.topics,
        stage_id=payload.stage_id,
        stage_name=payload.stage_name,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return LessonResponse(
        lesson_id=record.lesson_id,
        project_id=record.project_id,
        stage_id=record.stage_id,
        stage_name=record.stage_name,
        title=record.title,
        description=record.description,
        tags=record.tags,
        topics=record.topics,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


@app.delete("/api/knowledge/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str) -> dict[str, Any]:
    store = _get_knowledge_store()
    deleted = store.delete_lesson(lesson_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"status": "deleted", "lesson_id": lesson_id}


@app.get("/api/knowledge/lessons", response_model=list[LessonResponse])
async def list_lessons(
    project_id: str,
    query: str | None = None,
    tags: str | None = None,
    topics: str | None = None,
) -> list[LessonResponse]:
    store = _get_knowledge_store()
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    topic_list = [topic.strip() for topic in topics.split(",")] if topics else None
    records = store.list_lessons(
        project_id=project_id,
        query=query,
        tags=[tag for tag in (tag_list or []) if tag],
        topics=[topic for topic in (topic_list or []) if topic],
    )
    return [
        LessonResponse(
            lesson_id=record.lesson_id,
            project_id=record.project_id,
            stage_id=record.stage_id,
            stage_name=record.stage_name,
            title=record.title,
            description=record.description,
            tags=record.tags,
            topics=record.topics,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )
        for record in records
    ]


@app.post("/api/knowledge/lessons/recommendations", response_model=list[LessonResponse])
async def recommend_lessons(payload: LessonRecommendationRequest) -> list[LessonResponse]:
    store = _get_knowledge_store()
    records = store.recommend_lessons(
        project_id=payload.project_id,
        tags=payload.tags,
        topics=payload.topics,
        limit=payload.limit,
    )
    return [
        LessonResponse(
            lesson_id=record.lesson_id,
            project_id=record.project_id,
            stage_id=record.stage_id,
            stage_name=record.stage_name,
            title=record.title,
            description=record.description,
            tags=record.tags,
            topics=record.topics,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )
        for record in records
    ]


@app.post("/api/document-canvas/documents")
async def create_document_canvas_document(
    payload: DocumentCanvasRequest, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.create_document(payload.model_dump(), headers=headers)
    if response.status_code == 403:
        logger.info(
            "document_canvas.create",
            extra={
                "tenant_id": session.get("tenant_id"),
                "project_id": request.query_params.get("project_id"),
            },
        )
        return JSONResponse(status_code=403, content=response.json())
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.create",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
            "document_id": body.get("document_id"),
        },
    )
    return body


@app.get("/api/document-canvas/documents")
async def list_document_canvas_documents(request: Request) -> list[dict[str, Any]]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.list_documents(headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.list",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
        },
    )
    return body


@app.get("/api/document-canvas/documents/{document_id}")
async def get_document_canvas_document(
    document_id: str, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.get_document(document_id, headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.get",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
            "document_id": document_id,
        },
    )
    return body


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/workspace")
async def workspace_shell() -> HTMLResponse:
    html = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>PPM Workspace</title>
        <link rel="stylesheet" href="/static/styles.css" />
        <link rel="stylesheet" href="/static/workspace.css" />
      </head>
      <body>
        <div class="app">
          <p>Loading workspace...</p>
        </div>
        <script src="/static/workspace.js"></script>
      </body>
    </html>
    """
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)
