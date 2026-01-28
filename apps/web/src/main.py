from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
if str(OBSERVABILITY_ROOT) not in sys.path:
    sys.path.insert(0, str(OBSERVABILITY_ROOT))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from knowledge_store import KnowledgeStore  # noqa: E402

WEB_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = WEB_ROOT / "static"
DATA_DIR = WEB_ROOT / "data"
TEMPLATES_PATH = DATA_DIR / "templates.json"
PROJECTS_PATH = DATA_DIR / "projects.json"
KNOWLEDGE_DB_PATH = DATA_DIR / "knowledge.db"

SESSION_COOKIE = "ppm_session"
SESSION_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(title="PPM Web Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
configure_tracing("web-ui")
configure_metrics("web-ui")
app.add_middleware(TraceMiddleware, service_name="web-ui")
app.add_middleware(RequestMetricsMiddleware, service_name="web-ui")

knowledge_store: KnowledgeStore | None = None


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


@app.on_event("startup")
async def startup() -> None:
    global knowledge_store
    knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)


def _get_knowledge_store() -> KnowledgeStore:
    global knowledge_store
    if knowledge_store is None:
        knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)
    return knowledge_store


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
        return None
    return SESSION_STORE.get(session_id)


def _require_session(request: Request) -> dict[str, Any]:
    session = _session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
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
                    "roles": session.get("roles") or ["portfolio_admin"],
                },
            },
        )
        response.raise_for_status()
        return response.json()


@app.get("/api/templates", response_model=list[TemplateSummary])
async def list_templates() -> list[TemplateSummary]:
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
async def get_template(template_id: str) -> TemplateDefinition:
    templates = _load_templates()
    template = next((item for item in templates if item.id == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.post("/api/templates/{template_id}/apply", response_model=TemplateApplyResponse)
async def apply_template(template_id: str, payload: TemplateApplyRequest) -> TemplateApplyResponse:
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

    return TemplateApplyResponse(project=project, template=template)


@app.post("/api/knowledge/documents", response_model=DocumentVersionResponse)
async def create_document_version(payload: DocumentVersionRequest) -> DocumentVersionResponse:
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


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)
