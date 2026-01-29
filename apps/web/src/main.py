from __future__ import annotations

import base64
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from jwt import InvalidTokenError

REPO_ROOT = Path(__file__).resolve().parents[3]
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
LLM_ROOT = REPO_ROOT / "packages" / "llm" / "src"
for root in (OBSERVABILITY_ROOT, SECURITY_ROOT, LLM_ROOT):
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
    OpenRef,
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
from spreadsheet_models import (  # noqa: E402
    ColumnCreate,
    DeleteResult,
    ImportResult,
    Row,
    RowCreate,
    RowUpdate,
    Sheet,
    SheetCreate,
    SheetDetail,
)
from timeline_store import TimelineStore  # noqa: E402
from spreadsheet_store import SpreadsheetStore  # noqa: E402
from tree_models import (  # noqa: E402
    TreeDeleteResult,
    TreeExportResponse,
    TreeListResponse,
    TreeMoveRequest,
    TreeNode,
    TreeNodeCreate,
    TreeNodeUpdate,
)
from tree_store import TreeStore  # noqa: E402
from analytics_proxy import AnalyticsServiceClient  # noqa: E402
from connector_hub_proxy import ConnectorHubClient  # noqa: E402
from lineage_proxy import LineageServiceClient  # noqa: E402
from document_proxy import DocumentServiceClient, build_forward_headers  # noqa: E402
from orchestrator_proxy import OrchestratorProxyClient  # noqa: E402
from template_models import (  # noqa: E402
    Template as DeliverableTemplate,
    TemplateInstantiateRequest,
    TemplateInstantiateResponse,
    TemplateSummary as DeliverableTemplateSummary,
    TemplateType,
    build_placeholder_context,
    render_template_value,
)
from template_registry import (  # noqa: E402
    get_template as get_deliverable_template,
    list_templates as list_deliverable_templates,
)
from agent_registry import load_agent_registry  # noqa: E402
from agent_settings_models import (  # noqa: E402
    AgentConfigUpdate,
    AgentProjectEntry,
)
from agent_settings_store import AgentSettingsStore  # noqa: E402
from oidc_client import OIDCClient  # noqa: E402
from security.prompt_safety import evaluate_prompt  # noqa: E402
from security.secrets import resolve_secret  # noqa: E402
from llm.client import LLMClient, LLMProviderError  # noqa: E402

WEB_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = WEB_ROOT / "static"
DATA_DIR = WEB_ROOT / "data"
STORAGE_DIR = WEB_ROOT / "storage"
TEMPLATES_PATH = DATA_DIR / "templates.json"
PROJECTS_PATH = DATA_DIR / "projects.json"
KNOWLEDGE_DB_PATH = DATA_DIR / "knowledge.db"
WORKSPACE_STATE_PATH = STORAGE_DIR / "workspace_state.json"
TIMELINES_PATH = STORAGE_DIR / "timelines.json"
SPREADSHEETS_PATH = STORAGE_DIR / "spreadsheets.json"
TREES_PATH = STORAGE_DIR / "trees.json"
AGENT_SETTINGS_PATH = STORAGE_DIR / "agent_settings.json"
CONNECTOR_REGISTRY_PATH = REPO_ROOT / "connectors" / "registry" / "connectors.json"

SESSION_COOKIE = "ppm_session"
STATE_COOKIE = "ppm_oidc_state"
SESSION_SIGNING_ALGORITHM = "HS256"
OIDC_HTTP_TRANSPORT: httpx.BaseTransport | None = None

app = FastAPI(title="PPM Web Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
configure_tracing("web-ui")
configure_metrics("web-ui")
app.add_middleware(TraceMiddleware, service_name="web-ui")
app.add_middleware(RequestMetricsMiddleware, service_name="web-ui")

knowledge_store: KnowledgeStore | None = None
workspace_state_store = WorkspaceStateStore(WORKSPACE_STATE_PATH)
timeline_store = TimelineStore(TIMELINES_PATH)
spreadsheet_store = SpreadsheetStore(SPREADSHEETS_PATH)
tree_store = TreeStore(TREES_PATH)
agent_settings_store = AgentSettingsStore(AGENT_SETTINGS_PATH)
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


class AssistantSendRequest(BaseModel):
    project_id: str
    message: str


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
    last_opened_document_id: str | None = None
    last_opened_sheet_id: str | None = None
    last_opened_milestone_id: str | None = None
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


class ConnectorInstanceCreate(BaseModel):
    connector_type_id: str
    version: str
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorInstanceUpdate(BaseModel):
    version: str | None = None
    enabled: bool | None = None
    health_status: str | None = Field(
        default=None, pattern="^(healthy|degraded|unhealthy|unknown)$"
    )


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
    template_version: str = "1.0"
    created_at: str
    methodology: dict[str, Any]
    agent_config: TemplateAgentConfig
    connector_config: TemplateConnectorConfig
    initial_tabs: list[TemplateTab]
    dashboards: list[TemplateTab]


class TemplateApplyRequest(BaseModel):
    project_name: str
    version: str | None = None


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


class DashboardWhatIfRequest(BaseModel):
    scenario: str
    adjustments: dict[str, Any] = {}


class AssistantPrerequisite(BaseModel):
    activity_id: str
    activity_name: str
    stage_id: str
    stage_name: str
    status: str


class AssistantSuggestionRequest(BaseModel):
    project_id: str
    activity_id: str | None = None
    stage_id: str | None = None
    activity_name: str | None = None
    stage_name: str | None = None
    activity_status: str | None = None
    canvas_type: CanvasTab | None = None
    incomplete_prerequisites: list[AssistantPrerequisite] = []


class AssistantSuggestion(BaseModel):
    id: str
    label: str
    category: str
    priority: str
    icon: str | None = None
    action_type: str
    payload: dict[str, Any]
    enabled: bool = True
    description: str | None = None


class AssistantSuggestionResponse(BaseModel):
    context: dict[str, Any]
    suggestions: list[AssistantSuggestion]
    generated_by: str


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


def _analytics_client() -> AnalyticsServiceClient:
    return AnalyticsServiceClient()


def _lineage_client() -> LineageServiceClient:
    return LineageServiceClient()


def _orchestrator_client() -> OrchestratorProxyClient:
    return OrchestratorProxyClient()


def _connector_hub_client() -> ConnectorHubClient:
    return ConnectorHubClient()


def _raise_upstream_error(response: httpx.Response) -> None:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise HTTPException(status_code=response.status_code, detail=detail)


def _passthrough_response(response: httpx.Response) -> Response:
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )


def _format_credentials(connector_id: str, fields: list[str]) -> list[str]:
    return [f"{connector_id.upper()}_{field.upper()}" for field in fields]


def _load_connector_manifest(manifest_path: str) -> dict[str, Any] | None:
    manifest_file = REPO_ROOT / manifest_path
    if not manifest_file.exists():
        return None
    try:
        with manifest_file.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _enrich_connector_types(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for entry in entries:
        connector_id = entry.get("id")
        if not connector_id:
            continue
        record = {
            "id": connector_id,
            "name": entry.get("name", connector_id),
            "status": entry.get("status", "unknown"),
            "certification": entry.get("certification", "unknown"),
            "manifest_path": entry.get("manifest_path"),
        }
        credentials_required: list[str] | None = None
        manifest_path = entry.get("manifest_path")
        if manifest_path:
            manifest = _load_connector_manifest(manifest_path)
            if manifest:
                record["default_version"] = manifest.get("version")
                auth = manifest.get("auth") or {}
                fields = auth.get("fields")
                if isinstance(fields, list) and fields:
                    credentials_required = _format_credentials(connector_id, fields)
        if not credentials_required:
            if connector_id == "jira":
                credentials_required = [
                    "JIRA_INSTANCE_URL",
                    "JIRA_EMAIL",
                    "JIRA_API_TOKEN",
                ]
            else:
                record["credentials_note"] = "See docs for required credentials."
        if credentials_required:
            record["credentials_required"] = credentials_required
        enriched.append(record)
    return enriched


def _load_connector_registry() -> list[dict[str, Any]]:
    try:
        with CONNECTOR_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        logger.error(
            "connector_gallery.registry_read_failed", extra={"error": str(exc)}
        )
        return []
    if not isinstance(payload, list):
        return []
    return _enrich_connector_types(payload)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _oidc_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing OIDC setting: {name}")
    return value


def _cookie_secure() -> bool:
    override = os.getenv("SESSION_COOKIE_SECURE")
    if override is not None:
        return override.lower() in {"1", "true", "yes"}
    environment = os.getenv("ENVIRONMENT", "development").lower()
    return environment not in {"dev", "development", "local", "test"}


def _session_signing_key() -> str:
    key = resolve_secret(os.getenv("AUTH_SESSION_SIGNING_KEY"))
    if key:
        return key
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in {"dev", "development", "local", "test"}:
        return "dev-session-key"
    raise HTTPException(status_code=500, detail="Missing AUTH_SESSION_SIGNING_KEY")


def _encode_cookie(payload: dict[str, Any], ttl_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    claims = payload | {
        "iat": int(now.timestamp()),
        "exp": int((now.timestamp()) + ttl_seconds),
    }
    return jwt.encode(claims, _session_signing_key(), algorithm=SESSION_SIGNING_ALGORITHM)


def _decode_cookie(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            _session_signing_key(),
            algorithms=[SESSION_SIGNING_ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
    except InvalidTokenError:
        return None


def _random_token_urlsafe(length_bytes: int) -> str:
    return base64.urlsafe_b64encode(os.urandom(length_bytes)).rstrip(b"=").decode("utf-8")


def _random_token_hex(length_bytes: int) -> str:
    return os.urandom(length_bytes).hex()


def _session_from_request(request: Request) -> dict[str, Any] | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return _dev_session()
    payload = _decode_cookie(session_id)
    if payload:
        return payload
    return _dev_session()


def _require_session(request: Request) -> dict[str, Any]:
    session = _session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def _tenant_id_from_request(request: Request, session: dict[str, Any]) -> str | None:
    auth = getattr(request.state, "auth", None)
    tenant_id = getattr(auth, "tenant_id", None) if auth else None
    return tenant_id or session.get("tenant_id")


def _assistant_context(
    tenant_id: str,
    project_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    state = workspace_state_store.get_or_create(tenant_id, project_id)
    context: dict[str, Any] = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "correlation_id": correlation_id,
        "methodology": state.methodology,
        "current_stage_id": state.current_stage_id,
        "current_activity_id": state.current_activity_id,
        "current_canvas_tab": state.current_canvas_tab,
    }
    open_ref: dict[str, str] = {}
    if state.last_opened_document_id:
        open_ref["document_id"] = state.last_opened_document_id
    if state.last_opened_sheet_id:
        open_ref["sheet_id"] = state.last_opened_sheet_id
    if state.last_opened_milestone_id:
        open_ref["milestone_id"] = state.last_opened_milestone_id
    if open_ref:
        context["open_ref"] = open_ref
    try:
        registry = load_agent_registry()
        settings = agent_settings_store.ensure_project_settings(tenant_id, project_id, registry)
        context["enabled_agent_ids"] = [
            agent_id for agent_id, entry in settings.agents.items() if entry.enabled
        ]
        context["agent_config_by_id"] = {
            agent_id: entry.config for agent_id, entry in settings.agents.items()
        }
    except Exception:  # pragma: no cover - defensive
        logger.exception("Unable to attach agent settings context")
    return context


def _find_activity(methodology_map: dict[str, Any], activity_id: str) -> dict[str, Any] | None:
    for stage in methodology_map.get("stages", []):
        for activity in stage.get("activities", []):
            if activity.get("id") == activity_id:
                return activity
    return None


def _fallback_suggestions(
    payload: AssistantSuggestionRequest,
    state: WorkspaceState,
    methodology_map: dict[str, Any],
) -> list[AssistantSuggestion]:
    suggestions: list[AssistantSuggestion] = []
    for prereq in payload.incomplete_prerequisites[:3]:
        suggestions.append(
            AssistantSuggestion(
                id=f"prereq-{prereq.activity_id}",
                label=f"Go to {prereq.activity_name}",
                category="navigate",
                priority="high",
                icon="→",
                action_type="open_activity",
                payload={
                    "type": "open_activity",
                    "activityId": prereq.activity_id,
                    "stageId": prereq.stage_id,
                },
                description=f"Complete prerequisite {prereq.activity_name}.",
            )
        )

    if payload.activity_id and payload.activity_name:
        suggestions.append(
            AssistantSuggestion(
                id=f"continue-{payload.activity_id}",
                label=f"Continue {payload.activity_name}",
                category="create",
                priority="high",
                icon="▶",
                action_type="open_activity",
                payload={"type": "open_activity", "activityId": payload.activity_id},
                description="Resume work on the current activity.",
            )
        )

    next_activity_id = next_required_activity(methodology_map, state)
    if next_activity_id and next_activity_id != payload.activity_id:
        next_activity = _find_activity(methodology_map, next_activity_id)
        suggestions.append(
            AssistantSuggestion(
                id=f"next-{next_activity_id}",
                label=f"Open {next_activity.get('name', 'next activity')}",
                category="navigate",
                priority="medium",
                icon="✨",
                action_type="open_activity",
                payload={"type": "open_activity", "activityId": next_activity_id},
                description="Move to the next required activity.",
            )
        )

    suggestions.append(
        AssistantSuggestion(
            id="open-dashboard",
            label="View project dashboard",
            category="analyse",
            priority="low",
            icon="📈",
            action_type="open_dashboard",
            payload={"type": "open_dashboard"},
            description="Review project health and metrics.",
        )
    )
    return suggestions


async def _llm_suggestions(
    payload: AssistantSuggestionRequest,
    context: dict[str, Any],
    methodology_map: dict[str, Any],
) -> list[AssistantSuggestion]:
    llm = LLMClient()
    system_prompt = (
        "You are a PMO assistant generating next best action suggestions. "
        "Return JSON with a top-level key 'suggestions' that is a list of objects. "
        "Each suggestion must include: label, category, priority, action_type, payload, description, icon. "
        "Use action_type values from: open_activity, open_artifact, open_dashboard, generate_template, "
        "show_prerequisites, complete_activity, custom. "
        "Use category values from: create, review, approve, analyse, navigate. "
        "Use priority values from: high, medium, low. "
        "Payload should include a 'type' field matching action_type and any required ids."
    )
    user_prompt = json.dumps(
        {
            "context": context,
            "activity": payload.model_dump(),
            "activities": [
                {
                    "id": activity.get("id"),
                    "name": activity.get("name"),
                    "status": activity.get("status"),
                    "stage_id": stage.get("id"),
                }
                for stage in methodology_map.get("stages", [])
                for activity in stage.get("activities", [])
            ],
        },
        indent=2,
    )

    response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response was not JSON") from exc

    suggestions: list[AssistantSuggestion] = []
    for item in data.get("suggestions", []):
        if not isinstance(item, dict):
            continue
        try:
            suggestion = AssistantSuggestion(
                id=item.get("id") or f"llm-{_random_token_hex(4)}",
                label=str(item.get("label", "")),
                category=str(item.get("category", "analyse")),
                priority=str(item.get("priority", "medium")),
                icon=item.get("icon"),
                action_type=str(item.get("action_type", "custom")),
                payload=item.get("payload") or {},
                description=item.get("description"),
                enabled=bool(item.get("enabled", True)),
            )
        except Exception:  # pragma: no cover - defensive parsing
            continue
        suggestions.append(suggestion)
    return suggestions


def _template_context(
    *,
    project_id: str,
    tenant_id: str,
    session: dict[str, Any],
    parameters: dict[str, Any] | None,
) -> dict[str, Any]:
    user = (parameters or {}).get("user") or session.get("subject") or "unknown"
    return build_placeholder_context(
        project_id=project_id,
        tenant_id=tenant_id,
        user=user,
        parameters=parameters,
    )


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


def _roles_from_request(request: Request, session: dict[str, Any]) -> set[str]:
    auth = getattr(request.state, "auth", None)
    roles = getattr(auth, "roles", None) if auth else None
    if roles is None:
        roles = session.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return {role for role in roles if role}


def _is_agent_admin(request: Request, session: dict[str, Any]) -> bool:
    roles = _roles_from_request(request, session)
    return bool(roles.intersection({"tenant_owner", "portfolio_admin"}))


def _oidc_enabled() -> bool:
    return bool(
        os.getenv("OIDC_ISSUER_URL")
        and os.getenv("OIDC_CLIENT_ID")
        and os.getenv("OIDC_REDIRECT_URI")
    )


def _legacy_oidc_enabled() -> bool:
    return bool(
        os.getenv("OIDC_AUTH_URL")
        and os.getenv("OIDC_TOKEN_URL")
        and os.getenv("OIDC_JWKS_URL")
        and os.getenv("OIDC_CLIENT_ID")
        and os.getenv("OIDC_REDIRECT_URI")
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


def _select_project_template(
    template_id: str, version: str | None = None
) -> TemplateDefinition | None:
    templates = [item for item in _load_templates() if item.id == template_id]
    if not templates:
        return None
    if version is None:
        return templates[0]
    exact = next((item for item in templates if item.version == version), None)
    if exact:
        return exact
    fallback = templates[0]
    if version in fallback.available_versions:
        return fallback.model_copy(update={"version": version})
    return None


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
        last_opened_document_id=state.last_opened_document_id,
        last_opened_sheet_id=state.last_opened_sheet_id,
        last_opened_milestone_id=state.last_opened_milestone_id,
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
        suffix = _random_token_hex(2)
        candidate = f"{base}-{suffix}"
    return candidate


def _oidc_client() -> OIDCClient:
    issuer_url = _oidc_required("OIDC_ISSUER_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    client_secret = resolve_secret(os.getenv("OIDC_CLIENT_SECRET"))
    redirect_uri = _oidc_required("OIDC_REDIRECT_URI")
    scope = os.getenv("OIDC_SCOPE", "openid profile email")
    return OIDCClient(
        issuer_url=issuer_url,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        transport=OIDC_HTTP_TRANSPORT,
    )


async def _exchange_code_for_token(code: str) -> dict[str, Any]:
    token_url = _oidc_required("OIDC_TOKEN_URL")
    client_id = _oidc_required("OIDC_CLIENT_ID")
    client_secret = resolve_secret(os.getenv("OIDC_CLIENT_SECRET"))
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
    audience = os.getenv("OIDC_AUDIENCE")
    issuer = os.getenv("OIDC_ISSUER")

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
        api_gateway_url=os.getenv("API_GATEWAY_URL", "http://api-gateway:8000"),
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
async def login(request: Request) -> RedirectResponse:
    if not _oidc_enabled():
        if _legacy_oidc_enabled():
            auth_url = _oidc_required("OIDC_AUTH_URL")
            client_id = _oidc_required("OIDC_CLIENT_ID")
            redirect_uri = _oidc_required("OIDC_REDIRECT_URI")
            state = _random_token_urlsafe(16)
            nonce = _random_token_urlsafe(16)
            project_id = request.query_params.get("project_id")
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
                STATE_COOKIE,
                _encode_cookie({"state": state, "nonce": nonce, "project_id": project_id}, 600),
                httponly=True,
                secure=_cookie_secure(),
                samesite="lax",
            )
            return response

        auth_dev_mode = os.getenv("AUTH_DEV_MODE", "false").lower() in {"1", "true", "yes"}
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if auth_dev_mode and environment in {"dev", "development", "local", "test"}:
            return RedirectResponse(url="/workspace")
        raise HTTPException(status_code=500, detail="OIDC not configured")

    client = _oidc_client()
    discovery = await client.discover()
    state = _random_token_urlsafe(16)
    nonce = _random_token_urlsafe(16)
    project_id = request.query_params.get("project_id")

    params = {
        "client_id": client.client_id,
        "response_type": "code",
        "scope": client.scope,
        "redirect_uri": client.redirect_uri,
        "state": state,
        "nonce": nonce,
    }
    response = RedirectResponse(url=f"{discovery.authorization_endpoint}?{urlencode(params)}")
    response.set_cookie(
        STATE_COOKIE,
        _encode_cookie({"state": state, "nonce": nonce, "project_id": project_id}, 600),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    return response


@app.get("/oidc/callback")
async def oidc_callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OIDC callback parameters")

    state_cookie = request.cookies.get(STATE_COOKIE)
    state_payload = _decode_cookie(state_cookie) if state_cookie else None
    if not state_payload or state_payload.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid login state")

    if _oidc_enabled():
        client = _oidc_client()
        token_response = await client.exchange_code(code)
    elif _legacy_oidc_enabled():
        token_response = await _exchange_code_for_token(code)
        client = None
    else:
        raise HTTPException(status_code=500, detail="OIDC not configured")

    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")
    if not id_token or not access_token:
        raise HTTPException(status_code=401, detail="OIDC token response missing tokens")

    if client:
        claims = await client.verify_id_token(id_token, state_payload.get("nonce"))
    else:
        claims = await _decode_id_token(id_token)

    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    roles_claim = os.getenv("OIDC_ROLES_CLAIM", "roles")
    tenant_id = claims.get(tenant_claim)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="OIDC token missing tenant claim")

    roles = claims.get(roles_claim) or []
    if isinstance(roles, str):
        roles = [roles]

    session_payload = {
        "access_token": access_token,
        "id_token": id_token,
        "tenant_id": tenant_id,
        "subject": claims.get("sub"),
        "roles": roles,
    }
    response = RedirectResponse(
        url=f"/workspace?project_id={state_payload.get('project_id')}"
        if state_payload.get("project_id")
        else "/workspace"
    )
    response.set_cookie(
        SESSION_COOKIE,
        _encode_cookie(session_payload, 8 * 60 * 60),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    response.delete_cookie(STATE_COOKIE)
    return response


@app.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    return await oidc_callback(request)


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    session = _session_from_request(request) or {}
    response = RedirectResponse(url="/")
    discovery = None
    if _oidc_enabled():
        client = _oidc_client()
        discovery = await client.discover()
    if discovery and discovery.end_session_endpoint and session.get("id_token"):
        params = {"id_token_hint": session["id_token"]}
        response = RedirectResponse(
            url=f"{discovery.end_session_endpoint}?{urlencode(params)}"
        )
    elif _legacy_oidc_enabled():
        logout_url = os.getenv("OIDC_LOGOUT_URL")
        if logout_url:
            response = RedirectResponse(url=logout_url)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(STATE_COOKIE)
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
    open_ref = updates.pop("open_ref", None)
    if open_ref:
        open_ref = OpenRef.model_validate(open_ref)
        if open_ref.document_id:
            updates["last_opened_document_id"] = open_ref.document_id
        if open_ref.sheet_id:
            updates["last_opened_sheet_id"] = open_ref.sheet_id
        if open_ref.milestone_id:
            updates["last_opened_milestone_id"] = open_ref.milestone_id
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


@app.post(
    "/api/templates/{template_id}/instantiate",
    response_model=TemplateInstantiateResponse,
)
async def instantiate_template(
    template_id: str, payload: TemplateInstantiateRequest, request: Request
) -> TemplateInstantiateResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    template = get_deliverable_template(template_id)
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
        classification = context.get("classification") or template.defaults.classification
        retention_days = int(
            context.get("retention_days") or template.defaults.retention_days
        )
        payload_model = template.payload
        name = render_template_value(payload_model.name_template, context)
        content = render_template_value(payload_model.content_template, context)
        metadata = (
            render_template_value(payload_model.metadata_template, context)
            if payload_model.metadata_template
            else {}
        )
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
        return TemplateInstantiateResponse(
            created_type=TemplateType.document,
            document_id=body.get("document_id"),
            name=body.get("name"),
            advisories=body.get("advisories"),
        )
    if template.type == TemplateType.spreadsheet:
        payload_model = template.payload
        sheet_name = render_template_value(payload_model.sheet_name_template, context)
        columns = [
            ColumnCreate(name=column.name, type=column.type, required=column.required)
            for column in payload_model.columns
        ]
        try:
            sheet = spreadsheet_store.create_sheet(
                tenant_id,
                payload.project_id,
                SheetCreate(name=sheet_name, columns=columns),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload_model.seed_rows:
            column_map = {column.name: column.column_id for column in sheet.columns}
            for row in payload_model.seed_rows:
                rendered = render_template_value(row.values, context)
                values = {
                    column_map[name]: value
                    for name, value in rendered.items()
                    if name in column_map
                }
                try:
                    spreadsheet_store.add_row(
                        tenant_id,
                        payload.project_id,
                        sheet.sheet_id,
                        RowCreate(values=values),
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
        return TemplateInstantiateResponse(
            created_type=TemplateType.spreadsheet,
            sheet_id=sheet.sheet_id,
            sheet_name=sheet.name,
        )
    raise HTTPException(status_code=400, detail="Unsupported template type")


@app.get("/api/agent-gallery/agents")
async def list_agent_registry(request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    logger.info(
        "agent_gallery.registry.list",
        extra={"tenant_id": tenant_id, "project_id": None, "agent_id": None},
    )
    return JSONResponse(status_code=200, content=[entry.model_dump() for entry in registry])


@app.get("/api/agent-gallery/{project_id}")
async def get_project_agent_settings(project_id: str, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    registry = load_agent_registry()
    settings = agent_settings_store.ensure_project_settings(tenant_id, project_id, registry)
    logger.info(
        "agent_gallery.project.get",
        extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": None},
    )
    response_agents = []
    for entry in registry:
        stored = settings.agents.get(entry.agent_id)
        if not stored:
            continue
        response_agents.append(
            AgentProjectEntry(
                agent_id=entry.agent_id,
                name=entry.name,
                category=entry.category,
                description=entry.description,
                outputs=entry.outputs,
                required=entry.required,
                enabled=stored.enabled,
                config=stored.config,
            ).model_dump()
        )
    return JSONResponse(
        status_code=200,
        content={
            "project_id": project_id,
            "tenant_id": tenant_id,
            "agents": response_agents,
        },
    )


@app.patch("/api/agent-gallery/{project_id}/agents/{agent_id}")
async def update_project_agent_settings(
    project_id: str,
    agent_id: str,
    payload: AgentConfigUpdate,
    request: Request,
) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if not _is_agent_admin(request, session):
        raise HTTPException(status_code=403, detail="Agent gallery is read-only")
    registry = load_agent_registry()
    registry_entry = next((entry for entry in registry if entry.agent_id == agent_id), None)
    if not registry_entry:
        raise HTTPException(status_code=404, detail="Agent not found")
    if payload.enabled is False and registry_entry.required:
        raise HTTPException(status_code=422, detail="Required agents cannot be disabled")
    settings = agent_settings_store.ensure_project_settings(tenant_id, project_id, registry)
    if agent_id not in settings.agents:
        raise HTTPException(status_code=404, detail="Agent not configured")
    try:
        updated = agent_settings_store.update_agent_settings(
            tenant_id,
            project_id,
            agent_id,
            enabled=payload.enabled,
            config=payload.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "agent_gallery.project.patch",
        extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": agent_id},
    )
    response = AgentProjectEntry(
        agent_id=registry_entry.agent_id,
        name=registry_entry.name,
        category=registry_entry.category,
        description=registry_entry.description,
        outputs=registry_entry.outputs,
        required=registry_entry.required,
        enabled=updated.enabled,
        config=updated.config,
    )
    return JSONResponse(status_code=200, content=response.model_dump())


@app.post("/api/agent-gallery/{project_id}/reset-defaults")
async def reset_project_agent_settings(project_id: str, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if not _is_agent_admin(request, session):
        raise HTTPException(status_code=403, detail="Agent gallery is read-only")
    registry = load_agent_registry()
    settings = agent_settings_store.reset_project_defaults(tenant_id, project_id, registry)
    logger.info(
        "agent_gallery.project.reset",
        extra={"tenant_id": tenant_id, "project_id": project_id, "agent_id": None},
    )
    response_agents = []
    for entry in registry:
        stored = settings.agents.get(entry.agent_id)
        if not stored:
            continue
        response_agents.append(
            AgentProjectEntry(
                agent_id=entry.agent_id,
                name=entry.name,
                category=entry.category,
                description=entry.description,
                outputs=entry.outputs,
                required=entry.required,
                enabled=stored.enabled,
                config=stored.config,
            ).model_dump()
        )
    return JSONResponse(
        status_code=200,
        content={
            "project_id": project_id,
            "tenant_id": tenant_id,
            "agents": response_agents,
        },
    )


@app.post("/api/assistant/send")
async def send_assistant_message(payload: AssistantSendRequest, request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    prompt_result = evaluate_prompt(payload.message)
    if prompt_result.decision == "deny":
        logger.warning(
            "assistant_prompt_blocked",
            extra={"tenant_id": tenant_id, "reasons": prompt_result.reasons},
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Prompt rejected due to unsafe content.",
                "reasons": prompt_result.reasons,
            },
        )
    correlation_id = f"corr-{_random_token_hex(8)}"
    context = _assistant_context(tenant_id, payload.project_id, correlation_id)
    headers = build_forward_headers(request, session)
    headers["X-Tenant-ID"] = tenant_id
    try:
        response = await _orchestrator_client().send_query(
            query=prompt_result.sanitized_text, context=context, headers=headers
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"detail": "upstream timeout", "correlation_id": correlation_id},
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            return JSONResponse(
                status_code=response.status_code,
                content={"detail": response.text, "correlation_id": correlation_id},
            )
        if isinstance(detail, dict):
            detail["correlation_id"] = correlation_id
            return JSONResponse(status_code=response.status_code, content=detail)
        return JSONResponse(
            status_code=response.status_code,
            content={"detail": detail, "correlation_id": correlation_id},
        )

    try:
        response_payload: Any = response.json()
    except ValueError:
        response_payload = response.text
    warnings = prompt_result.reasons if prompt_result.decision == "allow_with_warning" else []
    return JSONResponse(
        status_code=200,
        content={
            "tenant_id": tenant_id,
            "project_id": payload.project_id,
            "correlation_id": correlation_id,
            "response": response_payload,
            "prompt_safety_warning": warnings,
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.post("/api/assistant/suggestions", response_model=AssistantSuggestionResponse)
async def generate_assistant_suggestions(
    payload: AssistantSuggestionRequest, request: Request
) -> AssistantSuggestionResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")

    state = workspace_state_store.get_or_create(tenant_id, payload.project_id)
    methodology_map = get_methodology_map(state.methodology)
    correlation_id = f"corr-{_random_token_hex(8)}"
    context = _assistant_context(tenant_id, payload.project_id, correlation_id)
    context.update(
        {
            "activity_id": payload.activity_id,
            "stage_id": payload.stage_id,
            "activity_name": payload.activity_name,
            "stage_name": payload.stage_name,
            "activity_status": payload.activity_status,
            "canvas_type": payload.canvas_type,
            "incomplete_prerequisites": [
                prereq.model_dump() for prereq in payload.incomplete_prerequisites
            ],
        }
    )

    suggestions: list[AssistantSuggestion] = []
    generated_by = "heuristic"
    try:
        suggestions = await _llm_suggestions(payload, context, methodology_map)
        if suggestions:
            generated_by = "llm"
    except (LLMProviderError, ValueError):
        suggestions = []

    if not suggestions:
        suggestions = _fallback_suggestions(payload, state, methodology_map)

    return AssistantSuggestionResponse(
        context=context,
        suggestions=suggestions,
        generated_by=generated_by,
    )


@app.get("/api/tree/{project_id}", response_model=TreeListResponse)
async def list_tree_nodes(project_id: str, request: Request) -> TreeListResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info(
        "tree.list",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TreeListResponse(tenant_id=tenant_id, project_id=project_id, nodes=nodes)


@app.post("/api/tree/{project_id}/nodes", response_model=TreeNode)
async def create_tree_node(
    project_id: str, payload: TreeNodeCreate, request: Request
) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.create_node(tenant_id, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "tree.create",
        extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node.node_id},
    )
    return node


@app.patch("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeNode)
async def update_tree_node(
    project_id: str, node_id: str, payload: TreeNodeUpdate, request: Request
) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.update_node(tenant_id, project_id, node_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not node:
        raise HTTPException(status_code=404, detail="Tree node not found")
    logger.info(
        "tree.update",
        extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id},
    )
    return node


@app.post("/api/tree/{project_id}/nodes/{node_id}/move", response_model=TreeNode)
async def move_tree_node(
    project_id: str, node_id: str, payload: TreeMoveRequest, request: Request
) -> TreeNode:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        node = tree_store.move_node(tenant_id, project_id, node_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not node:
        raise HTTPException(status_code=404, detail="Tree node not found")
    logger.info(
        "tree.move",
        extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id},
    )
    return node


@app.delete("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeDeleteResult)
async def delete_tree_node(
    project_id: str, node_id: str, request: Request
) -> TreeDeleteResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted_count = tree_store.delete_node(tenant_id, project_id, node_id)
    logger.info(
        "tree.delete",
        extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id},
    )
    return TreeDeleteResult(deleted=deleted_count > 0, deleted_count=deleted_count)


@app.get("/api/tree/{project_id}/export", response_model=TreeExportResponse)
async def export_tree(project_id: str, request: Request) -> TreeExportResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info(
        "tree.export",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TreeExportResponse(
        tenant_id=tenant_id, project_id=project_id, exported_at=datetime.now(timezone.utc), nodes=nodes
    )


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


@app.get("/api/spreadsheets/{project_id}/sheets", response_model=list[Sheet])
async def list_spreadsheet_sheets(project_id: str, request: Request) -> list[Sheet]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    sheets = spreadsheet_store.list_sheets(tenant_id, project_id)
    logger.info(
        "spreadsheet.sheet.list",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return sheets


@app.post("/api/spreadsheets/{project_id}/sheets", response_model=Sheet)
async def create_spreadsheet_sheet(
    project_id: str, payload: SheetCreate, request: Request
) -> Sheet:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        sheet = spreadsheet_store.create_sheet(tenant_id, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "spreadsheet.sheet.create",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet.sheet_id,
        },
    )
    return sheet


@app.get(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}", response_model=SheetDetail
)
async def get_spreadsheet_sheet(
    project_id: str, sheet_id: str, request: Request
) -> SheetDetail:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    detail = spreadsheet_store.get_sheet(tenant_id, project_id, sheet_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info(
        "spreadsheet.sheet.get",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
        },
    )
    return detail


@app.post(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows", response_model=Row
)
async def add_spreadsheet_row(
    project_id: str, sheet_id: str, payload: RowCreate, request: Request
) -> Row:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        row = spreadsheet_store.add_row(tenant_id, project_id, sheet_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info(
        "spreadsheet.row.create",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
            "row_id": row.row_id,
        },
    )
    return row


@app.patch(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}",
    response_model=Row,
)
async def update_spreadsheet_row(
    project_id: str,
    sheet_id: str,
    row_id: str,
    payload: RowUpdate,
    request: Request,
) -> Row:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    try:
        row = spreadsheet_store.update_row(
            tenant_id, project_id, sheet_id, row_id, payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    logger.info(
        "spreadsheet.row.update",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
            "row_id": row_id,
        },
    )
    return row


@app.delete(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}",
    response_model=DeleteResult,
)
async def delete_spreadsheet_row(
    project_id: str, sheet_id: str, row_id: str, request: Request
) -> DeleteResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted = spreadsheet_store.delete_row(tenant_id, project_id, sheet_id, row_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Row not found")
    logger.info(
        "spreadsheet.row.delete",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
            "row_id": row_id,
        },
    )
    return DeleteResult(deleted=True, row_id=row_id)


@app.get("/api/spreadsheets/{project_id}/sheets/{sheet_id}/export.csv")
async def export_spreadsheet_csv(
    project_id: str, sheet_id: str, request: Request
) -> Response:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    csv_payload = spreadsheet_store.export_csv(tenant_id, project_id, sheet_id)
    if csv_payload is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info(
        "spreadsheet.csv.export",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
        },
    )
    return Response(content=csv_payload, media_type="text/csv")


@app.post(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}/import.csv",
    response_model=ImportResult,
)
async def import_spreadsheet_csv(
    project_id: str, sheet_id: str, request: Request
) -> ImportResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    csv_bytes = await request.body()
    if not csv_bytes:
        raise HTTPException(status_code=422, detail="CSV payload is required")
    try:
        csv_payload = csv_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8") from exc
    try:
        imported = spreadsheet_store.import_csv(
            tenant_id, project_id, sheet_id, csv_payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if imported is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    logger.info(
        "spreadsheet.csv.import",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "sheet_id": sheet_id,
        },
    )
    return ImportResult(imported=imported)


@app.get(
    "/api/templates",
    response_model=list[TemplateSummary | DeliverableTemplateSummary],
)
async def list_templates(
    request: Request,
    type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    gallery: bool | None = None,
) -> list[TemplateSummary | DeliverableTemplateSummary]:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    wants_gallery = (
        gallery is True
        or "type" in request.query_params
        or "tag" in request.query_params
        or "q" in request.query_params
    )
    if wants_gallery:
        try:
            template_type = TemplateType(type) if type else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Unsupported template type") from exc
        templates = list_deliverable_templates(
            template_type=template_type,
            tag=tag,
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


@app.get(
    "/api/templates/{template_id}",
    response_model=TemplateDefinition | DeliverableTemplate,
)
async def get_template(
    template_id: str,
    request: Request,
    gallery: bool | None = None,
    version: str | None = None,
) -> TemplateDefinition | DeliverableTemplate:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    deliverable_template = get_deliverable_template(template_id)
    if gallery is True or deliverable_template is not None:
        if not deliverable_template:
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info(
            "templates.get",
            extra={
                "tenant_id": tenant_id,
                "project_id": request.query_params.get("project_id"),
                "template_id": template_id,
            },
        )
        return deliverable_template

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


@app.post("/api/templates/{template_id}/apply", response_model=TemplateApplyResponse)
async def apply_template(
    template_id: str, payload: TemplateApplyRequest, request: Request
) -> TemplateApplyResponse:
    session = _require_roles(
        request,
        {"PMO_ADMIN", "PM", "tenant_owner", "portfolio_admin", "project_manager"},
    )
    template = _select_project_template(template_id, version=payload.version)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    selected_version = payload.version or template.version
    if selected_version not in template.available_versions:
        raise HTTPException(status_code=422, detail="Template version not available")

    projects = _load_projects()
    existing_ids = {project.id for project in projects}
    base_slug = _slugify(payload.project_name) or "project"
    project_id = _unique_project_id(base_slug, existing_ids)

    project = ProjectRecord(
        id=project_id,
        name=payload.project_name,
        template_id=template.id,
        template_version=selected_version,
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

    response_template = template.model_copy(update={"version": selected_version})
    return TemplateApplyResponse(project=project, template=response_template)


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


@app.get("/api/dashboard/{project_id}/health")
async def get_dashboard_health(project_id: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_project_health(project_id, headers=headers)
    logger.info(
        "dashboard.health.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/api/dashboard/{project_id}/trends")
async def get_dashboard_trends(project_id: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_project_trends(project_id, headers=headers)
    logger.info(
        "dashboard.trends.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/api/dashboard/{project_id}/quality")
async def get_dashboard_quality(project_id: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _lineage_client()
    response = await client.get_quality_summary(headers=headers)
    logger.info(
        "dashboard.quality.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.post("/api/dashboard/{project_id}/what-if")
async def create_dashboard_what_if(
    project_id: str, payload: DashboardWhatIfRequest, request: Request
) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.request_what_if(
        project_id, payload.model_dump(), headers=headers
    )
    logger.info(
        "dashboard.whatif.request",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/api/dashboard/{project_id}/kpis")
async def get_dashboard_kpis(project_id: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_project_kpis(project_id, headers=headers)
    logger.info(
        "dashboard.kpis.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/api/dashboard/{project_id}/narrative")
async def get_dashboard_narrative(project_id: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_project_narrative(project_id, headers=headers)
    logger.info(
        "dashboard.narrative.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/api/connector-gallery/types")
async def list_connector_types(request: Request) -> list[dict[str, Any]]:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    types = _load_connector_registry()
    logger.info("connector_gallery.types.list", extra={"tenant_id": tenant_id})
    return types


@app.get("/api/connector-gallery/instances")
async def list_connector_instances(request: Request) -> Response:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    headers = build_forward_headers(request, session)
    client = _connector_hub_client()
    try:
        response = await client.list_connectors(headers=headers)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    logger.info("connector_gallery.instances.list", extra={"tenant_id": tenant_id})
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.post("/api/connector-gallery/instances")
async def create_connector_instance(
    payload: ConnectorInstanceCreate, request: Request
) -> Response:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    headers = build_forward_headers(request, session)
    metadata = {"connector_type_id": payload.connector_type_id}
    metadata.update(payload.metadata or {})
    connector_request = {
        "name": payload.connector_type_id,
        "version": payload.version,
        "enabled": payload.enabled,
        "metadata": metadata,
    }
    client = _connector_hub_client()
    try:
        response = await client.create_connector(connector_request, headers=headers)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough_response(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.create",
        extra={
            "tenant_id": tenant_id,
            "connector_id": body.get("connector_id"),
            "connector_type_id": payload.connector_type_id,
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)


@app.patch("/api/connector-gallery/instances/{connector_id}")
async def update_connector_instance(
    connector_id: str, payload: ConnectorInstanceUpdate, request: Request
) -> Response:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    headers = build_forward_headers(request, session)
    update_payload = payload.model_dump(exclude_none=True)
    client = _connector_hub_client()
    try:
        response = await client.update_connector(
            connector_id, update_payload, headers=headers
        )
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough_response(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.update",
        extra={
            "tenant_id": tenant_id,
            "connector_id": connector_id,
            "connector_type_id": body.get("metadata", {}).get("connector_type_id"),
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)


@app.get("/api/connector-gallery/instances/{connector_id}/health")
async def get_connector_health(connector_id: str, request: Request) -> Response:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    headers = build_forward_headers(request, session)
    client = _connector_hub_client()
    try:
        response = await client.get_connector_health(connector_id, headers=headers)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough_response(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.health",
        extra={
            "tenant_id": tenant_id,
            "connector_id": connector_id,
            "connector_type_id": body.get("metadata", {}).get("connector_type_id"),
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)


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
