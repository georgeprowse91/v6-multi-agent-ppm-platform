"""Shared dependencies and helpers used across all route modules.

This module re-exports state objects, store instances, helper functions,
and Pydantic models so individual route modules can do::

    from routes._deps import (
        _require_session, _tenant_id_from_request, logger, ...
    )

Nothing in this module should import from any route module.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import jwt
import yaml
from fastapi import (
    HTTPException,
    Request,
    Response,
)
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[4]
WEB_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = WEB_ROOT / "static"
FRONTEND_DIST_DIR = WEB_ROOT / "frontend" / "dist"
DATA_DIR = WEB_ROOT / "data"
STORAGE_DIR = WEB_ROOT / "storage"

TEMPLATES_PATH = DATA_DIR / "templates.json"
PROJECTS_PATH = DATA_DIR / "projects.json"
ROLES_SEED_PATH = DATA_DIR / "roles.json"
KNOWLEDGE_DB_PATH = DATA_DIR / "knowledge.db"
WORKSPACE_STATE_PATH = STORAGE_DIR / "workspace_state.json"
TIMELINES_PATH = STORAGE_DIR / "timelines.json"
SPREADSHEETS_PATH = STORAGE_DIR / "spreadsheets.json"
TREES_PATH = STORAGE_DIR / "trees.json"
AGENT_SETTINGS_PATH = STORAGE_DIR / "agent_settings.json"
INTAKE_REQUESTS_PATH = STORAGE_DIR / "intake_requests.json"
PIPELINE_STATE_PATH = STORAGE_DIR / "pipeline_state.json"
WORKFLOW_DEFINITIONS_PATH = STORAGE_DIR / "workflow_definitions.json"
DEMO_OUTBOX_PATH = STORAGE_DIR / "demo_outbox.json"
RUNTIME_LIFECYCLE_PATH = STORAGE_DIR / "runtime_lifecycle.json"
DEMO_DOWNLOADS_DIR = STORAGE_DIR / "downloads"
SOR_FIXTURES_PATH = DATA_DIR / "demo" / "sor_fixtures.json"
ROLES_PATH = STORAGE_DIR / "roles.json"
MERGE_REVIEW_PATH = STORAGE_DIR / "merge_review_cases.json"
LLM_PREFERENCES_PATH = STORAGE_DIR / "llm_preferences.json"
DEMAND_STORE_PATH = STORAGE_DIR / "demand.json"
PRIORITISATION_STORE_PATH = STORAGE_DIR / "prioritisation.json"
CAPACITY_STORE_PATH = STORAGE_DIR / "capacity.json"
SCENARIOS_STORE_PATH = STORAGE_DIR / "scenarios.json"
COMMENTS_STORE_PATH = STORAGE_DIR / "comments.json"
NOTIFICATIONS_STORE_PATH = STORAGE_DIR / "notifications.json"
SYNC_STORE_PATH = STORAGE_DIR / "sync_center.json"
PACKS_STORE_PATH = STORAGE_DIR / "packs.json"
ALERTS_STORE_PATH = STORAGE_DIR / "alerts.json"
MERGE_REVIEW_SEED_PATH = WEB_ROOT / "data" / "merge_review_seed.json"
CONNECTOR_REGISTRY_PATH = REPO_ROOT / "connectors" / "registry" / "connectors.json"
METHODOLOGY_DOCS_ROOT = REPO_ROOT / "docs" / "methodology"
PROMPT_ROOT = REPO_ROOT / "agents" / "runtime" / "prompts"
DEMAND_PROMPT_PATH = PROMPT_ROOT / "demand-intake-extraction.prompt.yaml"
PROJECT_PROMPT_PATH = PROMPT_ROOT / "project-intake-extraction.prompt.yaml"
INTAKE_ASSISTANT_PROMPTS = {
    "sponsor": PROMPT_ROOT / "intake-assistant-sponsor.prompt.yaml",
    "business": PROMPT_ROOT / "intake-assistant-business.prompt.yaml",
    "success": PROMPT_ROOT / "intake-assistant-success.prompt.yaml",
    "attachments": PROMPT_ROOT / "intake-assistant-attachments.prompt.yaml",
}

SESSION_COOKIE = "ppm_session"
STATE_COOKIE = "ppm_oidc_state"
SESSION_SIGNING_ALGORITHM = "HS256"
OIDC_HTTP_TRANSPORT: httpx.BaseTransport | None = None

# ---------------------------------------------------------------------------
# Store instances  (created once, shared by all route modules)
# ---------------------------------------------------------------------------
from agent_registry import load_agent_registry  # noqa: E402
from agent_settings_models import AgentConfigUpdate, AgentProjectEntry  # noqa: E402
from agent_settings_store import AgentSettingsStore  # noqa: E402
from analytics_proxy import AnalyticsServiceClient  # noqa: E402
from connector_hub_proxy import ConnectorHubClient  # noqa: E402
from data_service_proxy import DataServiceClient  # noqa: E402
from demo_integrations import (  # noqa: E402
    DemoAnalyticsServiceClient,
    DemoConnectorHubClient,
    DemoDataServiceClient,
    DemoDocumentServiceClient,
    DemoOutbox,
)
from demo_seed import DEMO_TENANT_ID  # noqa: E402
from document_proxy import DocumentServiceClient  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402
from methodology_node_runtime import load_methodology_node_runtime_registry  # noqa: E402
from template_mappings import TemplateMapping, load_template_mappings  # noqa: E402
from workspace_state import CanvasTab  # noqa: E402
from intake_store import IntakeStore  # noqa: E402
from knowledge_store import KnowledgeStore  # noqa: E402
from lineage_proxy import LineageServiceClient  # noqa: E402
from llm_preferences_store import LLMPreferencesStore  # noqa: E402
from merge_review_store import MergeReviewStore  # noqa: E402
from model_registry import get_enabled_models  # noqa: E402
from oidc_client import OIDCClient  # noqa: E402
from orchestrator_proxy import OrchestratorProxyClient  # noqa: E402
from pipeline_store import PipelineStore  # noqa: E402
from runtime_flags import demo_mode_enabled  # noqa: E402
from runtime_lifecycle_store import RuntimeLifecycleStore  # noqa: E402
from search_service import SearchService  # noqa: E402
from security.audit_log import build_event, get_audit_log_store  # noqa: E402
from security.config import load_yaml as load_yaml_config  # noqa: E402
from security.secrets import resolve_secret  # noqa: E402
from spreadsheet_store import SpreadsheetStore  # noqa: E402
from timeline_store import TimelineStore  # noqa: E402
from tree_store import TreeStore  # noqa: E402
from workflow_store import WorkflowDefinitionStore  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402

# ---------------------------------------------------------------------------
# Singleton stores
# ---------------------------------------------------------------------------
knowledge_store: KnowledgeStore | None = None
llm_preferences_store = LLMPreferencesStore(LLM_PREFERENCES_PATH)
workspace_state_store = WorkspaceStateStore(WORKSPACE_STATE_PATH)
timeline_store = TimelineStore(TIMELINES_PATH)
spreadsheet_store = SpreadsheetStore(SPREADSHEETS_PATH)
tree_store = TreeStore(TREES_PATH)
agent_settings_store = AgentSettingsStore(AGENT_SETTINGS_PATH)
intake_store = IntakeStore(INTAKE_REQUESTS_PATH)
merge_review_store = MergeReviewStore(MERGE_REVIEW_PATH, MERGE_REVIEW_SEED_PATH)
pipeline_store = PipelineStore(PIPELINE_STATE_PATH)
workflow_definition_store = WorkflowDefinitionStore(WORKFLOW_DEFINITIONS_PATH)
demo_outbox = DemoOutbox(DEMO_OUTBOX_PATH)
runtime_lifecycle_store = RuntimeLifecycleStore(RUNTIME_LIFECYCLE_PATH)
logger = logging.getLogger("web-ui")


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _demo_mode_enabled() -> bool:
    return demo_mode_enabled()


def _get_knowledge_store() -> KnowledgeStore:
    global knowledge_store
    if knowledge_store is None:
        knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)
    return knowledge_store


def _get_search_service() -> SearchService:
    return SearchService(_get_knowledge_store(), spreadsheet_store)


def _document_client() -> DocumentServiceClient | DemoDocumentServiceClient:
    if _demo_mode_enabled():
        return DemoDocumentServiceClient(demo_outbox)
    return DocumentServiceClient()


def _data_service_client() -> DataServiceClient | DemoDataServiceClient:
    if _demo_mode_enabled():
        return DemoDataServiceClient(demo_outbox)
    return DataServiceClient()


def _analytics_client() -> AnalyticsServiceClient | DemoAnalyticsServiceClient:
    if _demo_mode_enabled():
        return DemoAnalyticsServiceClient()
    return AnalyticsServiceClient()


def _lineage_client() -> LineageServiceClient:
    return LineageServiceClient()


def _orchestrator_client() -> OrchestratorProxyClient:
    return OrchestratorProxyClient()


def _connector_hub_client() -> ConnectorHubClient | DemoConnectorHubClient:
    if _demo_mode_enabled():
        return DemoConnectorHubClient(demo_outbox)
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


def _spa_route(path: str) -> str:
    return f"/app{path}"


def _multimodal_intake_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("multimodal_intake", environment=environment, default=False)


def _require_multimodal_intake() -> None:
    if not _multimodal_intake_enabled():
        raise HTTPException(status_code=404, detail="Feature disabled")


def _duplicate_resolution_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("duplicate_resolution", environment=environment, default=False)


def _unified_dashboards_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("unified_dashboards", environment=environment, default=False)


def _require_duplicate_resolution() -> None:
    if not _duplicate_resolution_enabled():
        raise HTTPException(status_code=404, detail="Feature disabled")


def _autonomous_deliverables_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("autonomous_deliverables", environment=environment, default=False)


def _load_demo_dashboard_payload(filename: str) -> dict[str, Any] | None:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", filename):
        return None
    candidate_paths = [
        REPO_ROOT / "apps" / "web" / "data" / "demo_dashboards" / filename,
        REPO_ROOT / "examples" / "demo-scenarios" / filename,
    ]
    for demo_path in candidate_paths:
        if not demo_path.exists():
            continue
        try:
            with demo_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _dashboard_demo_payload_or_default(
    filename: str, default_payload: dict[str, Any]
) -> dict[str, Any]:
    payload = _load_demo_dashboard_payload(filename)
    if isinstance(payload, dict):
        return payload
    return default_payload


def _slugify_filename(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", value).strip("-").lower()
    return sanitized or "project"


def _load_demo_search_payload(filename: str) -> dict[str, Any] | None:
    payload = _load_demo_dashboard_payload(filename)
    if not payload:
        return None
    results = payload.get("results")
    if not isinstance(results, list):
        return None
    return payload


def _load_demo_assistant_payload(filename: str) -> dict[str, Any] | None:
    payload = _load_demo_dashboard_payload(filename)
    if not payload:
        return None
    if not isinstance(payload.get("responses"), list):
        return None
    if not isinstance(payload.get("default"), dict):
        return None
    return payload


def _load_demo_conversation_payload(filename: str) -> list[dict[str, str]] | None:
    demo_path = REPO_ROOT / "apps" / "web" / "data" / "demo_conversations" / filename
    if not demo_path.exists():
        return None
    try:
        with demo_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None
    script: list[dict[str, str]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            return None
        role = entry.get("role")
        content = entry.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            return None
        script.append({"role": role, "content": content})
    return script


def _highlight_query(query: str, text: str) -> str | None:
    needle = query.lower().strip()
    if not needle:
        return None
    lowered = text.lower()
    if needle not in lowered:
        return None
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return pattern.sub(lambda value: f"<mark>{value.group(0)}</mark>", text)


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


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return load_yaml_config(path) or {}
    except (OSError, yaml.YAMLError):
        return {}


@lru_cache(maxsize=8)
def _load_prompt(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid prompt payload in {path}")
    return payload


def _render_prompt(template: str, *, document_name: str, document_content: str) -> str:
    return (
        template.replace("{{document_name}}", document_name)
        .replace("{{document_content}}", document_content)
        .strip()
    )


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _random_token_urlsafe(length_bytes: int) -> str:
    return base64.urlsafe_b64encode(os.urandom(length_bytes)).rstrip(b"=").decode("utf-8")


def _random_token_hex(length_bytes: int) -> str:
    return os.urandom(length_bytes).hex()


# ---------------------------------------------------------------------------
# Session / auth helpers
# ---------------------------------------------------------------------------

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


def _session_from_request(request: Request) -> dict[str, Any] | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return _dev_session()
    payload = _decode_cookie(session_id)
    if payload:
        return payload
    return _dev_session()


def _all_permission_ids() -> list[str]:
    permission_ids: set[str] = set()
    for role in _list_roles():
        permission_ids.update(role.permissions)
    return sorted(permission_ids)


def _demo_session_payload() -> dict[str, Any]:
    return {
        "subject": "demo-user",
        "tenant_id": DEMO_TENANT_ID,
        "roles": ["PMO_ADMIN"],
        "permissions": _all_permission_ids(),
        "access_token": "demo-token",
    }


def _require_session(request: Request) -> dict[str, Any]:
    session = _session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def _tenant_id_from_request(request: Request, session: dict[str, Any]) -> str | None:
    auth = getattr(request.state, "auth", None)
    tenant_id = getattr(auth, "tenant_id", None) if auth else None
    return tenant_id or session.get("tenant_id")


ROLE_ALIASES: dict[str, str] = {
    "tenant_owner": "PMO_ADMIN",
    "portfolio_admin": "PMO_ADMIN",
    "project_manager": "PM",
    "analyst": "TEAM_MEMBER",
    "auditor": "AUDITOR",
    "collaborator": "COLLABORATOR",
}


def _normalize_role_ids(roles: set[str]) -> set[str]:
    return {ROLE_ALIASES.get(role, role) for role in roles if role}


def _roles_from_request(request: Request, session: dict[str, Any]) -> set[str]:
    auth = getattr(request.state, "auth", None)
    roles = getattr(auth, "roles", None) if auth else None
    if roles is None:
        roles = session.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return {role for role in roles if role}


def _is_agent_admin(request: Request, session: dict[str, Any]) -> bool:
    roles = _normalize_role_ids(_roles_from_request(request, session))
    return bool(roles.intersection({"PMO_ADMIN"}))


def _require_roles(request: Request, allowed_roles: set[str]) -> dict[str, Any]:
    session = _require_session(request)
    roles = session.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    if not any(role in allowed_roles for role in roles):
        raise HTTPException(status_code=403, detail="RBAC denied")
    return session


def _role_ids_for_user(user_id: str) -> set[str]:
    for assignment in _list_role_assignments():
        if assignment.user_id == user_id:
            return set(assignment.role_ids)
    return set()


def _permissions_for_user(request: Request, session: dict[str, Any]) -> set[str]:
    explicit_permissions = session.get("permissions") or []
    if isinstance(explicit_permissions, str):
        explicit_permissions = [explicit_permissions]
    seeded_permissions = {permission for permission in explicit_permissions if permission}
    role_ids = set(_roles_from_request(request, session))
    subject = session.get("subject")
    if subject:
        role_ids |= _role_ids_for_user(subject)
    role_ids = _normalize_role_ids(role_ids)
    roles = {role.id: role for role in _list_roles()}
    permissions: set[str] = set()
    for role_id in role_ids:
        role = roles.get(role_id)
        if role:
            permissions.update(role.permissions)
    return permissions.union(seeded_permissions)


def permission_required(*permissions: str):
    required = {perm for perm in permissions if perm}

    def decorator(func):
        setattr(func, "required_permissions", required)
        return func

    return decorator


def _can_manage_llm(request: Request, session: dict[str, Any]) -> bool:
    permissions = _permissions_for_user(request, session)
    return bool({"config.manage", "llm.manage"}.intersection(permissions))


def _resolve_llm_selection(
    tenant_id: str, project_id: str | None, user_id: str | None
) -> tuple[str, str]:
    preference = llm_preferences_store.get_preferences(
        tenant_id=tenant_id, project_id=project_id, user_id=user_id
    )
    models = get_enabled_models(demo_mode=_demo_mode_enabled())
    if not models:
        raise HTTPException(status_code=503, detail="No enabled models")
    fallback = models[0]
    selected_provider = str(preference.get("provider") or fallback.provider)
    selected_model = str(preference.get("model_id") or fallback.model_id)
    available = {(item.provider, item.model_id) for item in models}
    if (selected_provider, selected_model) in available:
        return selected_provider, selected_model
    tenant_pref = llm_preferences_store.get_preferences(
        tenant_id=tenant_id, project_id=None, user_id=None
    )
    tenant_provider = str(tenant_pref.get("provider") or "")
    tenant_model = str(tenant_pref.get("model_id") or "")
    if (tenant_provider, tenant_model) in available:
        return tenant_provider, tenant_model
    return fallback.provider, fallback.model_id


# ---------------------------------------------------------------------------
# Roles helpers  (shared by auth + roles routes)
# ---------------------------------------------------------------------------

class RoleDefinition(BaseModel):
    id: str
    name: str
    permissions: list[str] = Field(default_factory=list)
    description: str | None = None


class RoleAssignment(BaseModel):
    user_id: str
    role_ids: list[str] = Field(default_factory=list)


def _load_roles_payload() -> dict[str, Any]:
    if ROLES_PATH.exists():
        return _load_json(ROLES_PATH, {"roles": [], "assignments": []})
    seed = _load_json(ROLES_SEED_PATH, {"roles": [], "assignments": []})
    if seed:
        _write_json(ROLES_PATH, seed)
    return seed


def _list_roles() -> list[RoleDefinition]:
    payload = _load_roles_payload()
    return [RoleDefinition.model_validate(item) for item in payload.get("roles", [])]


def _list_role_assignments() -> list[RoleAssignment]:
    payload = _load_roles_payload()
    return [RoleAssignment.model_validate(item) for item in payload.get("assignments", [])]


# ---------------------------------------------------------------------------
# OIDC helpers
# ---------------------------------------------------------------------------

def _oidc_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing OIDC setting: {name}")
    return value


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


def _is_safe_redirect_path(value: str) -> bool:
    if not value.startswith("/"):
        return False
    if value.startswith("//") or value.startswith("/\\"):
        return False
    if "://" in value or "@" in value:
        return False
    return True


def _validate_project_id(value: str | None) -> str | None:
    if value is None:
        return None
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", value):
        return None
    return value


# ---------------------------------------------------------------------------
# Enterprise store helper
# ---------------------------------------------------------------------------

def _load_store(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    payload = _load_json(path, default) if path.exists() else default
    if not isinstance(payload, dict):
        return default
    return payload


def _audit_record(request: Request, action: str, details: dict[str, Any]) -> None:
    session = _require_session(request)
    get_audit_log_store().record_event(
        build_event(
            tenant_id=session.get("tenant_id") or "demo-tenant",
            actor_id=session.get("subject") or "demo-user",
            actor_type="user",
            roles=list(_roles_from_request(request, session)),
            action=action,
            resource_type=details.get("resource", "enterprise"),
            resource_id=str(
                details.get("resource_id")
                or details.get("demand_id")
                or details.get("scenario_id")
                or details.get("pack_id")
                or "n/a"
            ),
            outcome="success",
            metadata=details,
        )
    )


def _ensure_notifications(payload: dict[str, Any], tenant_id: str) -> list[dict[str, Any]]:
    rows = payload.setdefault("notifications", [])
    if not isinstance(rows, list):
        payload["notifications"] = []
    return payload["notifications"]


# ---------------------------------------------------------------------------
# Approval payload  (used by search, assistant, legacy_pages, enterprise)
# ---------------------------------------------------------------------------

def _approval_payload() -> dict[str, Any]:
    if _demo_mode_enabled():
        seeded = demo_outbox.read("approvals")
        if seeded:
            return {
                "pending_count": len(seeded),
                "queues": [{"id": "seeded", "label": "Seeded Demo", "count": len(seeded)}],
                "items": seeded,
                "history": [],
            }
    return {
        "pending_count": 24,
        "queues": [
            {"id": "stage-gates", "label": "Stage Gates", "count": 12},
            {"id": "budget", "label": "Budget Changes", "count": 6},
            {"id": "vendor", "label": "Vendor Reviews", "count": 4},
            {"id": "compliance", "label": "Compliance", "count": 2},
        ],
        "items": [
            {
                "id": "app-1024",
                "title": "Gate: Phase 2 Exit",
                "project": "Phoenix",
                "risk": "Medium",
                "due_in": "2d",
                "sla": "On track",
                "approvers": [
                    {"name": "A. Lee", "role": "Primary"},
                    {"name": "S. Ortiz", "role": "Delegate"},
                ],
            },
            {
                "id": "app-1025",
                "title": "Budget Change +12%",
                "project": "Orion",
                "risk": "High",
                "due_in": "8h",
                "sla": "At risk",
                "approvers": [
                    {"name": "S. Patel", "role": "Finance"},
                    {"name": "M. Chung", "role": "Portfolio"},
                ],
            },
        ],
        "history": [
            {
                "timestamp": "09:32",
                "action": "Gate Exit Approval",
                "actor": "A. Lee",
                "evidence": "Evidence pack attached",
            },
            {
                "timestamp": "09:14",
                "action": "Budget Review Delegated",
                "actor": "S. Patel",
                "evidence": "SLA met",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Project loading helper  (used by search, assistant, templates_api)
# ---------------------------------------------------------------------------

def _load_projects() -> list:
    """Load all projects from the projects store file.

    Returns a list of ProjectRecord instances (imported lazily to avoid
    circular imports with ``_models``).
    """
    from routes._models import ProjectRecord

    raw = _load_json(PROJECTS_PATH, {"projects": []})
    return [ProjectRecord.model_validate(p) for p in raw.get("projects", [])]
