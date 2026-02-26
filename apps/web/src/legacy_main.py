from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import jwt
import yaml
from fastapi import (
    APIRouter,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

REPO_ROOT = Path(__file__).resolve().parents[3]
_common_src = REPO_ROOT / "packages" / "common" / "src"
if str(_common_src) not in sys.path:
    sys.path.insert(0, str(_common_src))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from agent_registry import load_agent_registry  # noqa: E402
from agent_settings_models import (  # noqa: E402
    AgentConfigUpdate,
    AgentProjectEntry,
)
from agent_settings_store import AgentSettingsStore  # noqa: E402
from analytics_proxy import AnalyticsServiceClient  # noqa: E402
from canonical_template_registry import (  # noqa: E402
    get_catalog_template,
    list_catalog_templates,
)
from connector_hub_proxy import ConnectorHubClient  # noqa: E402
from data_service_proxy import DataServiceClient  # noqa: E402
from demo_integrations import (  # noqa: E402
    DemoAnalyticsServiceClient,
    DemoConnectorHubClient,
    DemoDataServiceClient,
    DemoDocumentServiceClient,
    DemoOutbox,
)
from demo_seed import (  # noqa: E402
    DEMO_TENANT_ID,
    seed_demo_data,
)
from document_proxy import DocumentServiceClient, build_forward_headers  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402
from gating import evaluate_activity_access, next_required_activity, stage_progress  # noqa: E402
from intake_models import (  # noqa: E402
    IntakeDecision,
    IntakeRequest,
    IntakeRequestCreate,
)
from intake_store import IntakeStore  # noqa: E402
from knowledge_store import KnowledgeStore  # noqa: E402
from lineage_proxy import LineageServiceClient  # noqa: E402
from llm.client import LLMGateway, LLMProviderError  # noqa: E402
from llm_preferences_store import LLMPreferencesStore  # noqa: E402
from merge_review_models import MergeDecision, MergeReviewCase  # noqa: E402
from merge_review_store import MergeReviewStore  # noqa: E402
from methodologies import (  # noqa: E402
    METHODOLOGY_STORAGE_PATH,
    available_methodologies,
    get_default_methodology_map,
    get_methodology_map,
)
from methodology_node_runtime import (  # noqa: E402
    list_runtime_actions_for_node,
    load_methodology_node_runtime_registry,
    resolve_runtime,
)
from model_registry import get_enabled_models  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing, get_trace_id  # noqa: E402
from oidc_client import OIDCClient  # noqa: E402
from orchestrator_proxy import OrchestratorProxyClient  # noqa: E402
from pipeline_models import (  # noqa: E402
    PipelineBoard,
    PipelineItem,
    PipelineItemUpdate,
)
from pipeline_store import PipelineStore  # noqa: E402
from runtime_lifecycle_store import RuntimeLifecycleStore  # noqa: E402
from search_service import SearchService, _match_score  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.audit_log import build_event, get_audit_log_store  # noqa: E402
from security.prompt_safety import evaluate_prompt  # noqa: E402
from security.secrets import resolve_secret  # noqa: E402
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
from spreadsheet_store import SpreadsheetStore  # noqa: E402
from template_mappings import (  # noqa: E402
    TemplateMapping,
    get_template_mapping,
    list_templates_for_methodology_node,
    load_template_mappings,
)
from template_models import (
    CanonicalTemplateDefinition,
    CanonicalTemplateSummary,
    TemplateInstantiateRequest,
    TemplateInstantiateResponse,
    TemplateType,
    build_placeholder_context,
    render_template_value_with_unresolved,
)
from template_registry import (  # noqa: E402
    get_template as get_deliverable_template,
)
from timeline_models import (  # noqa: E402
    Milestone,
    MilestoneCreate,
    MilestoneUpdate,
    TimelineExportResponse,
    TimelineResponse,
)
from timeline_store import TimelineStore  # noqa: E402
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
from workflow_models import (  # noqa: E402
    WorkflowDefinitionPayload,
    WorkflowDefinitionRecord,
    WorkflowDefinitionSummary,
)
from workflow_store import WorkflowDefinitionStore  # noqa: E402
from workspace_state import (  # noqa: E402
    ActivityCompletionUpdate,
    CanvasTab,
    OpenRef,
    WorkspaceSelectionUpdate,
    WorkspaceState,
)
from workspace_state_store import WorkspaceStateStore  # noqa: E402

from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.orchestrator import Orchestrator  # noqa: E402
from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402
from runtime_flags import demo_mode_enabled  # noqa: E402
from security.config import load_yaml as load_yaml_config  # noqa: E402

WEB_ROOT = Path(__file__).resolve().parents[1]
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
CONNECTOR_REGISTRY_PATH = REPO_ROOT / "integrations" / "connectors" / "registry" / "connectors.json"
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

app = FastAPI(title="PPM Web Console", version=API_VERSION)
api_router = APIRouter(prefix="/v1")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if FRONTEND_DIST_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
apply_api_governance(app, service_name="web")

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

_meter = configure_metrics("web-ui")
post_login_landing_success_total = _meter.create_counter(
    name="post_login_landing_success_total",
    description="Total successful post-login landing redirects.",
    unit="1",
)

validate_startup_config()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "web-ui"
    dependencies: dict[str, str] = Field(default_factory=dict)


class UIConfig(BaseModel):
    api_gateway_url: str
    workflow_engine_url: str
    oidc_enabled: bool
    login_url: str
    logout_url: str
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class SessionInfo(BaseModel):
    authenticated: bool
    subject: str | None = None
    tenant_id: str | None = None
    roles: list[str] | None = None
    permissions: list[str] | None = None


class IntakeExtractionEntity(BaseModel):
    schema_name: str
    entity_id: str


class IntakeExtractionResponse(BaseModel):
    document_id: str | None = None
    demand: dict[str, Any] | None = None
    project: dict[str, Any] | None = None
    entities: dict[str, IntakeExtractionEntity] = Field(default_factory=dict)


class IntakeAssistantRequest(BaseModel):
    step_id: Literal["sponsor", "business", "success", "attachments"]
    step_index: int = Field(ge=0, le=3)
    form_state: dict[str, str] = Field(default_factory=dict)
    validation_errors: dict[str, str] = Field(default_factory=dict)
    user_answer: str | None = None


class IntakeAssistantResponse(BaseModel):
    step_id: Literal["sponsor", "business", "success", "attachments"]
    questions: list[str] = Field(default_factory=list)
    proposals: dict[str, str] = Field(default_factory=dict)
    apply_hints: list[str] = Field(default_factory=list)


class RoleDefinition(BaseModel):
    id: str
    name: str
    permissions: list[str] = Field(default_factory=list)
    description: str | None = None


class WbsItem(BaseModel):
    id: str
    title: str
    parent_id: str | None = None
    order: int = 0
    owner: str | None = None
    status: str | None = None


class WbsResponse(BaseModel):
    project_id: str
    updated_at: str
    items: list[WbsItem] = Field(default_factory=list)


class WbsUpdateRequest(BaseModel):
    item_id: str
    parent_id: str | None = None
    order: int = 0


class ScheduleTask(BaseModel):
    id: str
    name: str
    start: str
    end: str
    progress: int = 0
    dependencies: list[str] = Field(default_factory=list)
    owner: str | None = None
    status: str | None = None


class ScheduleResponse(BaseModel):
    project_id: str
    updated_at: str
    tasks: list[ScheduleTask] = Field(default_factory=list)


class DependencyNode(BaseModel):
    id: str
    label: str
    type: Literal["program", "project", "task", "milestone"]
    status: str | None = None
    owner: str | None = None
    summary: str | None = None
    url: str | None = None


class DependencyLink(BaseModel):
    source: str
    target: str
    kind: Literal["hard", "soft"] = "hard"
    critical: bool = False


class DependencyMapResponse(BaseModel):
    program_id: str
    generated_at: str
    nodes: list[DependencyNode] = Field(default_factory=list)
    links: list[DependencyLink] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    id: str
    name: str
    start: str
    end: str
    owner: str | None = None
    status: Literal["planned", "in_progress", "at_risk", "complete"] = "planned"
    progress: int = Field(ge=0, le=100)
    summary: str | None = None


class RoadmapMilestone(BaseModel):
    id: str
    name: str
    date: str
    phase_id: str
    status: Literal["planned", "in_progress", "complete"] = "planned"
    owner: str | None = None


class ProgramRoadmapResponse(BaseModel):
    program_id: str
    generated_at: str
    phases: list[RoadmapPhase] = Field(default_factory=list)
    milestones: list[RoadmapMilestone] = Field(default_factory=list)


class RoleAssignment(BaseModel):
    user_id: str
    role_ids: list[str] = Field(default_factory=list)


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
    assistant_prompts: list[str] = Field(default_factory=list)
    template_id: str | None = None
    agent_id: str | None = None
    connector_id: str | None = None
    access: ActivityAccessSummary
    completed: bool
    children: list[ActivitySummary] = Field(default_factory=list)


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


class MethodologyActivityEditor(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    prerequisites: list[str] = Field(default_factory=list)
    category: str = Field(default="methodology")
    recommended_canvas_tab: CanvasTab = "document"


class MethodologyStageEditor(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exit_criteria: list[str] = Field(default_factory=list)
    activities: list[MethodologyActivityEditor] = Field(default_factory=list)


class MethodologyGateCriteriaEditor(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence: str | None = None
    check: str | None = None


class MethodologyGateEditor(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    criteria: list[MethodologyGateCriteriaEditor] = Field(default_factory=list)


class MethodologyEditorPayload(BaseModel):
    methodology_id: str = Field(min_length=1)
    stages: list[MethodologyStageEditor] = Field(default_factory=list)
    gates: list[MethodologyGateEditor] = Field(default_factory=list)


class GatingSummary(BaseModel):
    current_activity_access: ActivityAccessSummary
    next_required_activity_id: str | None = None


class AssistantSendRequest(BaseModel):
    project_id: str
    message: str
    prompt_id: str | None = None
    prompt_description: str | None = None
    prompt_tags: list[str] = Field(default_factory=list)


class SelectedActivitySummary(BaseModel):
    id: str
    name: str
    description: str
    assistant_prompts: list[str]
    recommended_canvas_tab: CanvasTab
    category: str
    template_id: str | None = None
    agent_id: str | None = None
    connector_id: str | None = None


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
    templates_available_here: list[TemplateMapping] = Field(default_factory=list)
    templates_required_here: list[TemplateMapping] = Field(default_factory=list)
    templates_in_review: list[TemplateMapping] = Field(default_factory=list)
    runtime_actions_available: list[str] = Field(default_factory=list)
    runtime_default_view_contract: dict[str, Any] | None = None


class MethodologyRuntimeResolveResponse(BaseModel):
    resolution_contract: dict[str, Any]


class MethodologyNodeActionRequest(BaseModel):
    methodology_id: str
    stage_id: str
    activity_id: str | None = None
    task_id: str | None = None
    lifecycle_event: Literal["view", "generate", "update", "review", "approve", "publish"]
    user_input: dict[str, Any] = Field(default_factory=dict)


class MethodologyNodeActionResponse(BaseModel):
    workspace_id: str
    lifecycle_event: str
    resolution_contract: dict[str, Any]
    assistant_response: dict[str, Any]
    artifacts_created: list[dict[str, Any]] = Field(default_factory=list)
    artifacts_updated: list[dict[str, Any]] = Field(default_factory=list)
    connector_operations: list[dict[str, Any]] = Field(default_factory=list)
    workflow_trace: dict[str, Any] = Field(default_factory=dict)
    human_review: dict[str, Any] = Field(default_factory=dict)
    status: str


class RuntimeApprovalDecisionRequest(BaseModel):
    workspace_id: str
    decision: Literal["approve", "reject", "modify"]
    notes: str | None = None


class SorPreviewRequest(BaseModel):
    methodology_id: str
    stage_id: str
    activity_id: str | None = None
    task_id: str | None = None
    lifecycle_event: Literal["generate", "update", "review", "approve", "publish"] = "generate"


class SorPreviewResponse(BaseModel):
    sources: list[dict[str, Any]] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)


class SorPublishRequest(SorPreviewRequest):
    workspace_id: str = "default"
    changes: dict[str, Any] = Field(default_factory=dict)


class SorPublishResponse(BaseModel):
    outbox_entry: dict[str, Any]
    applied_change: dict[str, Any]


class AgentProfileTemplateMapping(BaseModel):
    template_id: str
    template_name: str
    lifecycle_events: list[str] = Field(default_factory=list)
    methodology_nodes: list[dict[str, Any]] = Field(default_factory=list)
    run_modes: list[str] = Field(default_factory=list)


class AgentProfileResponse(BaseModel):
    agent_id: str
    name: str
    purpose: str
    capabilities: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    templates_touched: list[AgentProfileTemplateMapping] = Field(default_factory=list)
    connectors_used: list[dict[str, Any]] = Field(default_factory=list)
    methodology_nodes_supported: list[dict[str, Any]] = Field(default_factory=list)
    run_modes: list[str] = Field(default_factory=list)


class AgentPreviewRunRequest(BaseModel):
    methodology_id: str | None = None
    stage_id: str | None = None
    activity_id: str | None = None
    task_id: str | None = None
    lifecycle_event: Literal["generate", "update", "review", "approve", "publish"] = "generate"
    user_input: dict[str, Any] = Field(default_factory=dict)


class AgentPreviewRunResponse(BaseModel):
    agent_id: str
    demo_safe: bool
    run_trace: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    connector_operations: list[dict[str, Any]] = Field(default_factory=list)
    status: str


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
    methodology: dict[str, Any]
    template_mapping: TemplateMapping | None = None
    related_templates: list[TemplateMapping] = Field(default_factory=list)


def _autonomous_deliverables_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("autonomous_deliverables", environment=environment, default=False)


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


class SearchResult(BaseModel):
    id: str
    type: Literal["document", "project", "knowledge", "approval", "workflow"]
    title: str
    summary: str
    project_id: str | None = None
    updated_at: str | None = None
    highlights: dict[str, str] | None = None
    payload: dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    offset: int
    limit: int
    total: int
    results: list[SearchResult]


class AssistantQueryRequest(BaseModel):
    query: str
    project_id: str | None = None
    provider: str | None = None
    model_id: str | None = None


class AssistantQueryResponse(BaseModel):
    query: str
    summary: str
    items: list[str] = Field(default_factory=list)


class DemoConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DemoConversationResponse(BaseModel):
    scenario: str
    messages: list[DemoConversationMessage] = Field(default_factory=list)


class DocumentCanvasRequest(BaseModel):
    name: str
    content: str
    classification: str
    retention_days: int
    metadata: dict[str, Any] = {}


class DashboardWhatIfRequest(BaseModel):
    scenario: str
    adjustments: dict[str, Any] = {}


class DashboardExportResponse(BaseModel):
    project_id: str
    file_name: str
    download_path: str
    generated_at: str


class AssistantPrerequisite(BaseModel):
    activity_id: str
    activity_name: str
    stage_id: str
    stage_name: str
    status: str


class AssistantSuggestionRequest(BaseModel):
    project_id: str
    provider: str | None = None
    model_id: str | None = None
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


class LLMPreferenceRequest(BaseModel):
    scope: Literal["tenant", "project", "user"]
    project_id: str | None = None
    provider: str
    model_id: str


class LLMPreferenceResponse(BaseModel):
    provider: str
    model_id: str


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


@app.on_event("startup")
async def startup() -> None:
    global knowledge_store
    knowledge_store = KnowledgeStore(KNOWLEDGE_DB_PATH)
    load_template_mappings()
    load_methodology_node_runtime_registry()
    if _demo_mode_enabled():
        seed_demo_data(
            workspace_state_store=workspace_state_store,
            spreadsheet_store=spreadsheet_store,
            timeline_store=timeline_store,
            tree_store=tree_store,
            knowledge_db_path=KNOWLEDGE_DB_PATH,
            demo_outbox=demo_outbox,
        )


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


def _demo_mode_enabled() -> bool:
    return demo_mode_enabled()


def _load_demo_dashboard_payload(filename: str) -> dict[str, Any] | None:
    # Validate filename to prevent path traversal
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


_demo_wbs_state: dict[str, list[WbsItem]] = {}
_demo_schedule_state: dict[str, list[ScheduleTask]] = {}


def _default_wbs_items(project_id: str) -> list[WbsItem]:
    return [
        WbsItem(id=f"{project_id}-1", title="Initiation", order=0, owner="PMO"),
        WbsItem(
            id=f"{project_id}-1-1",
            title="Project charter",
            parent_id=f"{project_id}-1",
            order=0,
            owner="PMO",
        ),
        WbsItem(
            id=f"{project_id}-1-2",
            title="Stakeholder map",
            parent_id=f"{project_id}-1",
            order=1,
            owner="Comms",
        ),
        WbsItem(id=f"{project_id}-2", title="Planning", order=1, owner="Delivery"),
        WbsItem(
            id=f"{project_id}-2-1",
            title="Scope baseline",
            parent_id=f"{project_id}-2",
            order=0,
            owner="Delivery",
        ),
        WbsItem(
            id=f"{project_id}-2-2",
            title="Resource plan",
            parent_id=f"{project_id}-2",
            order=1,
            owner="People Ops",
        ),
        WbsItem(id=f"{project_id}-3", title="Execution", order=2, owner="Delivery"),
        WbsItem(
            id=f"{project_id}-3-1",
            title="Sprint backlog",
            parent_id=f"{project_id}-3",
            order=0,
            owner="Engineering",
        ),
        WbsItem(
            id=f"{project_id}-3-2",
            title="QA readiness",
            parent_id=f"{project_id}-3",
            order=1,
            owner="QA",
        ),
    ]


def _default_schedule_tasks(project_id: str) -> list[ScheduleTask]:
    return [
        ScheduleTask(
            id=f"{project_id}-kickoff",
            name="Kickoff & alignment",
            start="2026-11-04",
            end="2026-11-08",
            progress=100,
            dependencies=[],
            owner="PMO",
            status="complete",
        ),
        ScheduleTask(
            id=f"{project_id}-plan",
            name="Planning sprint",
            start="2026-11-11",
            end="2026-11-22",
            progress=60,
            dependencies=[f"{project_id}-kickoff"],
            owner="Delivery",
            status="in_progress",
        ),
        ScheduleTask(
            id=f"{project_id}-build",
            name="Execution build",
            start="2026-11-25",
            end="2026-12-20",
            progress=25,
            dependencies=[f"{project_id}-plan"],
            owner="Engineering",
            status="planned",
        ),
        ScheduleTask(
            id=f"{project_id}-review",
            name="Gate review",
            start="2026-12-23",
            end="2026-12-27",
            progress=0,
            dependencies=[f"{project_id}-build"],
            owner="PMO",
            status="planned",
        ),
    ]


def _get_demo_wbs(project_id: str) -> list[WbsItem]:
    if project_id not in _demo_wbs_state:
        _demo_wbs_state[project_id] = _default_wbs_items(project_id)
    return _demo_wbs_state[project_id]


def _get_demo_schedule(project_id: str) -> list[ScheduleTask]:
    if project_id not in _demo_schedule_state:
        _demo_schedule_state[project_id] = _default_schedule_tasks(project_id)
    return _demo_schedule_state[project_id]


def _mock_dependency_map(program_id: str) -> DependencyMapResponse:
    now = datetime.now(timezone.utc).isoformat()
    nodes = [
        DependencyNode(
            id=f"{program_id}-program",
            label="Digital Core Program",
            type="program",
            status="in_progress",
            owner="PMO",
            summary="Modernize core platforms and data foundations.",
            url=f"/app/programs/{program_id}",
        ),
        DependencyNode(
            id=f"{program_id}-proj-crm",
            label="CRM migration",
            type="project",
            status="at_risk",
            owner="Revenue Ops",
            summary="Move sales workflows to new CRM environment.",
            url="/app/projects/crm-migration",
        ),
        DependencyNode(
            id=f"{program_id}-proj-data",
            label="Data lake uplift",
            type="project",
            status="in_progress",
            owner="Data Platform",
            summary="Harden ingestion pipelines and governance rules.",
            url="/app/projects/data-lake-uplift",
        ),
        DependencyNode(
            id=f"{program_id}-task-api",
            label="API gateway cutover",
            type="task",
            status="planned",
            owner="Engineering",
            summary="Finalize gateway routes before CRM launch.",
            url="/app/projects/crm-migration",
        ),
        DependencyNode(
            id=f"{program_id}-task-privacy",
            label="Privacy review",
            type="task",
            status="in_progress",
            owner="Security",
            summary="Run DPIA and retention review for new data lake.",
            url="/app/projects/data-lake-uplift",
        ),
        DependencyNode(
            id=f"{program_id}-milestone-ga",
            label="Program launch",
            type="milestone",
            status="planned",
            owner="PMO",
            summary="Go-live for the unified platform release.",
            url="/app/programs/launch",
        ),
    ]
    links = [
        DependencyLink(
            source=f"{program_id}-program",
            target=f"{program_id}-proj-crm",
            kind="hard",
            critical=True,
        ),
        DependencyLink(
            source=f"{program_id}-program",
            target=f"{program_id}-proj-data",
            kind="hard",
            critical=False,
        ),
        DependencyLink(
            source=f"{program_id}-proj-crm",
            target=f"{program_id}-task-api",
            kind="soft",
            critical=True,
        ),
        DependencyLink(
            source=f"{program_id}-proj-data",
            target=f"{program_id}-task-privacy",
            kind="hard",
            critical=False,
        ),
        DependencyLink(
            source=f"{program_id}-task-api",
            target=f"{program_id}-milestone-ga",
            kind="hard",
            critical=True,
        ),
        DependencyLink(
            source=f"{program_id}-task-privacy",
            target=f"{program_id}-milestone-ga",
            kind="soft",
            critical=False,
        ),
    ]
    return DependencyMapResponse(
        program_id=program_id,
        generated_at=now,
        nodes=nodes,
        links=links,
    )


def _mock_program_roadmap(program_id: str) -> ProgramRoadmapResponse:
    now = datetime.now(timezone.utc).isoformat()
    phases = [
        RoadmapPhase(
            id=f"{program_id}-phase-discovery",
            name="Discovery & alignment",
            start="2026-10-07",
            end="2026-11-15",
            owner="Strategy",
            status="complete",
            progress=100,
            summary="Scope the program charter and align executive sponsors.",
        ),
        RoadmapPhase(
            id=f"{program_id}-phase-design",
            name="Design & architecture",
            start="2026-11-18",
            end="2027-01-10",
            owner="Enterprise Architecture",
            status="in_progress",
            progress=68,
            summary="Define integration patterns and readiness checkpoints.",
        ),
        RoadmapPhase(
            id=f"{program_id}-phase-delivery",
            name="Delivery waves",
            start="2027-01-13",
            end="2027-04-18",
            owner="Delivery",
            status="at_risk",
            progress=42,
            summary="Execute release waves with partner teams.",
        ),
        RoadmapPhase(
            id=f"{program_id}-phase-rollout",
            name="Rollout & adoption",
            start="2027-04-21",
            end="2027-06-06",
            owner="Change Management",
            status="planned",
            progress=10,
            summary="Train end users and monitor adoption KPIs.",
        ),
    ]
    milestones = [
        RoadmapMilestone(
            id=f"{program_id}-ms-charter",
            name="Charter signed",
            date="2026-11-12",
            phase_id=f"{program_id}-phase-discovery",
            status="complete",
            owner="PMO",
        ),
        RoadmapMilestone(
            id=f"{program_id}-ms-arch",
            name="Architecture review",
            date="2026-12-20",
            phase_id=f"{program_id}-phase-design",
            status="in_progress",
            owner="Architecture",
        ),
        RoadmapMilestone(
            id=f"{program_id}-ms-wave1",
            name="Wave 1 launch",
            date="2027-02-14",
            phase_id=f"{program_id}-phase-delivery",
            status="planned",
            owner="Delivery",
        ),
        RoadmapMilestone(
            id=f"{program_id}-ms-rollout",
            name="Adoption checkpoint",
            date="2027-05-09",
            phase_id=f"{program_id}-phase-rollout",
            status="planned",
            owner="Change",
        ),
    ]
    return ProgramRoadmapResponse(
        program_id=program_id,
        generated_at=now,
        phases=phases,
        milestones=milestones,
    )


def _mock_portfolio_health(portfolio_id: str | None, project_id: str | None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "portfolio_id": portfolio_id or "portfolio-01",
        "project_id": project_id,
        "as_of": now,
        "kpis": [
            {
                "id": "value_delivered",
                "label": "Value delivered",
                "value": 4.1,
                "target": 5.0,
                "unit": "M",
                "trend": "up",
            },
            {
                "id": "budget_utilisation",
                "label": "Budget utilisation",
                "value": 0.76,
                "target": 0.8,
                "unit": "ratio",
                "trend": "steady",
            },
            {
                "id": "risk_exposure",
                "label": "Risk exposure",
                "value": 0.29,
                "target": 0.25,
                "unit": "ratio",
                "trend": "down",
            },
            {
                "id": "resource_capacity",
                "label": "Resource capacity",
                "value": 0.88,
                "target": 0.9,
                "unit": "ratio",
                "trend": "up",
            },
            {
                "id": "stage_gate_status",
                "label": "Stage-gate status",
                "value": 0.7,
                "target": 0.8,
                "unit": "ratio",
                "trend": "up",
            },
        ],
        "highlights": [
            {"label": "Programs on track", "value": 7},
            {"label": "Programs at risk", "value": 2},
            {"label": "Portfolio NPV", "value": 11.8, "unit": "M"},
        ],
    }


def _mock_lifecycle_metrics(portfolio_id: str | None, project_id: str | None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "portfolio_id": portfolio_id or "portfolio-01",
        "project_id": project_id,
        "as_of": now,
        "summary": {
            "avg_cycle_time_days": 39,
            "gates_on_track": 3,
            "gates_at_risk": 1,
            "gates_blocked": 0,
        },
        "stage_gates": [
            {
                "stage_id": "adaptive-discovery",
                "stage_name": "Discovery",
                "status": "on_track",
                "percent_complete": 82,
                "gate": "Discovery Gate",
                "due_date": "2026-09-05",
            },
            {
                "stage_id": "adaptive-planning",
                "stage_name": "Planning",
                "status": "at_risk",
                "percent_complete": 58,
                "gate": "Planning Gate",
                "due_date": "2026-09-18",
            },
            {
                "stage_id": "adaptive-delivery",
                "stage_name": "Delivery",
                "status": "on_track",
                "percent_complete": 43,
                "gate": "Delivery Gate",
                "due_date": "2026-10-02",
            },
            {
                "stage_id": "adaptive-review",
                "stage_name": "Review",
                "status": "on_track",
                "percent_complete": 18,
                "gate": "Review Gate",
                "due_date": "2026-10-20",
            },
        ],
        "capacity": {"current": 0.86, "target": 0.9},
    }


def _format_credentials(connector_id: str, fields: list[str]) -> list[str]:
    return [f"{connector_id.upper()}_{field.upper()}" for field in fields]


def _load_connector_manifest(manifest_path: str) -> dict[str, Any] | None:
    manifest_file = (REPO_ROOT / manifest_path).resolve()
    if not manifest_file.is_relative_to(REPO_ROOT):
        logger.warning("Path traversal blocked in manifest load: %s", manifest_path)
        return None
    if not manifest_file.exists():
        return None
    try:
        payload = load_yaml_config(manifest_file)
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
        logger.error("connector_gallery.registry_read_failed", extra={"error": str(exc)})
        return []
    if not isinstance(payload, list):
        return []
    return _enrich_connector_types(payload)


@app.get("/healthz", response_model=HealthResponse)
async def healthz(response: Response) -> HealthResponse:
    dependencies = {
        "knowledge_store": "ok" if knowledge_store else "down",
        "intake_store": "ok" if intake_store else "down",
        "pipeline_store": "ok" if pipeline_store else "down",
        "workflow_definitions": "ok" if WORKFLOW_DEFINITIONS_PATH.exists() else "down",
    }
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("web")


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


def _is_safe_redirect_path(value: str) -> bool:
    """Validate that a redirect target is a safe relative path (not an open redirect)."""
    if not value.startswith("/"):
        return False
    # Block protocol-relative URLs (//evil.com) and backslash tricks
    if value.startswith("//") or value.startswith("/\\"):
        return False
    # Block URLs with embedded credentials or schemes
    if "://" in value or "@" in value:
        return False
    return True


def _validate_project_id(value: str | None) -> str | None:
    """Validate project_id is alphanumeric with hyphens/underscores only."""
    if value is None:
        return None
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", value):
        return None
    return value


def _resolve_post_login_redirect(state_payload: dict[str, Any]) -> str:
    return_to = state_payload.get("return_to")
    if isinstance(return_to, str) and _is_safe_redirect_path(return_to):
        landing = return_to
        post_login_landing_success_total.add(
            1,
            {
                "flow": "return_to",
                "landing_route": landing,
            },
        )
        logger.info(
            "auth.post_login_landing",
            extra={
                "flow": "return_to",
                "requested_return_to": return_to,
                "landing_route": landing,
            },
        )
        return landing

    project_id = state_payload.get("project_id")
    if project_id:
        landing = f"/app/projects/{project_id}"
        post_login_landing_success_total.add(
            1,
            {
                "flow": "project_id",
                "landing_route": landing,
            },
        )
        logger.info(
            "auth.post_login_landing",
            extra={
                "flow": "project_id",
                "project_id": project_id,
                "landing_route": landing,
            },
        )
        return landing

    landing = "/app"
    post_login_landing_success_total.add(
        1,
        {
            "flow": "default",
            "landing_route": landing,
        },
    )
    logger.info(
        "auth.post_login_landing",
        extra={
            "flow": "default",
            "landing_route": landing,
        },
    )
    return landing


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
                icon="navigation.next",
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
                icon="navigation.next",
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
                icon="ai.suggestion",
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
            icon="artifact.dashboard",
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
    *,
    tenant_id: str,
    user_id: str | None,
) -> list[AssistantSuggestion]:
    llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
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

    provider, model_id = (
        (payload.provider, payload.model_id)
        if payload.provider and payload.model_id
        else _resolve_llm_selection(tenant_id, payload.project_id, user_id)
    )
    response = await llm.complete(
        system_prompt=system_prompt, user_prompt=user_prompt, provider=provider, model_id=model_id
    )
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
        except Exception:  # pragma: no cover - defensive parsing  # noqa: BLE001
            logger.debug("Skipping unparseable suggestion item: %s", item)
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
    roles = _normalize_role_ids(_roles_from_request(request, session))
    return bool(roles.intersection({"PMO_ADMIN"}))


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


def _normalize_demand_payload(payload: dict[str, Any], *, document_name: str) -> dict[str, Any]:
    title = _coerce_str(payload.get("title")) or document_name or "Untitled demand"
    description = _coerce_str(payload.get("description")) or title
    business_objective = (
        _coerce_str(payload.get("business_objective")) or "Pending business objective"
    )
    urgency = _coerce_str(payload.get("urgency"))
    if urgency not in {"Low", "Medium", "High", "Critical"}:
        urgency = ""
    return {
        "title": title,
        "description": description,
        "business_objective": business_objective,
        "requester": _coerce_str(payload.get("requester")),
        "business_unit": _coerce_str(payload.get("business_unit")),
        "urgency": urgency,
        "source": _coerce_str(payload.get("source")),
    }


def _normalize_date(value: Any) -> str | None:
    text = _coerce_str(value)
    if not text:
        return None
    match = re.match(r"^\d{4}-\d{2}-\d{2}$", text)
    if match:
        return text
    return None


def _normalize_project_payload(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    document_name: str,
    owner_fallback: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    name = _coerce_str(payload.get("name")) or document_name or "Untitled project"
    status = _coerce_str(payload.get("status")) or "initiated"
    if status not in {"initiated", "planning", "execution", "monitoring", "closed"}:
        status = "initiated"
    classification = _coerce_str(payload.get("classification")) or "internal"
    if classification not in {"public", "internal", "confidential", "restricted"}:
        classification = "internal"
    start_date = _normalize_date(payload.get("start_date")) or now.date().isoformat()
    end_date = _normalize_date(payload.get("end_date"))
    project: dict[str, Any] = {
        "id": _coerce_str(payload.get("id")) or str(uuid4()),
        "tenant_id": tenant_id,
        "program_id": _coerce_str(payload.get("program_id")) or "unassigned",
        "name": name,
        "status": status,
        "start_date": start_date,
        "owner": _coerce_str(payload.get("owner")) or owner_fallback,
        "classification": classification,
        "created_at": _coerce_str(payload.get("created_at")) or now.isoformat(),
    }
    if end_date:
        project["end_date"] = end_date
    updated_at = _coerce_str(payload.get("updated_at"))
    if updated_at:
        project["updated_at"] = updated_at
    return project


def _decode_upload_content(content: bytes) -> tuple[str, str]:
    if b"\x00" in content:
        return base64.b64encode(content).decode("utf-8"), "base64"
    try:
        return content.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return base64.b64encode(content).decode("utf-8"), "base64"


async def _extract_intake_fields(
    *,
    prompt_path: Path,
    document_name: str,
    document_content: str,
) -> dict[str, Any]:
    prompt = _load_prompt(prompt_path)
    prompt_body = prompt.get("prompt", {})
    system_prompt = str(prompt_body.get("system", "")).strip()
    user_prompt = _render_prompt(
        str(prompt_body.get("user", "")),
        document_name=document_name,
        document_content=document_content,
    )
    llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
    response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response was not JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM response was not an object")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


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


class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        endpoint = request.scope.get("endpoint")
        required = getattr(endpoint, "required_permissions", None)
        if required:
            session = _session_from_request(request)
            if not session:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            permissions = _permissions_for_user(request, session)
            if not permissions.intersection(required):
                return JSONResponse(status_code=403, content={"detail": "Permission denied"})
        return await call_next(request)


app.add_middleware(PermissionMiddleware)


class DemoAutoSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _demo_mode_enabled():
            return await call_next(request)

        if request.url.path not in {"/", "/app"}:
            return await call_next(request)

        if _session_from_request(request):
            return await call_next(request)

        response = RedirectResponse(url="/app?project_id=demo-predictive", status_code=307)
        response.set_cookie(
            SESSION_COOKIE,
            _encode_cookie(_demo_session_payload(), 8 * 60 * 60),
            httponly=True,
            secure=_cookie_secure(),
            samesite="lax",
        )
        return response


app.add_middleware(DemoAutoSessionMiddleware)


def _detect_workflow_cycles(nodes: list[str], edges: list[tuple[str, str]]) -> bool:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for source, target in edges:
        if source in adjacency:
            adjacency[source].append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for neighbor in adjacency.get(node_id, []):
            if visit(neighbor):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in nodes)


def _validate_workflow_payload(payload: WorkflowDefinitionPayload) -> None:
    if not payload.nodes:
        raise HTTPException(status_code=422, detail="Workflow must include at least one node")
    node_ids = {node.id for node in payload.nodes}
    missing_refs = [
        edge for edge in payload.edges if edge.source not in node_ids or edge.target not in node_ids
    ]
    if missing_refs:
        raise HTTPException(status_code=422, detail="Workflow contains edges to unknown nodes")
    edges = [(edge.source, edge.target) for edge in payload.edges]
    if _detect_workflow_cycles(list(node_ids), edges):
        raise HTTPException(status_code=422, detail="Workflow contains a cycle")
    for node in payload.nodes:
        if node.data.step_type in {"task", "api"} and not (node.data.agent_id and node.data.action):
            raise HTTPException(
                status_code=422,
                detail=f"Node '{node.id}' requires agent and action configuration",
            )
        if node.data.step_type == "decision" and not (
            node.data.condition and node.data.condition.field.strip()
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Node '{node.id}' requires a condition for decision logic",
            )


async def _sync_workflow_definition(
    request: Request, workflow_id: str, definition: dict[str, Any]
) -> None:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.put(
                f"{workflow_url}/v1/workflows/definitions/{workflow_id}",
                headers={
                    "Authorization": f"Bearer {session['access_token']}",
                    "X-Tenant-ID": session["tenant_id"],
                },
                json={"definition": definition},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to sync workflow definition", exc_info=exc)


async def _delete_workflow_definition(request: Request, workflow_id: str) -> None:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.delete(
                f"{workflow_url}/v1/workflows/definitions/{workflow_id}",
                headers={
                    "Authorization": f"Bearer {session['access_token']}",
                    "X-Tenant-ID": session["tenant_id"],
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to delete workflow definition", exc_info=exc)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return load_yaml_config(path) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _load_methodology_storage() -> dict[str, Any]:
    return _load_json(METHODOLOGY_STORAGE_PATH, {"methodologies": {}})


def _load_exit_criteria_from_yaml(methodology_id: str) -> list[list[str]]:
    payload = _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "map.yaml")
    stages = payload.get("stages", [])
    return [stage.get("exit_criteria", []) for stage in stages if isinstance(stage, dict)]


def _load_gates_from_yaml(methodology_id: str) -> list[dict[str, Any]]:
    payload = _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "gates.yaml")
    gates = payload.get("gates", [])
    return [gate for gate in gates if isinstance(gate, dict)]


def _build_methodology_editor_payload(methodology_id: str) -> MethodologyEditorPayload:
    storage = _load_methodology_storage()
    stored_entry = storage.get("methodologies", {}).get(methodology_id, {})
    stored_map = stored_entry.get("map") if isinstance(stored_entry, dict) else None
    stored_gates = stored_entry.get("gates") if isinstance(stored_entry, dict) else None

    methodology_map = stored_map or get_default_methodology_map(methodology_id)
    gates = stored_gates or _load_gates_from_yaml(methodology_id)
    exit_criteria_defaults = _load_exit_criteria_from_yaml(methodology_id)

    stages: list[MethodologyStageEditor] = []
    for index, stage in enumerate(methodology_map.get("stages", [])):
        exit_criteria = stage.get("exit_criteria")
        if exit_criteria is None:
            exit_criteria = (
                exit_criteria_defaults[index] if index < len(exit_criteria_defaults) else []
            )
        activities: list[MethodologyActivityEditor] = []
        for activity in stage.get("activities", []):
            activities.append(
                MethodologyActivityEditor(
                    id=activity.get("id", ""),
                    name=activity.get("name", ""),
                    description=activity.get("description", ""),
                    prerequisites=activity.get("prerequisites", []),
                    category=activity.get("category", "methodology"),
                    recommended_canvas_tab=activity.get("recommended_canvas_tab", "document"),
                )
            )
        stages.append(
            MethodologyStageEditor(
                id=stage.get("id", ""),
                name=stage.get("name", ""),
                exit_criteria=exit_criteria,
                activities=activities,
            )
        )

    gates_payload = [
        MethodologyGateEditor(
            id=gate.get("id", ""),
            name=gate.get("name", ""),
            stage=gate.get("stage", ""),
            criteria=[
                MethodologyGateCriteriaEditor(
                    id=criterion.get("id", ""),
                    description=criterion.get("description", ""),
                    evidence=criterion.get("evidence"),
                    check=criterion.get("check"),
                )
                for criterion in gate.get("criteria", [])
                if isinstance(criterion, dict)
            ],
        )
        for gate in gates
        if isinstance(gate, dict)
    ]

    return MethodologyEditorPayload(
        methodology_id=methodology_id,
        stages=stages,
        gates=gates_payload,
    )


def _validate_methodology_prereqs(stages: list[MethodologyStageEditor]) -> None:
    activity_ids = {activity.id for stage in stages for activity in stage.activities if activity.id}
    invalid: list[str] = []
    for stage in stages:
        for activity in stage.activities:
            for prereq in activity.prerequisites:
                if prereq not in activity_ids:
                    invalid.append(f"{activity.id}:{prereq}")
    if invalid:
        raise HTTPException(
            status_code=422,
            detail="Invalid prerequisites: " + ", ".join(sorted(invalid)),
        )


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


_METHODOLOGY_ALIASES = {
    "adaptive": "adaptive",
    "predictive": "predictive",
    "methodology-adaptive": "adaptive",
    "methodology-predictive": "predictive",
}


def _resolve_template_methodology_id(template: TemplateDefinition) -> str:
    raw_id = str(template.methodology.get("id") or "").strip().lower()
    raw_type = str(template.methodology.get("type") or "").strip().lower()
    candidate = raw_id or raw_type
    normalized = _METHODOLOGY_ALIASES.get(candidate, candidate)
    methodology_map = get_methodology_map(normalized)
    return str(methodology_map.get("id", normalized))


def _load_projects() -> list[ProjectRecord]:
    payload = _load_json(PROJECTS_PATH, {"projects": []})
    return [ProjectRecord.model_validate(item) for item in payload.get("projects", [])]


def _build_activity_summary(
    methodology_map: dict[str, Any],
    state: WorkspaceState,
    activity: dict[str, Any],
) -> ActivitySummary:
    access_payload = evaluate_activity_access(methodology_map, state, activity["id"])
    activity_metadata = activity.get("metadata", {})
    return ActivitySummary(
        id=activity["id"],
        name=activity["name"],
        description=activity["description"],
        prerequisites=activity.get("prerequisites", []),
        category=activity["category"],
        recommended_canvas_tab=activity["recommended_canvas_tab"],
        assistant_prompts=activity.get("assistant_prompts", []),
        template_id=activity_metadata.get("template_id"),
        agent_id=activity_metadata.get("agent_id"),
        connector_id=activity_metadata.get("connector_id"),
        access=ActivityAccessSummary(**access_payload),
        completed=state.activity_completion.get(activity["id"], False),
        children=[
            _build_activity_summary(methodology_map, state, child)
            for child in activity.get("children", []) or []
        ],
    )


def _find_activity_by_id(
    activities: list[dict[str, Any]], activity_id: str
) -> dict[str, Any] | None:
    for activity in activities:
        if activity.get("id") == activity_id:
            return activity
        match = _find_activity_by_id(activity.get("children", []) or [], activity_id)
        if match:
            return match
    return None


def _build_workspace_response(state: WorkspaceState) -> WorkspaceStateResponse:
    methodology_map = get_methodology_map(state.methodology)

    selected_stage_id = state.current_stage_id
    selected_activity_id = state.current_activity_id
    methodology_id = str(methodology_map.get("id", state.methodology or ""))
    available_here = (
        list_templates_for_methodology_node(
            methodology_id,
            selected_stage_id,
            selected_activity_id,
            task_id=None,
            lifecycle_event=None,
        )
        if selected_stage_id and selected_activity_id
        else []
    )
    required_here = [
        mapping
        for mapping in available_here
        if any(
            binding.required
            for binding in mapping.methodology_bindings
            if binding.methodology_id == methodology_id
            and binding.stage_id == selected_stage_id
            and binding.activity_id == selected_activity_id
        )
    ]
    review_here = (
        list_templates_for_methodology_node(
            methodology_id,
            selected_stage_id,
            selected_activity_id,
            task_id=None,
            lifecycle_event="review",
        )
        if selected_stage_id and selected_activity_id
        else []
    )

    stage_summaries: list[StageSummary] = []
    for stage in methodology_map.get("stages", []):
        activities: list[ActivitySummary] = [
            _build_activity_summary(methodology_map, state, activity)
            for activity in stage.get("activities", [])
        ]
        stage_summaries.append(
            StageSummary(
                id=stage["id"],
                name=stage["name"],
                progress=StageProgressSummary(
                    **stage_progress(methodology_map, state, stage["id"])
                ),
                activities=activities,
            )
        )

    monitoring_summaries: list[ActivitySummary] = [
        _build_activity_summary(methodology_map, state, activity)
        for activity in methodology_map.get("monitoring", [])
    ]

    selected_activity_payload: SelectedActivitySummary | None = None
    if state.current_activity_id:
        activity_lookup = None
        for stage in methodology_map.get("stages", []):
            activity_lookup = _find_activity_by_id(
                stage.get("activities", []),
                state.current_activity_id,
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
            selected_metadata = activity_lookup.get("metadata", {})
            selected_activity_payload = SelectedActivitySummary(
                id=activity_lookup["id"],
                name=activity_lookup["name"],
                description=activity_lookup["description"],
                assistant_prompts=activity_lookup.get("assistant_prompts", []),
                recommended_canvas_tab=activity_lookup["recommended_canvas_tab"],
                category=activity_lookup["category"],
                template_id=selected_metadata.get("template_id"),
                agent_id=selected_metadata.get("agent_id"),
                connector_id=selected_metadata.get("connector_id"),
            )

    current_access = (
        evaluate_activity_access(methodology_map, state, state.current_activity_id)
        if state.current_activity_id
        else {"allowed": True, "reasons": [], "missing_prereqs": []}
    )
    runtime_actions_available: list[str] = []
    runtime_default_view_contract: dict[str, Any] | None = None
    if selected_stage_id:
        runtime_actions_available = list_runtime_actions_for_node(
            methodology_id,
            selected_stage_id,
            selected_activity_id,
            task_id=None,
        )
        if "view" in runtime_actions_available:
            runtime_default_view_contract = resolve_runtime(
                methodology_id,
                selected_stage_id,
                selected_activity_id,
                task_id=None,
                lifecycle_event="view",
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
        templates_available_here=available_here,
        templates_required_here=required_here,
        templates_in_review=review_here,
        runtime_actions_available=runtime_actions_available,
        runtime_default_view_contract=runtime_default_view_contract,
    )


async def run_methodology_node_action(
    workspace_id: str,
    methodology_id: str,
    stage_id: str,
    activity_id: str | None,
    task_id: str | None,
    lifecycle_event: str,
    user_input: dict[str, Any],
) -> dict[str, Any]:
    resolution_contract = resolve_runtime(
        methodology_id,
        stage_id,
        activity_id,
        task_id,
        lifecycle_event,
    )
    correlation_basis = "::".join(
        [
            workspace_id,
            methodology_id,
            stage_id,
            activity_id or "-",
            task_id or "-",
            lifecycle_event,
            ",".join(resolution_contract.get("template_ids", [])),
            str(user_input.get("request_id") or datetime.now(tz=timezone.utc).isoformat()),
        ]
    )
    correlation_id = str(uuid5(NAMESPACE_URL, correlation_basis))

    workspace_state = workspace_state_store.get_or_create("default", workspace_id)
    actor_id = str(user_input.get("actor_id") or "ui-user")

    get_audit_log_store().record_event(
        build_event(
            tenant_id=workspace_state.tenant_id,
            actor_id=actor_id,
            actor_type="user",
            roles=["project_member"],
            action=f"methodology.lifecycle.{lifecycle_event}.requested",
            resource_type="workspace",
            resource_id=workspace_id,
            outcome="success",
            metadata={
                "stage_id": stage_id,
                "activity_id": activity_id,
                "correlation_id": correlation_id,
            },
        )
    )

    escalation_rules = (
        resolution_contract.get("assistant", {})
        .get("response_contract", {})
        .get("escalation_rules", [])
    )
    needs_human_review = (
        resolution_contract.get("agent_workflow", {}).get("human_review_required", False)
        or lifecycle_event in {"review", "approve", "publish"}
        or any(
            "publish_external" in str(rule).lower() and "approve" in str(rule).lower()
            for rule in escalation_rules
        )
    )

    if needs_human_review and not user_input.get("human_review_approved"):
        approval_id = f"apr-{uuid4().hex[:10]}"
        runtime_lifecycle_store.create_approval(
            tenant_id=workspace_state.tenant_id,
            workspace_id=workspace_id,
            approval={
                "approval_id": approval_id,
                "workspace_id": workspace_id,
                "methodology_id": methodology_id,
                "stage_id": stage_id,
                "activity_id": activity_id,
                "requested_event": lifecycle_event,
                "status": "pending",
                "requested_at": datetime.now(tz=timezone.utc).isoformat(),
                "requested_by": actor_id,
                "notes": user_input.get("notes"),
                "history": [
                    {
                        "action": "requested",
                        "actor": actor_id,
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    }
                ],
            },
        )
        get_audit_log_store().record_event(
            build_event(
                tenant_id=workspace_state.tenant_id,
                actor_id=actor_id,
                actor_type="user",
                roles=["project_member"],
                action="methodology.lifecycle.review.queued",
                resource_type="approval",
                resource_id=approval_id,
                outcome="success",
                metadata={"requested_event": lifecycle_event, "correlation_id": correlation_id},
            )
        )
        return {
            "workspace_id": workspace_id,
            "lifecycle_event": lifecycle_event,
            "resolution_contract": resolution_contract,
            "assistant_response": {
                "intent_id": resolution_contract["assistant"]["intent_id"],
                "output_format": resolution_contract["assistant"]["response_contract"][
                    "output_format"
                ],
                "validation_checklist": resolution_contract["assistant"]["response_contract"][
                    "validation_checklist"
                ],
                "content": "Human review is required before this lifecycle action can proceed.",
            },
            "artifacts_created": [],
            "artifacts_updated": [],
            "connector_operations": [],
            "workflow_trace": {
                "correlation_id": correlation_id,
                "agent_ids_executed": [],
                "started_at": datetime.now(tz=timezone.utc).isoformat(),
                "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            "human_review": {
                "status": "pending",
                "required": True,
                "approval_id": approval_id,
                "next_step": "Resolve in approval inbox then rerun with human_review_approved=true.",
            },
            "status": "review_required",
        }

    context_refs: dict[str, Any] = {
        "workspace_id": workspace_id,
        "project_id": workspace_id,
        "methodology_id": methodology_id,
        "stage_id": stage_id,
        "activity_id": activity_id,
        "task_id": task_id,
        "lifecycle_event": lifecycle_event,
        "connector_bindings": resolution_contract.get("connectors", {}),
        "selected_canvas": resolution_contract.get("canvas", {}),
        "workspace_context": workspace_state.model_dump(mode="json"),
        "user_input": user_input,
        "correlation_id": correlation_id,
    }

    orchestrator = Orchestrator()
    started_at = datetime.now(tz=timezone.utc).isoformat()
    orchestration_result = await orchestrator.run_methodology_node_action(
        methodology_id=methodology_id,
        stage_id=stage_id,
        activity_id=activity_id,
        task_id=task_id,
        lifecycle_event=lifecycle_event,
        template_ids=resolution_contract.get("template_ids", []),
        context_refs=context_refs,
    )
    completed_at = datetime.now(tz=timezone.utc).isoformat()

    connector_operations: list[dict[str, Any]] = []
    agent_ids_executed: list[str] = []
    for task_payload in orchestration_result.results.values():
        connector_operations.append(
            {
                "connector_binding": task_payload.get("input", {}).get("connector_binding"),
                "side_effects": task_payload.get("input", {}).get("side_effects", []),
            }
        )
        agent_id = task_payload.get("agent_id")
        if agent_id:
            agent_ids_executed.append(agent_id)

    canvas_type = resolution_contract.get("canvas", {}).get("canvas_type", "document")
    artifact_id = f"artifact::{workspace_id}::{methodology_id}::{stage_id}::{activity_id or 'activity'}::{canvas_type}"
    lifecycle_state = "published" if lifecycle_event == "publish" else "draft"
    artifact_ref = runtime_lifecycle_store.upsert_artifact(
        tenant_id=workspace_state.tenant_id,
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        artifact={
            "workspace_id": workspace_id,
            "methodology_id": methodology_id,
            "stage_id": stage_id,
            "activity_id": activity_id,
            "canvas_type": canvas_type,
            "status": lifecycle_state,
            "title": (activity_id or stage_id).replace("-", " ").title(),
            "metadata": {
                "correlation_id": correlation_id,
                "lifecycle_event": lifecycle_event,
                "connector_operations": connector_operations,
            },
        },
    )

    if lifecycle_event == "publish":
        destinations = _collect_sor_destinations(resolution_contract)
        change_payload = {
            "artifact_id": artifact_id,
            "status": lifecycle_state,
            "metadata": artifact_ref.get("metadata", {}),
        }
        if _demo_mode_enabled():
            demo_outbox.append(
                "external_side_effects",
                {
                    "workspace_id": workspace_id,
                    "lifecycle_event": lifecycle_event,
                    "destinations": destinations,
                    "changes": change_payload,
                    "status": "captured_in_demo_outbox",
                    "captured_at": completed_at,
                },
            )
        else:
            connector_operations.append(
                {
                    "connector_binding": {"destinations": destinations},
                    "side_effects": ["publish_external"],
                    "status": "submitted_to_sor",
                }
            )

    output_format = resolution_contract["assistant"]["response_contract"]["output_format"]
    assistant_content: Any
    if output_format == "json":
        assistant_content = {
            "templates": resolution_contract.get("template_ids", []),
            "results": orchestration_result.results,
            "artifact_reference": artifact_ref,
        }
    else:
        assistant_content = f"Executed {lifecycle_event} and persisted artifact {artifact_id}."

    get_audit_log_store().record_event(
        build_event(
            tenant_id=workspace_state.tenant_id,
            actor_id=actor_id,
            actor_type="user",
            roles=["project_member"],
            action=f"methodology.lifecycle.{lifecycle_event}.completed",
            resource_type="artifact",
            resource_id=artifact_id,
            outcome="success",
            metadata={"correlation_id": correlation_id, "state": lifecycle_state},
        )
    )

    sor_sources = _collect_sor_sources(resolution_contract)
    sor_preview = _build_sor_preview_rows(sor_sources)
    return {
        "workspace_id": workspace_id,
        "lifecycle_event": lifecycle_event,
        "resolution_contract": resolution_contract,
        "assistant_response": {
            "intent_id": resolution_contract["assistant"]["intent_id"],
            "output_format": output_format,
            "validation_checklist": resolution_contract["assistant"]["response_contract"][
                "validation_checklist"
            ],
            "content": assistant_content,
        },
        "artifacts_created": [artifact_ref] if lifecycle_event == "generate" else [],
        "artifacts_updated": (
            [artifact_ref] if lifecycle_event in {"update", "review", "approve", "publish"} else []
        ),
        "connector_operations": connector_operations,
        "sor_preview": {"sources": sor_sources, "preview_rows": sor_preview},
        "workflow_trace": {
            "correlation_id": correlation_id,
            "agent_ids_executed": agent_ids_executed,
            "started_at": started_at,
            "completed_at": completed_at,
        },
        "human_review": {
            "status": "approved" if user_input.get("human_review_approved") else "not_required",
            "required": needs_human_review,
        },
        "status": "completed",
    }


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

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("OIDC token exchange failed: status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="OIDC token exchange failed") from exc
    except httpx.RequestError as exc:
        logger.error("OIDC token exchange request error: %s", exc)
        raise HTTPException(status_code=502, detail="OIDC provider unreachable") from exc


async def _decode_id_token(id_token: str) -> dict[str, Any]:
    jwks_url = _oidc_required("OIDC_JWKS_URL")
    audience = os.getenv("OIDC_AUDIENCE")
    issuer = os.getenv("OIDC_ISSUER")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("OIDC JWKS fetch failed: status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="OIDC JWKS fetch failed") from exc
    except httpx.RequestError as exc:
        logger.error("OIDC JWKS request error: %s", exc)
        raise HTTPException(status_code=502, detail="OIDC JWKS endpoint unreachable") from exc

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


def _ui_feature_flags() -> dict[str, bool]:
    environment = os.getenv("ENVIRONMENT", "dev")
    return {
        "agent_run_ui": is_feature_enabled("agent_run_ui", environment=environment, default=False),
        "multimodal_intake": is_feature_enabled(
            "multimodal_intake", environment=environment, default=False
        ),
        "duplicate_resolution": is_feature_enabled(
            "duplicate_resolution", environment=environment, default=False
        ),
        "predictive_alerts": is_feature_enabled(
            "predictive_alerts", environment=environment, default=False
        ),
        "resource_optimization": is_feature_enabled(
            "resource_optimization", environment=environment, default=False
        ),
        "multi_agent_collab": is_feature_enabled(
            "multi_agent_collab", environment=environment, default=False
        ),
        "autonomous_deliverables": is_feature_enabled(
            "autonomous_deliverables", environment=environment, default=False
        ),
        "unified_dashboards": is_feature_enabled(
            "unified_dashboards", environment=environment, default=False
        ),
    }


@api_router.get("/config", response_model=UIConfig)
async def config() -> UIConfig:
    return UIConfig(
        api_gateway_url=os.getenv("API_GATEWAY_URL", "http://api-gateway:8000"),
        workflow_engine_url=os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082"),
        oidc_enabled=_oidc_enabled(),
        login_url="/login",
        logout_url="/logout",
        feature_flags=_ui_feature_flags(),
    )


@api_router.get("/session", response_model=SessionInfo)
async def session_info(request: Request) -> SessionInfo:
    session = _session_from_request(request)
    if not session:
        return SessionInfo(authenticated=False)
    return SessionInfo(
        authenticated=True,
        subject=session.get("subject"),
        tenant_id=session.get("tenant_id"),
        roles=session.get("roles"),
        permissions=session.get("permissions"),
    )


@api_router.get("/api/roles", response_model=list[RoleDefinition])
async def list_roles(request: Request) -> list[RoleDefinition]:
    _require_session(request)
    return _list_roles()


@api_router.post("/api/roles", response_model=RoleDefinition, status_code=201)
@permission_required("roles.manage")
async def create_role(payload: RoleDefinition) -> RoleDefinition:
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    existing_index = next((idx for idx, role in enumerate(roles) if role.id == payload.id), None)
    if existing_index is None:
        roles.append(payload)
    else:
        roles[existing_index] = payload
    _write_json(
        ROLES_PATH,
        {
            "roles": [role.model_dump() for role in roles],
            "assignments": roles_payload.get("assignments", []),
        },
    )
    return payload


@api_router.put("/api/roles/{role_id}", response_model=RoleDefinition)
@permission_required("roles.manage")
async def update_role(role_id: str, payload: RoleDefinition) -> RoleDefinition:
    if role_id != payload.id:
        raise HTTPException(status_code=422, detail="Role ID mismatch")
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    existing_index = next((idx for idx, role in enumerate(roles) if role.id == role_id), None)
    if existing_index is None:
        raise HTTPException(status_code=404, detail="Role not found")
    roles[existing_index] = payload
    _write_json(
        ROLES_PATH,
        {
            "roles": [role.model_dump() for role in roles],
            "assignments": roles_payload.get("assignments", []),
        },
    )
    return payload


@api_router.delete("/api/roles/{role_id}", status_code=204)
@permission_required("roles.manage")
async def delete_role(role_id: str) -> Response:
    roles_payload = _load_roles_payload()
    roles = [RoleDefinition.model_validate(item) for item in roles_payload.get("roles", [])]
    updated_roles = [role for role in roles if role.id != role_id]
    if len(updated_roles) == len(roles):
        raise HTTPException(status_code=404, detail="Role not found")
    assignments = [
        RoleAssignment.model_validate(item) for item in roles_payload.get("assignments", [])
    ]
    for assignment in assignments:
        assignment.role_ids = [rid for rid in assignment.role_ids if rid != role_id]
    _write_json(
        ROLES_PATH,
        {
            "roles": [role.model_dump() for role in updated_roles],
            "assignments": [assignment.model_dump() for assignment in assignments],
        },
    )
    return Response(status_code=204)


@api_router.get("/api/roles/assignments", response_model=list[RoleAssignment])
@permission_required("roles.manage")
async def list_role_assignments(request: Request) -> list[RoleAssignment]:
    _require_session(request)
    return _list_role_assignments()


@api_router.post("/api/roles/assignments", response_model=RoleAssignment)
@permission_required("roles.manage")
async def upsert_role_assignment(payload: RoleAssignment) -> RoleAssignment:
    roles_payload = _load_roles_payload()
    roles = roles_payload.get("roles", [])
    assignments = [
        RoleAssignment.model_validate(item) for item in roles_payload.get("assignments", [])
    ]
    existing_index = next(
        (
            idx
            for idx, assignment in enumerate(assignments)
            if assignment.user_id == payload.user_id
        ),
        None,
    )
    if existing_index is None:
        assignments.append(payload)
    else:
        assignments[existing_index] = payload
    _write_json(
        ROLES_PATH,
        {
            "roles": roles,
            "assignments": [assignment.model_dump() for assignment in assignments],
        },
    )
    return payload


@api_router.get("/login")
async def login(request: Request) -> RedirectResponse:
    if not _oidc_enabled():
        if _legacy_oidc_enabled():
            auth_url = _oidc_required("OIDC_AUTH_URL")
            client_id = _oidc_required("OIDC_CLIENT_ID")
            redirect_uri = _oidc_required("OIDC_REDIRECT_URI")
            state = _random_token_urlsafe(16)
            nonce = _random_token_urlsafe(16)
            project_id = _validate_project_id(request.query_params.get("project_id"))
            return_to = request.query_params.get("return_to")
            if return_to and not _is_safe_redirect_path(return_to):
                return_to = None
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
                _encode_cookie(
                    {
                        "state": state,
                        "nonce": nonce,
                        "project_id": project_id,
                        "return_to": return_to,
                    },
                    600,
                ),
                httponly=True,
                secure=_cookie_secure(),
                samesite="lax",
            )
            return response

        auth_dev_mode = os.getenv("AUTH_DEV_MODE", "false").lower() in {"1", "true", "yes"}
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if auth_dev_mode and environment in {"dev", "development", "local", "test"}:
            return RedirectResponse(url="/app")
        raise HTTPException(status_code=500, detail="OIDC not configured")

    client = _oidc_client()
    discovery = await client.discover()
    state = _random_token_urlsafe(16)
    nonce = _random_token_urlsafe(16)
    project_id = _validate_project_id(request.query_params.get("project_id"))
    return_to = request.query_params.get("return_to")
    if return_to and not _is_safe_redirect_path(return_to):
        return_to = None

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
        _encode_cookie(
            {
                "state": state,
                "nonce": nonce,
                "project_id": project_id,
                "return_to": return_to,
            },
            600,
        ),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    return response


@api_router.get("/oidc/callback")
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
    redirect_target = _resolve_post_login_redirect(state_payload)
    response = RedirectResponse(url=redirect_target)
    response.set_cookie(
        SESSION_COOKIE,
        _encode_cookie(session_payload, 8 * 60 * 60),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    response.delete_cookie(STATE_COOKIE)
    return response


@api_router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    return await oidc_callback(request)


@api_router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    session = _session_from_request(request) or {}
    response = RedirectResponse(url="/")
    discovery = None
    if _oidc_enabled():
        client = _oidc_client()
        discovery = await client.discover()
    if discovery and discovery.end_session_endpoint and session.get("id_token"):
        params = {"id_token_hint": session["id_token"]}
        response = RedirectResponse(url=f"{discovery.end_session_endpoint}?{urlencode(params)}")
    elif _legacy_oidc_enabled():
        logout_url = os.getenv("OIDC_LOGOUT_URL")
        if logout_url:
            response = RedirectResponse(url=logout_url)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(STATE_COOKIE)
    return response


@api_router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    session = _require_session(request)
    api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_gateway_url}/v1/status",
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "X-Tenant-ID": session["tenant_id"],
            },
        )
        response.raise_for_status()
        return response.json()


@api_router.get("/approvals", response_model=None)
async def approvals_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/approvals"), status_code=307)


@api_router.get("/workflow-monitoring", response_model=None)
async def workflow_monitoring_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/workflows/monitoring"), status_code=307)


@api_router.get("/document-search", response_model=None)
async def document_search_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/knowledge/documents"), status_code=307)


@api_router.get("/lessons-learned", response_model=None)
async def lessons_learned_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/knowledge/lessons"), status_code=307)


@api_router.get("/audit-log", response_model=None)
async def audit_log_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/admin/audit"), status_code=307)


@api_router.get("/api/approvals")
async def approvals_feed() -> dict[str, Any]:
    return _approval_payload()


@api_router.get("/api/methodology/runtime/approvals")
async def get_runtime_approvals(
    workspace_id: str, request: Request, status: str = "pending"
) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    items = runtime_lifecycle_store.list_approvals(
        tenant_id=tenant_id, workspace_id=workspace_id, status=status
    )
    if _demo_mode_enabled() and not items and status == "pending":
        items = [
            {
                "approval_id": "demo-approval-1",
                "workspace_id": workspace_id,
                "methodology_id": "adaptive",
                "stage_id": "demo-stage",
                "activity_id": "demo-activity",
                "requested_event": "publish",
                "status": "pending",
                "requested_at": datetime.now(tz=timezone.utc).isoformat(),
                "requested_by": "demo-user",
                "notes": "Seeded approval for demo lifecycle walkthrough.",
                "history": [],
            }
        ]
    return {"items": items}


@api_router.post("/api/methodology/runtime/approvals/{approval_id}/decision")
async def decide_runtime_approval(
    approval_id: str, payload: RuntimeApprovalDecisionRequest, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    actor_id = session.get("subject") or "ui-user"
    decision = runtime_lifecycle_store.decide_approval(
        tenant_id=tenant_id,
        workspace_id=payload.workspace_id,
        approval_id=approval_id,
        decision=payload.decision,
        actor=actor_id,
        notes=payload.notes,
    )
    if not decision:
        raise HTTPException(status_code=404, detail="Approval not found")

    get_audit_log_store().record_event(
        build_event(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type="user",
            roles=["approver"],
            action=f"methodology.lifecycle.approval.{payload.decision}",
            resource_type="approval",
            resource_id=approval_id,
            outcome="success",
            metadata={"workspace_id": payload.workspace_id, "notes": payload.notes},
        )
    )
    return decision


@api_router.get("/api/workflow-monitoring")
async def workflow_monitoring_feed() -> dict[str, Any]:
    return {
        "status_board": {"healthy": 18, "warning": 4, "failed": 2},
        "runs": [
            {
                "id": "WF-2041",
                "name": "Intake Routing",
                "status": "Success",
                "duration": "2m 12s",
                "agent": "Intake",
            },
            {
                "id": "WF-2042",
                "name": "Approval Escalation",
                "status": "Failed",
                "duration": "4m 50s",
                "agent": "Governance",
            },
            {
                "id": "WF-2043",
                "name": "Document Sync",
                "status": "Warning",
                "duration": "9m 03s",
                "agent": "SharePoint",
            },
        ],
        "bottlenecks": [
            {
                "issue": "Approval Escalation backlog",
                "recommendation": "Reroute to alternate approver",
                "severity": "High",
            },
            {
                "issue": "Document Sync latency",
                "recommendation": "Increase connector concurrency",
                "severity": "Medium",
            },
        ],
    }


@api_router.get("/api/document-search")
async def document_search_feed() -> dict[str, Any]:
    return {
        "query": "business case",
        "filters": {
            "project": "Phoenix",
            "confidentiality": "Confidential",
            "stage": "Initiation",
        },
        "results": [
            {
                "id": "doc-771",
                "title": "Business Case v5",
                "project": "Phoenix",
                "tags": ["ROI", "Approval", "Confidential"],
                "summary": "Latest funding request with revised ROI assumptions.",
            },
            {
                "id": "doc-772",
                "title": "Lessons Learned ▸ Sprint 8",
                "project": "Phoenix",
                "tags": ["Retrospective", "Risk"],
                "summary": "Highlights schedule recovery tactics.",
            },
        ],
        "saved_searches": ["Critical approvals", "Evidence packs"],
    }


@api_router.get("/api/lessons-learned")
async def lessons_learned_feed() -> dict[str, Any]:
    return {
        "categories": ["Schedule", "Scope", "Risk", "Vendor"],
        "entries": [
            {
                "id": "lesson-201",
                "title": "Sprint 8 Retrospective",
                "status": "Applied 3x",
                "theme": "Schedule",
                "severity": "Medium",
            },
            {
                "id": "lesson-202",
                "title": "Vendor Delay Mitigation",
                "status": "Applied 1x",
                "theme": "Vendor",
                "severity": "High",
            },
        ],
        "recommendations": [
            {
                "title": "Contractual lead times",
                "tags": ["Procurement", "SLA", "Risk"],
                "adoption": "Reviewed",
            }
        ],
    }


@api_router.get("/api/audit-log")
async def audit_log_feed() -> dict[str, Any]:
    return {
        "filters": ["Actor", "Action", "Object", "Framework", "Date"],
        "entries": [
            {
                "timestamp": "09:32",
                "action": "Approval",
                "object": "Gate Exit",
                "actor": "A. Lee",
                "source": "Workflow Engine",
                "hash": "a13f9c2",
            },
            {
                "timestamp": "09:14",
                "action": "Workflow Retry",
                "object": "WF-2041",
                "actor": "Orchestrator",
                "source": "Automation",
                "hash": "b82c4d1",
            },
        ],
        "evidence_packs": [
            {
                "id": "pack-7",
                "label": "Q1 Compliance Review",
                "integrity": "SHA256",
            }
        ],
    }


@api_router.get("/ui/migration-map")
async def ui_migration_map() -> dict[str, Any]:
    return {
        "migration_status": {
            "legacy_ui_retired": True,
            "notes": "Legacy UI has been fully retired; compatibility is redirect-only.",
        },
        "routes": [
            {
                "legacy": "/v1/approvals",
                "spa": "/app/approvals",
                "notes": "Approval inbox moved into SPA workflow area.",
            },
            {
                "legacy": "/v1/workflow-monitoring",
                "spa": "/app/workflows/monitoring",
                "notes": "Monitoring now relies on SPA route with live updates.",
            },
            {
                "legacy": "/v1/document-search",
                "spa": "/app/knowledge/documents",
                "notes": "Knowledge document search consolidated in SPA.",
            },
            {
                "legacy": "/v1/lessons-learned",
                "spa": "/app/knowledge/lessons",
                "notes": "Lessons page moved to knowledge section.",
            },
            {
                "legacy": "/v1/audit-log",
                "spa": "/app/admin/audit",
                "notes": "Admin audit access requires admin role in SPA.",
            },
        ],
        "compatibility": {
            "api_endpoints": "Preserved under /v1/api/* and /v1/workflows/*.",
            "legacy_html": "Legacy HTML compatibility removed; routes redirect to SPA.",
        },
    }


@api_router.get("/agent-runs")
async def list_agent_runs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    session = _require_session(request)
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        raise HTTPException(status_code=503, detail="DATA_SERVICE_URL not configured")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "X-Tenant-ID": session["tenant_id"],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{data_service_url}/v1/agent-runs",
            headers=headers,
            params={
                "tenant_id": session["tenant_id"],
                "skip": skip,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()


@api_router.get("/agent-runs/{agent_run_id}")
async def get_agent_run(agent_run_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        raise HTTPException(status_code=503, detail="DATA_SERVICE_URL not configured")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "X-Tenant-ID": session["tenant_id"],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{data_service_url}/v1/agent-runs/{agent_run_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


@api_router.get("/audit/events")
async def list_audit_events(
    request: Request,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    session = _require_session(request)
    return get_audit_log_store().list_events(
        tenant_id=session["tenant_id"],
        limit=limit,
        offset=offset,
    )


@api_router.get("/audit/events/{event_id}")
async def get_audit_event(event_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    audit_url = os.getenv("AUDIT_LOG_SERVICE_URL")
    if audit_url:
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-Tenant-ID": session["tenant_id"],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{audit_url}/audit/events/{event_id}", headers=headers)
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Audit event not found")
            response.raise_for_status()
            return response.json()
    record = get_audit_log_store().get_event(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit event not found")
    if record.get("tenant_id") != session["tenant_id"]:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return record


@api_router.get("/api/methodology/editor", response_model=MethodologyEditorPayload)
@permission_required("methodology.edit")
async def get_methodology_editor(
    request: Request, methodology_id: str | None = None
) -> MethodologyEditorPayload:
    available = available_methodologies()
    if not methodology_id:
        methodology_id = (
            "hybrid" if "hybrid" in available else (available[0] if available else "adaptive")
        )
    if methodology_id not in available:
        raise HTTPException(status_code=404, detail="Methodology not found")
    return _build_methodology_editor_payload(methodology_id)


@api_router.post("/api/methodology/editor", response_model=MethodologyEditorPayload)
@permission_required("methodology.edit")
async def update_methodology_editor(
    payload: MethodologyEditorPayload, request: Request
) -> MethodologyEditorPayload:
    _validate_methodology_prereqs(payload.stages)

    existing_map = get_methodology_map(payload.methodology_id)
    activity_lookup: dict[str, dict[str, Any]] = {}
    for stage in existing_map.get("stages", []):
        for activity in stage.get("activities", []):
            activity_lookup[activity.get("id")] = activity

    stages_payload: list[dict[str, Any]] = []
    for stage in payload.stages:
        stage_activities: list[dict[str, Any]] = []
        for activity in stage.activities:
            existing_activity = activity_lookup.get(activity.id, {})
            stage_activities.append(
                {
                    "id": activity.id,
                    "name": activity.name,
                    "description": activity.description,
                    "assistant_prompts": existing_activity.get("assistant_prompts", []),
                    "prerequisites": activity.prerequisites,
                    "category": activity.category or "methodology",
                    "recommended_canvas_tab": activity.recommended_canvas_tab or "document",
                }
            )
        stages_payload.append(
            {
                "id": stage.id,
                "name": stage.name,
                "activities": stage_activities,
                "exit_criteria": stage.exit_criteria,
            }
        )

    map_payload = {
        "id": existing_map.get("id", payload.methodology_id),
        "name": existing_map.get("name", payload.methodology_id),
        "description": existing_map.get("description", ""),
        "stages": stages_payload,
        "monitoring": existing_map.get("monitoring", []),
    }

    storage = _load_methodology_storage()
    storage.setdefault("methodologies", {})
    storage["methodologies"][payload.methodology_id] = {
        "map": map_payload,
        "gates": [gate.model_dump() for gate in payload.gates],
    }
    _write_json(METHODOLOGY_STORAGE_PATH, storage)
    return _build_methodology_editor_payload(payload.methodology_id)


def _load_sor_fixtures() -> dict[str, Any]:
    if SOR_FIXTURES_PATH.exists():
        return json.loads(SOR_FIXTURES_PATH.read_text(encoding="utf-8"))
    return {"records": []}


def _collect_sor_sources(resolution_contract: dict[str, Any]) -> list[dict[str, Any]]:
    return list(resolution_contract.get("connectors", {}).get("sources", []))


def _collect_sor_destinations(resolution_contract: dict[str, Any]) -> list[dict[str, Any]]:
    return list(resolution_contract.get("connectors", {}).get("destinations", []))


def _build_sor_preview_rows(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixtures = _load_sor_fixtures()
    records = fixtures.get("records", [])
    if not sources:
        return []
    source_types = {src.get("connector_type") for src in sources}
    return [item for item in records if item.get("connector_type") in source_types][:20]


@api_router.get("/api/methodology/runtime/actions")
async def get_methodology_runtime_actions(
    methodology_id: str,
    stage_id: str,
    activity_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "methodology_id": methodology_id,
        "stage_id": stage_id,
        "activity_id": activity_id,
        "task_id": task_id,
        "actions": list_runtime_actions_for_node(
            methodology_id,
            stage_id,
            activity_id,
            task_id,
        ),
    }


@api_router.get(
    "/api/methodology/runtime/resolve", response_model=MethodologyRuntimeResolveResponse
)
async def get_methodology_runtime_resolve(
    methodology_id: str,
    stage_id: str,
    activity_id: str | None = None,
    task_id: str | None = None,
    event: Literal["view", "generate", "update", "review", "approve", "publish"] = "view",
) -> MethodologyRuntimeResolveResponse:
    try:
        resolution_contract = resolve_runtime(
            methodology_id,
            stage_id,
            activity_id,
            task_id,
            event,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MethodologyRuntimeResolveResponse(resolution_contract=resolution_contract)


@api_router.post("/api/methodology/runtime/sor/read", response_model=SorPreviewResponse)
async def read_from_sor(payload: SorPreviewRequest) -> SorPreviewResponse:
    resolution_contract = resolve_runtime(
        payload.methodology_id,
        payload.stage_id,
        payload.activity_id,
        payload.task_id,
        payload.lifecycle_event,
    )
    sources = _collect_sor_sources(resolution_contract)
    return SorPreviewResponse(sources=sources, preview_rows=_build_sor_preview_rows(sources))


@api_router.post("/api/methodology/runtime/sor/publish", response_model=SorPublishResponse)
async def push_to_sor(payload: SorPublishRequest) -> SorPublishResponse:
    resolution_contract = resolve_runtime(
        payload.methodology_id,
        payload.stage_id,
        payload.activity_id,
        payload.task_id,
        payload.lifecycle_event,
    )
    destinations = _collect_sor_destinations(resolution_contract)
    entry = {
        "workspace_id": payload.workspace_id,
        "lifecycle_event": payload.lifecycle_event,
        "destinations": destinations,
        "changes": payload.changes,
        "status": "captured_in_demo_outbox" if _demo_mode_enabled() else "submitted_to_sor",
        "captured_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if _demo_mode_enabled():
        demo_outbox.append("external_side_effects", entry)
    applied = {
        "workspace_id": payload.workspace_id,
        "destinations": destinations,
        "changes": payload.changes,
        "applied_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if _demo_mode_enabled():
        demo_outbox.append("applied_changes", applied)
    get_audit_log_store().record_event(
        build_event(
            tenant_id="default",
            actor_id="demo-sor",
            actor_type="service",
            roles=["automation"],
            action="demo.sor.publish.stubbed",
            resource_type="workspace",
            resource_id=payload.workspace_id,
            outcome="success",
            metadata={"destinations": destinations},
        )
    )
    return SorPublishResponse(outbox_entry=entry, applied_change=applied)


@api_router.get("/api/demo/sor")
async def get_demo_sor_state() -> dict[str, Any]:
    return {
        "outbox": demo_outbox.read("external_side_effects"),
        "applied_changes": demo_outbox.read("applied_changes"),
    }


@api_router.post(
    "/api/methodology/runtime/action",
    response_model=MethodologyNodeActionResponse,
)
async def run_methodology_runtime_action(
    payload: MethodologyNodeActionRequest,
) -> MethodologyNodeActionResponse:
    result = await run_methodology_node_action(
        payload.user_input.get("workspace_id", "default"),
        payload.methodology_id,
        payload.stage_id,
        payload.activity_id,
        payload.task_id,
        payload.lifecycle_event,
        payload.user_input,
    )
    return MethodologyNodeActionResponse.model_validate(result)


@api_router.post(
    "/api/workspace/{workspace_id}/methodology-node-actions",
    response_model=MethodologyNodeActionResponse,
)
async def run_workspace_methodology_node_action(
    workspace_id: str,
    payload: MethodologyNodeActionRequest,
) -> MethodologyNodeActionResponse:
    result = await run_methodology_node_action(
        workspace_id,
        payload.methodology_id,
        payload.stage_id,
        payload.activity_id,
        payload.task_id,
        payload.lifecycle_event,
        payload.user_input,
    )
    return MethodologyNodeActionResponse.model_validate(result)


@api_router.post("/api/intake/uploads")
async def upload_intake_document(
    request: Request,
    file: UploadFile = File(...),
    classification: str = Form("internal"),
    retention_days: int = Form(90),
) -> JSONResponse:
    _require_multimodal_intake()
    session = _require_session(request)
    content_bytes = await file.read()
    content, encoding = _decode_upload_content(content_bytes)
    document_name = file.filename or "intake-document"
    metadata = {
        "filename": document_name,
        "content_type": file.content_type,
        "encoding": encoding,
        "size_bytes": len(content_bytes),
        "source": "multimodal_intake",
    }
    payload = {
        "name": document_name,
        "content": content,
        "classification": classification,
        "retention_days": retention_days,
        "metadata": metadata,
    }
    response = await _document_client().create_document(
        payload, headers=build_forward_headers(request, session)
    )
    if response.status_code >= 400:
        _raise_upstream_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@api_router.post("/api/intake/extract", response_model=IntakeExtractionResponse)
async def extract_intake_document(
    request: Request,
    file: UploadFile = File(...),
    target: Literal["demand", "project", "both"] = Form("both"),
    document_id: str | None = Form(None),
) -> IntakeExtractionResponse:
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
            raw_demand = await _extract_intake_fields(
                prompt_path=DEMAND_PROMPT_PATH,
                document_name=document_name,
                document_content=content,
            )
            demand_payload = _normalize_demand_payload(raw_demand, document_name=document_name)
            if document_id and not demand_payload.get("source"):
                demand_payload["source"] = f"document:{document_id}"
            demand_response = await data_client.store_entity(
                "demand",
                {"tenant_id": tenant_id, "data": demand_payload},
                headers=headers,
            )
            if demand_response.status_code >= 400:
                _raise_upstream_error(demand_response)
            stored = demand_response.json()
            entities["demand"] = IntakeExtractionEntity(
                schema_name=stored.get("schema_name", "demand"),
                entity_id=stored.get("id", ""),
            )
            response.demand = demand_payload

        if target in {"project", "both"}:
            raw_project = await _extract_intake_fields(
                prompt_path=PROJECT_PROMPT_PATH,
                document_name=document_name,
                document_content=content,
            )
            project_payload = _normalize_project_payload(
                raw_project,
                tenant_id=tenant_id,
                document_name=document_name,
                owner_fallback=owner_fallback,
            )
            project_response = await data_client.store_entity(
                "project",
                {"tenant_id": tenant_id, "data": project_payload},
                headers=headers,
            )
            if project_response.status_code >= 400:
                _raise_upstream_error(project_response)
            stored_project = project_response.json()
            entities["project"] = IntakeExtractionEntity(
                schema_name=stored_project.get("schema_name", "project"),
                entity_id=stored_project.get("id", ""),
            )
            response.project = project_payload
    except (ValueError, LLMProviderError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    response.entities = entities
    return response


def _load_intake_assistant_prompt(step_id: str) -> dict[str, Any]:
    prompt_path = INTAKE_ASSISTANT_PROMPTS.get(step_id)
    if not prompt_path or not prompt_path.exists():
        return {}
    try:
        raw = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _non_empty(value: str | None) -> bool:
    return bool(value and value.strip())


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
            proposals["businessJustification"] = (
                "This initiative addresses a validated business need and aligns to current portfolio priorities."
            )
        if not _non_empty(form_state.get("expectedBenefits")):
            proposals["expectedBenefits"] = (
                "Reduce manual effort by 20% within two quarters and improve stakeholder response time by 30%."
            )
        if not _non_empty(form_state.get("businessSummary")):
            questions.append("What business problem should this intake solve in one sentence?")

    if payload.step_id == "success":
        if not _non_empty(form_state.get("successMetrics")):
            proposals["successMetrics"] = (
                "Achieve a 25% reduction in cycle time by Q4, maintain >=95% SLA adherence, and report monthly adoption above 80%."
            )
            questions.append("Which baseline metric should we compare against to prove value?")
        if not _non_empty(form_state.get("riskNotes")):
            proposals["riskNotes"] = (
                "Dependency on data quality improvements and availability of SME reviewers during pilot phase."
            )

    if payload.step_id == "attachments":
        if not _non_empty(form_state.get("attachmentSummary")):
            questions.append("Which supporting documents should reviewers inspect first?")
            proposals["attachmentSummary"] = (
                "Includes current-state process notes, stakeholder feedback summary, and budget assumptions worksheet."
            )

    for field in proposals:
        if _non_empty(form_state.get(field)):
            apply_hints.append(
                f"{field}: confirmation required because the field already contains a value."
            )
        else:
            apply_hints.append(f"{field}: safe to apply directly (field is empty).")

    for field_name, message in errors.items():
        questions.append(f"Validation issue on {field_name}: {message}")

    return IntakeAssistantResponse(
        step_id=payload.step_id,
        questions=questions,
        proposals=proposals,
        apply_hints=apply_hints,
    )


@api_router.post("/api/intake/assistant", response_model=IntakeAssistantResponse)
def intake_assistant(payload: IntakeAssistantRequest) -> IntakeAssistantResponse:
    return _build_intake_assistant_response(payload)


@api_router.get("/api/intake", response_model=list[IntakeRequest])
def list_intake_requests(status: str | None = None) -> list[IntakeRequest]:
    return intake_store.list_requests(status=status)


@api_router.post("/api/intake", response_model=IntakeRequest, status_code=201)
def create_intake_request(payload: IntakeRequestCreate) -> IntakeRequest:
    return intake_store.create_request(payload)


@api_router.get("/api/intake/{request_id}", response_model=IntakeRequest)
def get_intake_request(request_id: str) -> IntakeRequest:
    request = intake_store.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Intake request not found")
    return request


@api_router.post("/api/intake/{request_id}/decision", response_model=IntakeRequest)
@permission_required("intake.approve")
def decide_intake_request(request_id: str, payload: IntakeDecision) -> IntakeRequest:
    try:
        request = intake_store.update_decision(request_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not request:
        raise HTTPException(status_code=404, detail="Intake request not found")
    return request


@api_router.get("/api/merge-review", response_model=list[MergeReviewCase])
def list_merge_review_cases(status: str | None = None) -> list[MergeReviewCase]:
    _require_duplicate_resolution()
    return merge_review_store.list_cases(status=status)


@api_router.post("/api/merge-review/{case_id}/decision", response_model=MergeReviewCase)
def decide_merge_review_case(
    request: Request, case_id: str, payload: MergeDecision
) -> MergeReviewCase:
    _require_duplicate_resolution()
    session = _require_session(request)
    case = merge_review_store.update_decision(case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Merge review case not found")
    tenant_id = _tenant_id_from_request(request, session) or "default"
    event = build_audit_event(
        tenant_id=tenant_id,
        action="duplicate_resolution.merge_decision",
        outcome="success" if payload.decision == "approved" else "denied",
        actor_id=payload.reviewer_id,
        actor_type="user",
        actor_roles=session.get("roles") or [],
        resource_id=case.case_id,
        resource_type=f"{case.entity_type}_merge_review",
        metadata={
            "decision": payload.decision,
            "comments": payload.comments,
            "primary_record_id": case.primary_record.record_id,
            "duplicate_record_id": case.duplicate_record.record_id,
        },
        trace_id=get_trace_id() or "unknown",
        correlation_id=session.get("correlation_id"),
    )
    emit_audit_event(event)
    return case


@api_router.get("/api/pipeline/{entity_type}/{entity_id}", response_model=PipelineBoard)
def get_pipeline_board(
    entity_type: Literal["portfolio", "program"], entity_id: str
) -> PipelineBoard:
    return pipeline_store.get_board(entity_type, entity_id)


@api_router.patch(
    "/api/pipeline/{entity_type}/{entity_id}/items/{item_id}",
    response_model=PipelineItem,
)
def update_pipeline_item(
    entity_type: Literal["portfolio", "program"],
    entity_id: str,
    item_id: str,
    payload: PipelineItemUpdate,
) -> PipelineItem:
    try:
        item = pipeline_store.update_item_status(entity_type, entity_id, item_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Pipeline item not found")
    return item


@api_router.get("/api/workflows", response_model=list[WorkflowDefinitionSummary])
@permission_required("config.manage")
def list_workflow_definitions(request: Request) -> list[WorkflowDefinitionSummary]:
    _require_session(request)
    return workflow_definition_store.list_summaries()


@api_router.get("/api/workflows/{workflow_id}", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
def get_workflow_definition(workflow_id: str, request: Request) -> WorkflowDefinitionRecord:
    _require_session(request)
    record = workflow_definition_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return record


@api_router.post("/api/workflows", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
async def create_workflow_definition(
    request: Request, payload: WorkflowDefinitionPayload
) -> WorkflowDefinitionRecord:
    _validate_workflow_payload(payload)
    record = workflow_definition_store.upsert(payload)
    await _sync_workflow_definition(request, payload.workflow_id, payload.definition)
    return record


@api_router.put("/api/workflows/{workflow_id}", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
async def update_workflow_definition(
    workflow_id: str, request: Request, payload: WorkflowDefinitionPayload
) -> WorkflowDefinitionRecord:
    if payload.workflow_id != workflow_id:
        raise HTTPException(status_code=422, detail="workflow_id mismatch")
    _validate_workflow_payload(payload)
    record = workflow_definition_store.upsert(payload)
    await _sync_workflow_definition(request, workflow_id, payload.definition)
    return record


@api_router.delete("/api/workflows/{workflow_id}")
@permission_required("config.manage")
async def delete_workflow_definition(workflow_id: str, request: Request) -> dict[str, str]:
    _require_session(request)
    record = workflow_definition_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    workflow_definition_store.delete(workflow_id)
    await _delete_workflow_definition(request, workflow_id)
    return {"status": "deleted"}


@api_router.post("/api/workflows/start", response_model=WorkflowStartResponse)
async def api_start_workflow(request: Request, payload: WorkflowStartRequest) -> dict[str, Any]:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{workflow_url}/v1/workflows/start",
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


@api_router.get("/api/workspace/{project_id}", response_model=WorkspaceStateResponse)
@permission_required("portfolio.view")
async def get_workspace_state(
    project_id: str,
    request: Request,
    methodology: str | None = Query(default=None),
) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.get_or_create(tenant_id, project_id)

    if methodology is not None:
        selected_methodology = methodology.strip()
        available = set(available_methodologies())
        if selected_methodology not in available:
            raise HTTPException(status_code=422, detail="Invalid methodology")
        state = workspace_state_store.update_selection(
            tenant_id,
            project_id,
            {
                "methodology": selected_methodology,
                "current_stage_id": None,
                "current_activity_id": None,
            },
        )

    return _build_workspace_response(state)


@api_router.post("/api/workspace/{project_id}/select", response_model=WorkspaceStateResponse)
@permission_required("portfolio.view")
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


@api_router.post(
    "/api/workspace/{project_id}/activity-completion", response_model=WorkspaceStateResponse
)
@permission_required("portfolio.view")
async def update_activity_completion(
    project_id: str, payload: ActivityCompletionUpdate, request: Request
) -> WorkspaceStateResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    state = workspace_state_store.update_activity_completion(
        tenant_id, project_id, payload.activity_id, payload.completed
    )
    return _build_workspace_response(state)


@api_router.post(
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
        combined_advisories = [*upstream_advisories]
        if advisories:
            combined_advisories.append(
                "Unresolved placeholders left unchanged: " + ", ".join(sorted(advisories))
            )
        return TemplateInstantiateResponse(
            created_type=TemplateType.document,
            document_id=body.get("document_id"),
            name=body.get("name"),
            advisories=combined_advisories or None,
        )
    if template.type == TemplateType.spreadsheet:
        advisories: set[str] = set()
        payload_model = template.payload
        sheet_name, unresolved = render_template_value_with_unresolved(
            payload_model.sheet_name_template, context
        )
        advisories.update(unresolved)
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
                rendered, unresolved = render_template_value_with_unresolved(row.values, context)
                advisories.update(unresolved)
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
        response_advisories = None
        if advisories:
            response_advisories = [
                "Unresolved placeholders left unchanged: " + ", ".join(sorted(advisories))
            ]
        return TemplateInstantiateResponse(
            created_type=TemplateType.spreadsheet,
            sheet_id=sheet.sheet_id,
            sheet_name=sheet.name,
            advisories=response_advisories,
        )
    raise HTTPException(status_code=400, detail="Unsupported template type")


@api_router.get("/api/agent-gallery/agents")
async def list_agent_registry(request: Request) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    logger.info(
        "agent_gallery.registry.list",
        extra={"tenant_id": tenant_id, "project_id": None, "agent_id": None},
    )
    return JSONResponse(status_code=200, content=[entry.model_dump() for entry in registry])


@api_router.get("/api/agent-gallery/agents/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_profile(agent_id: str, request: Request) -> AgentProfileResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    entry = next((candidate for candidate in registry if candidate.agent_id == agent_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Agent not found")

    mappings = load_template_mappings().templates
    runtime_registry = load_methodology_node_runtime_registry()

    template_rows: dict[str, AgentProfileTemplateMapping] = {}
    connector_rows: dict[tuple[str, str], dict[str, Any]] = {}
    methodology_nodes: set[tuple[str, str, str | None, str | None, str]] = set()
    run_modes: set[str] = set()

    for mapping in mappings:
        binding = mapping.agent_bindings
        lifecycle_events = [
            event
            for event in ("generate", "update", "review", "approve", "publish")
            if agent_id in getattr(binding, event)
        ]
        if not lifecycle_events and agent_id not in binding.orchestration.produces_artifacts:
            continue

        template_rows[mapping.template_id] = AgentProfileTemplateMapping(
            template_id=mapping.template_id,
            template_name=mapping.name,
            lifecycle_events=lifecycle_events,
            run_modes=["dag", "demo-safe"],
            methodology_nodes=[
                {
                    "methodology_id": node.methodology_id,
                    "stage_id": node.stage_id,
                    "activity_id": node.activity_id,
                    "task_id": node.task_id,
                }
                for node in mapping.methodology_bindings
            ],
        )

        for endpoint in [
            *mapping.connector_binding.sources,
            *mapping.connector_binding.destinations,
        ]:
            key = (endpoint.connector_type, endpoint.system)
            connector_rows[key] = {
                "connector_type": endpoint.connector_type,
                "system": endpoint.system,
                "objects": endpoint.objects,
                "category": mapping.connector_binding.category,
            }

    for runtime_mapping in runtime_registry.mappings:
        workflow = runtime_mapping.resolution.agent_workflow
        if agent_id not in workflow.agent_ids:
            continue
        methodology_nodes.add(
            (
                runtime_mapping.key.methodology_id,
                runtime_mapping.key.stage_id,
                runtime_mapping.key.activity_id,
                runtime_mapping.key.task_id,
                runtime_mapping.key.lifecycle_event,
            )
        )
        run_modes.add(workflow.mode)

    run_modes.add("demo-safe")
    logger.info(
        "agent_gallery.profile.get",
        extra={"tenant_id": tenant_id, "project_id": None, "agent_id": agent_id},
    )
    return AgentProfileResponse(
        agent_id=entry.agent_id,
        name=entry.name,
        purpose=entry.description,
        capabilities=[f"{entry.name} capability"],
        inputs=["workspace_context", "template_context", "user_input"],
        outputs=entry.outputs,
        templates_touched=list(template_rows.values()),
        connectors_used=sorted(
            connector_rows.values(), key=lambda item: f"{item['connector_type']}::{item['system']}"
        ),
        methodology_nodes_supported=[
            {
                "methodology_id": methodology_id,
                "stage_id": stage_id,
                "activity_id": activity_id,
                "task_id": task_id,
                "lifecycle_event": lifecycle_event,
            }
            for methodology_id, stage_id, activity_id, task_id, lifecycle_event in sorted(
                methodology_nodes
            )
        ],
        run_modes=sorted(run_modes),
    )


@api_router.post(
    "/api/agent-gallery/agents/{agent_id}/run-preview", response_model=AgentPreviewRunResponse
)
async def run_agent_preview(
    agent_id: str, payload: AgentPreviewRunRequest, request: Request
) -> AgentPreviewRunResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    registry = load_agent_registry()
    if not any(entry.agent_id == agent_id for entry in registry):
        raise HTTPException(status_code=404, detail="Agent not found")

    runtime_registry = load_methodology_node_runtime_registry()
    matching_runtime = next(
        (
            mapping
            for mapping in runtime_registry.mappings
            if agent_id in mapping.resolution.agent_workflow.agent_ids
            and mapping.key.lifecycle_event
            in {"generate", "update", "review", "approve", "publish"}
        ),
        None,
    )
    if not matching_runtime:
        raise HTTPException(status_code=422, detail="No runtime mapping found for agent")

    methodology_id = payload.methodology_id or matching_runtime.key.methodology_id
    stage_id = payload.stage_id or matching_runtime.key.stage_id
    activity_id = (
        payload.activity_id if payload.activity_id is not None else matching_runtime.key.activity_id
    )
    task_id = payload.task_id if payload.task_id is not None else matching_runtime.key.task_id

    user_input = dict(payload.user_input)
    user_input["demo_safe"] = True
    user_input["preview_only"] = True
    user_input.setdefault("human_review_approved", True)

    result = await run_methodology_node_action(
        workspace_id=f"demo-preview-{agent_id}",
        methodology_id=methodology_id,
        stage_id=stage_id,
        activity_id=activity_id,
        task_id=task_id,
        lifecycle_event=payload.lifecycle_event,
        user_input=user_input,
    )

    logger.info(
        "agent_gallery.preview.run",
        extra={"tenant_id": tenant_id, "project_id": None, "agent_id": agent_id},
    )
    return AgentPreviewRunResponse(
        agent_id=agent_id,
        demo_safe=True,
        run_trace=result.get("workflow_trace", {}),
        artifacts=[*result.get("artifacts_created", []), *result.get("artifacts_updated", [])],
        connector_operations=result.get("connector_operations", []),
        status=result.get("status", "completed"),
    )


@api_router.get("/api/agent-gallery/{project_id}")
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


@api_router.patch("/api/agent-gallery/{project_id}/agents/{agent_id}")
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


@api_router.post("/api/agent-gallery/{project_id}/reset-defaults")
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


@api_router.get("/api/llm/models")
async def list_llm_models(request: Request) -> JSONResponse:
    _require_session(request)
    models = get_enabled_models(demo_mode=_demo_mode_enabled())
    return JSONResponse(
        status_code=200,
        content={
            "models": [
                {
                    "provider": item.provider,
                    "model_id": item.model_id,
                    "display_name": item.display_name,
                    "capabilities": list(item.capabilities),
                    "allow_in_demo": item.allow_in_demo,
                }
                for item in models
            ]
        },
    )


@api_router.get("/api/llm/preferences")
async def get_llm_preferences(request: Request, project_id: str | None = None) -> JSONResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    provider, model_id = _resolve_llm_selection(tenant_id, project_id, session.get("subject"))
    return JSONResponse(status_code=200, content={"provider": provider, "model_id": model_id})


@api_router.post("/api/llm/preferences", response_model=LLMPreferenceResponse)
async def set_llm_preferences(
    payload: LLMPreferenceRequest, request: Request
) -> LLMPreferenceResponse:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not available")
    if payload.scope in {"tenant", "project"} and not _can_manage_llm(request, session):
        raise HTTPException(status_code=403, detail="RBAC denied")
    user_id = session.get("subject") if payload.scope == "user" else None
    preference = llm_preferences_store.set_preference(
        scope=payload.scope,
        tenant_id=tenant_id,
        project_id=payload.project_id,
        user_id=user_id,
        provider=payload.provider,
        model_id=payload.model_id,
    )
    return LLMPreferenceResponse(**preference)


@api_router.post("/api/assistant/send")
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
    prompt_payload = None
    if payload.prompt_id or payload.prompt_description or payload.prompt_tags:
        prompt_payload = {
            "id": payload.prompt_id,
            "description": payload.prompt_description,
            "tags": payload.prompt_tags,
        }
    try:
        response = await _orchestrator_client().send_query(
            query=prompt_result.sanitized_text,
            context=context,
            headers=headers,
            prompt=prompt_payload,
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


@api_router.post("/api/assistant", response_model=AssistantQueryResponse)
async def assistant_query(
    payload: AssistantQueryRequest, request: Request
) -> AssistantQueryResponse:
    _require_session(request)
    query_text = payload.query.strip()
    if _demo_mode_enabled():
        demo_payload = _load_demo_assistant_payload("assistant-responses.json")
        if demo_payload:
            lowered = query_text.lower()
            for entry in demo_payload.get("responses", []):
                matches = entry.get("match") or []
                if any(match.lower() in lowered for match in matches):
                    return AssistantQueryResponse(
                        query=query_text,
                        summary=str(entry.get("summary", "")),
                        items=list(entry.get("items") or []),
                    )
            default_payload = demo_payload.get("default", {})
            return AssistantQueryResponse(
                query=query_text,
                summary=str(default_payload.get("summary", "")),
                items=list(default_payload.get("items") or []),
            )
    if payload.project_id:
        session = _require_session(request)
        tenant_id = _tenant_id_from_request(request, session)
        if tenant_id:
            provider, model_id = (
                (payload.provider, payload.model_id)
                if payload.provider and payload.model_id
                else _resolve_llm_selection(tenant_id, payload.project_id, session.get("subject"))
            )
            llm = LLMGateway(config={"demo_mode": _demo_mode_enabled()})
            try:
                system_prompt = "You are a PMO portfolio assistant. Return concise JSON with keys summary and items (array of strings)."
                user_prompt = json.dumps({"query": query_text, "project_id": payload.project_id})
                response = await llm.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    provider=provider,
                    model_id=model_id,
                    json_mode=True,
                )
                data = json.loads(response.content)
                if isinstance(data, dict):
                    return AssistantQueryResponse(
                        query=query_text,
                        summary=str(data.get("summary", "")),
                        items=[
                            str(item)
                            for item in data.get("items", [])
                            if isinstance(item, (str, int, float))
                        ],
                    )
            except Exception:  # noqa: BLE001
                logger.exception("LLM assistant query failed for query: %s", query_text[:100])

    lowered = query_text.lower()
    if "risk" in lowered:
        approvals = _approval_payload().get("items", [])
        items = [
            f"{item.get('project', 'Unknown')} — {item.get('risk', 'Risk')} ({item.get('title', '')})"
            for item in approvals
            if item.get("project")
        ]
        summary = "Projects with elevated risk exposure:"
        return AssistantQueryResponse(query=query_text, summary=summary, items=items)
    if "workflow" in lowered or "automation" in lowered:
        workflows = workflow_definition_store.list_summaries()
        items = [
            f"{workflow.name} — {workflow.description or 'Workflow definition'}"
            for workflow in workflows
        ]
        summary = "Workflow health summary:"
        return AssistantQueryResponse(query=query_text, summary=summary, items=items)
    if "approval" in lowered:
        approvals = _approval_payload().get("items", [])
        items = [item.get("title", "Approval review") for item in approvals]
        summary = "Pending approvals to review:"
        return AssistantQueryResponse(query=query_text, summary=summary, items=items)
    projects = _load_projects()
    summary = f"Tracking {len(projects)} active projects. Ask about risks, approvals, or workflows for details."
    return AssistantQueryResponse(query=query_text, summary=summary, items=[])


@api_router.get(
    "/api/assistant/demo-conversations/{scenario}", response_model=DemoConversationResponse
)
async def assistant_demo_conversation(scenario: str, request: Request) -> DemoConversationResponse:
    _require_session(request)

    safe_scenario = (scenario or "").strip().lower()
    if safe_scenario not in {"project_intake", "resource_request", "vendor_procurement"}:
        raise HTTPException(status_code=404, detail="Scenario not found")

    messages = _load_demo_conversation_payload(f"{safe_scenario}.json")
    if messages is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return DemoConversationResponse(
        scenario=safe_scenario,
        messages=[DemoConversationMessage(**entry) for entry in messages],
    )


@api_router.post("/api/assistant/suggestions", response_model=AssistantSuggestionResponse)
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
        suggestions = await _llm_suggestions(
            payload, context, methodology_map, tenant_id=tenant_id, user_id=session.get("subject")
        )
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


@api_router.get("/api/tree/{project_id}", response_model=TreeListResponse)
async def list_tree_nodes(project_id: str, request: Request) -> TreeListResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info(
        "tree.list",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TreeListResponse(tenant_id=tenant_id, project_id=project_id, nodes=nodes)


@api_router.post("/api/tree/{project_id}/nodes", response_model=TreeNode)
async def create_tree_node(project_id: str, payload: TreeNodeCreate, request: Request) -> TreeNode:
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


@api_router.patch("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeNode)
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


@api_router.post("/api/tree/{project_id}/nodes/{node_id}/move", response_model=TreeNode)
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


@api_router.delete("/api/tree/{project_id}/nodes/{node_id}", response_model=TreeDeleteResult)
async def delete_tree_node(project_id: str, node_id: str, request: Request) -> TreeDeleteResult:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted_count = tree_store.delete_node(tenant_id, project_id, node_id)
    logger.info(
        "tree.delete",
        extra={"tenant_id": tenant_id, "project_id": project_id, "node_id": node_id},
    )
    return TreeDeleteResult(deleted=deleted_count > 0, deleted_count=deleted_count)


@api_router.get("/api/tree/{project_id}/export", response_model=TreeExportResponse)
async def export_tree(project_id: str, request: Request) -> TreeExportResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    nodes = tree_store.list_nodes(tenant_id, project_id)
    logger.info(
        "tree.export",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return TreeExportResponse(
        tenant_id=tenant_id,
        project_id=project_id,
        exported_at=datetime.now(timezone.utc),
        nodes=nodes,
    )


@api_router.get("/api/timeline/{project_id}", response_model=TimelineResponse)
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


@api_router.post("/api/timeline/{project_id}/milestones", response_model=Milestone)
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


@api_router.patch("/api/timeline/{project_id}/milestones/{milestone_id}", response_model=Milestone)
async def update_timeline_milestone(
    project_id: str,
    milestone_id: str,
    payload: MilestoneUpdate,
    request: Request,
) -> Milestone:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestone = timeline_store.update_milestone(tenant_id, project_id, milestone_id, payload)
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


@api_router.delete("/api/timeline/{project_id}/milestones/{milestone_id}")
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


@api_router.get("/api/timeline/{project_id}/export", response_model=TimelineExportResponse)
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


@api_router.get("/api/wbs/{project_id}", response_model=WbsResponse)
async def get_wbs(project_id: str, request: Request) -> WbsResponse:
    _require_session(request)
    items = _get_demo_wbs(project_id)
    return WbsResponse(
        project_id=project_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )


@api_router.patch("/api/wbs/{project_id}", response_model=WbsItem)
async def update_wbs_item(
    project_id: str,
    payload: WbsUpdateRequest,
    request: Request,
) -> WbsItem:
    _require_session(request)
    if not _demo_mode_enabled():
        raise HTTPException(status_code=403, detail="WBS updates are available in demo mode.")
    items = _get_demo_wbs(project_id)
    updated_item = None
    for item in items:
        if item.id == payload.item_id:
            item.parent_id = payload.parent_id
            item.order = payload.order
            updated_item = item
            break
    if updated_item is None:
        raise HTTPException(status_code=404, detail="WBS item not found.")
    return updated_item


@api_router.get("/api/schedule/{project_id}", response_model=ScheduleResponse)
async def get_schedule(project_id: str, request: Request) -> ScheduleResponse:
    _require_session(request)
    tasks = _get_demo_schedule(project_id)
    return ScheduleResponse(
        project_id=project_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
        tasks=tasks,
    )


@api_router.get("/api/dependency-map/{program_id}", response_model=DependencyMapResponse)
async def get_dependency_map(program_id: str, request: Request) -> DependencyMapResponse:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _load_demo_dashboard_payload(
            f"dependency-map-{program_id}.json"
        ) or _load_demo_dashboard_payload("dependency-map.json")
        if payload:
            return DependencyMapResponse(**payload)
    return _mock_dependency_map(program_id)


@api_router.get("/api/program-roadmap/{program_id}", response_model=ProgramRoadmapResponse)
async def get_program_roadmap(program_id: str, request: Request) -> ProgramRoadmapResponse:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _load_demo_dashboard_payload(
            f"program-roadmap-{program_id}.json"
        ) or _load_demo_dashboard_payload("program-roadmap.json")
        if payload:
            return ProgramRoadmapResponse(**payload)
    return _mock_program_roadmap(program_id)


@api_router.get("/api/spreadsheets/{project_id}/sheets", response_model=list[Sheet])
async def list_spreadsheet_sheets(project_id: str, request: Request) -> list[Sheet]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    sheets = spreadsheet_store.list_sheets(tenant_id, project_id)
    logger.info(
        "spreadsheet.sheet.list",
        extra={"tenant_id": tenant_id, "project_id": project_id},
    )
    return sheets


@api_router.post("/api/spreadsheets/{project_id}/sheets", response_model=Sheet)
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


@api_router.get("/api/spreadsheets/{project_id}/sheets/{sheet_id}", response_model=SheetDetail)
async def get_spreadsheet_sheet(project_id: str, sheet_id: str, request: Request) -> SheetDetail:
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


@api_router.post("/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows", response_model=Row)
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


@api_router.patch(
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
        row = spreadsheet_store.update_row(tenant_id, project_id, sheet_id, row_id, payload)
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


@api_router.delete(
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


@api_router.get("/api/spreadsheets/{project_id}/sheets/{sheet_id}/export.csv")
async def export_spreadsheet_csv(project_id: str, sheet_id: str, request: Request) -> Response:
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


@api_router.post(
    "/api/spreadsheets/{project_id}/sheets/{sheet_id}/import.csv",
    response_model=ImportResult,
)
async def import_spreadsheet_csv(project_id: str, sheet_id: str, request: Request) -> ImportResult:
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
        imported = spreadsheet_store.import_csv(tenant_id, project_id, sheet_id, csv_payload)
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


@api_router.get(
    "/api/templates",
    response_model=list[TemplateSummary | CanonicalTemplateSummary],
)
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


@api_router.get(
    "/api/templates/{template_id}",
    response_model=TemplateDefinition | CanonicalTemplateDefinition,
)
async def get_template(
    template_id: str,
    request: Request,
    gallery: bool | None = None,
    version: str | None = None,
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


@api_router.post("/api/templates/{template_id}/apply", response_model=TemplateApplyResponse)
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
    stage_id = None
    activity_id = None
    if methodology_map.get("stages"):
        first_stage = methodology_map["stages"][0]
        stage_id = first_stage.get("id")
        first_activity = (first_stage.get("activities") or [{}])[0]
        activity_id = first_activity.get("id")
    if stage_id and activity_id:
        related_templates = list_templates_for_methodology_node(
            methodology_id,
            stage_id,
            activity_id,
            task_id=None,
            lifecycle_event=None,
        )

    return TemplateApplyResponse(
        project=project,
        template=response_template,
        methodology=methodology_map,
        template_mapping=template_mapping,
        related_templates=related_templates,
    )


@api_router.post("/api/knowledge/documents", response_model=DocumentVersionResponse)
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
        track_edits=_autonomous_deliverables_enabled(),
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


@api_router.get("/api/knowledge/documents", response_model=list[DocumentSummaryResponse])
async def list_documents(
    project_id: str | None = None, query: str | None = None
) -> list[DocumentSummaryResponse]:
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


@api_router.get(
    "/api/knowledge/documents/{document_id}/versions", response_model=list[DocumentVersionResponse]
)
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


@api_router.post("/api/knowledge/lessons", response_model=LessonResponse)
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


@api_router.put("/api/knowledge/lessons/{lesson_id}", response_model=LessonResponse)
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


@api_router.delete("/api/knowledge/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str) -> dict[str, Any]:
    store = _get_knowledge_store()
    deleted = store.delete_lesson(lesson_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"status": "deleted", "lesson_id": lesson_id}


@api_router.get("/api/knowledge/lessons", response_model=list[LessonResponse])
async def list_lessons(
    project_id: str | None = None,
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


@api_router.post("/api/knowledge/lessons/recommendations", response_model=list[LessonResponse])
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


@api_router.get("/api/search", response_model=SearchResponse)
async def search_global(
    request: Request,
    q: str | None = Query(default=None, alias="q"),
    query: str | None = None,
    types: str | None = None,
    project_ids: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> SearchResponse:
    session = _require_session(request)
    type_list = [entry.strip() for entry in types.split(",")] if types else []
    selected_types = type_list or [
        "document",
        "project",
        "knowledge",
        "approval",
        "workflow",
    ]
    project_id_set = (
        {entry.strip() for entry in project_ids.split(",") if entry.strip()}
        if project_ids
        else None
    )
    resolved_query = (q or query or "").strip()
    if _demo_mode_enabled():
        demo_payload = _load_demo_search_payload("global-search.json")
        if demo_payload:
            results_payload = demo_payload.get("results", [])
            return SearchResponse(
                query=resolved_query,
                offset=0,
                limit=min(max(limit, 1), 100),
                total=len(results_payload),
                results=[SearchResult.model_validate(item) for item in results_payload],
            )
    search_service = _get_search_service()
    search_results, _ = search_service.search(
        query=resolved_query,
        types=[entry for entry in selected_types if entry in {"document", "knowledge", "lesson"}],
        project_ids=project_id_set,
        tenant_id=session.get("tenant_id"),
        offset=0,
        limit=200,
    )
    results: list[SearchResult] = [
        SearchResult(
            id=item.id,
            type=item.result_type,
            title=item.title,
            summary=item.summary,
            project_id=item.project_id,
            updated_at=item.updated_at.isoformat() if item.updated_at else None,
            highlights=item.highlights,
            payload=item.payload,
        )
        for item in search_results
    ]

    if "project" in selected_types:
        for project in _load_projects():
            if project_id_set and project.id not in project_id_set:
                continue
            text = f"{project.name} {project.template_id} {project.methodology.get('name', '')}"
            score = _match_score(resolved_query, text)
            if score < 0.6:
                continue
            summary = f"Template {project.template_id}"
            methodology_name = project.methodology.get("name")
            if methodology_name:
                summary = f"{summary} · Methodology {methodology_name}"
            results.append(
                SearchResult(
                    id=project.id,
                    type="project",
                    title=project.name,
                    summary=summary,
                    project_id=project.id,
                    updated_at=project.created_at,
                    highlights={
                        key: value
                        for key, value in {
                            "title": _highlight_query(resolved_query, project.name),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if value
                    }
                    or None,
                    payload={
                        "projectId": project.id,
                        "name": project.name,
                        "templateId": project.template_id,
                        "methodology": project.methodology,
                        "createdAt": project.created_at,
                    },
                )
            )

    if "approval" in selected_types:
        approvals_payload = (
            _load_demo_dashboard_payload("approvals.json")
            if _demo_mode_enabled()
            else _approval_payload()
        )
        approvals = approvals_payload.get("approvals") or approvals_payload.get("items") or []
        for index, approval in enumerate(approvals):
            title = approval.get("title") or approval.get("name") or "Approval"
            meta = approval.get("meta") or []
            summary = " · ".join(meta) if isinstance(meta, list) else str(meta)
            if not summary:
                summary = " · ".join(
                    value
                    for value in [
                        approval.get("project"),
                        approval.get("risk"),
                        approval.get("due_in"),
                    ]
                    if value
                )
            combined = f"{title} {summary}"
            score = _match_score(resolved_query, combined)
            if score < 0.6:
                continue
            results.append(
                SearchResult(
                    id=str(approval.get("id") or f"approval-{index}"),
                    type="approval",
                    title=title,
                    summary=summary,
                    project_id=approval.get("project"),
                    highlights={
                        key: value
                        for key, value in {
                            "title": _highlight_query(resolved_query, title),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if value
                    }
                    or None,
                    payload=approval,
                )
            )

    if "workflow" in selected_types:
        if _demo_mode_enabled():
            workflow_payload = _load_demo_dashboard_payload("workflow-monitoring.json") or {}
            workflows = workflow_payload.get("runs", [])
        else:
            workflows = [
                workflow.model_dump() for workflow in workflow_definition_store.list_summaries()
            ]
        for index, workflow in enumerate(workflows):
            title = workflow.get("name") or workflow.get("title") or "Workflow"
            summary = workflow.get("description")
            if not summary:
                summary = " · ".join(
                    value
                    for value in [
                        workflow.get("status"),
                        workflow.get("run_id") or workflow.get("id"),
                        workflow.get("owner") or workflow.get("agent"),
                    ]
                    if value
                )
            combined = f"{title} {summary}"
            score = _match_score(resolved_query, combined)
            if score < 0.6:
                continue
            results.append(
                SearchResult(
                    id=str(
                        workflow.get("workflow_id")
                        or workflow.get("run_id")
                        or workflow.get("id")
                        or f"workflow-{index}"
                    ),
                    type="workflow",
                    title=title,
                    summary=summary,
                    updated_at=workflow.get("updated_at"),
                    highlights={
                        key: value
                        for key, value in {
                            "title": _highlight_query(resolved_query, title),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if value
                    }
                    or None,
                    payload=workflow,
                )
            )
    total = len(results)
    results.sort(key=lambda item: (item.updated_at or ""), reverse=True)
    trimmed_results = results[max(offset, 0) : max(offset, 0) + min(max(limit, 1), 100)]
    return SearchResponse(
        query=resolved_query,
        offset=max(offset, 0),
        limit=min(max(limit, 1), 100),
        total=total,
        results=trimmed_results,
    )


@api_router.get("/api/portfolio-health")
@permission_required("analytics.view")
async def get_portfolio_health(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _load_demo_dashboard_payload("portfolio-health.json")
        if payload:
            return JSONResponse(content=payload)
    return JSONResponse(content=_mock_portfolio_health(portfolio_id, project_id))


@api_router.get("/api/lifecycle-metrics")
@permission_required("analytics.view")
async def get_lifecycle_metrics(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _load_demo_dashboard_payload("lifecycle-metrics.json")
        if payload:
            return JSONResponse(content=payload)
    return JSONResponse(content=_mock_lifecycle_metrics(portfolio_id, project_id))


@api_router.get("/api/dashboard/{project_id}/health")
@permission_required("analytics.view")
async def get_dashboard_health(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-health.json",
                {"project_id": project_id, "status": "green", "composite_score": 0.91},
            )
        )
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


@api_router.get("/api/dashboard/{project_id}/trends")
@permission_required("analytics.view")
async def get_dashboard_trends(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-trends.json",
                {"project_id": project_id, "points": []},
            )
        )
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


@api_router.get("/api/dashboard/{project_id}/quality")
@permission_required("analytics.view")
async def get_dashboard_quality(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-quality.json",
                {"total_rules": 0, "pass_rate": 1.0, "violations": []},
            )
        )
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


@api_router.post("/api/dashboard/{project_id}/what-if")
@permission_required("analytics.view")
async def create_dashboard_what_if(
    project_id: str, payload: DashboardWhatIfRequest, request: Request
) -> Response:
    if _demo_mode_enabled():
        scenario_hash = hashlib.sha1(
            f"{project_id}:{payload.scenario}:{json.dumps(payload.adjustments, sort_keys=True)}".encode()
        ).hexdigest()[:10]
        baseline_payload = _dashboard_demo_payload_or_default(
            "project-dashboard-kpis.json",
            {
                "project_id": project_id,
                "metrics": [],
                "computed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        adjusted_metrics: list[dict[str, Any]] = []
        for metric in baseline_payload.get("metrics", []):
            name = str(metric.get("name", ""))
            normalized = float(metric.get("normalized", 0.0))
            boost = (
                float(payload.adjustments.get(name, 0.0))
                if isinstance(payload.adjustments, dict)
                else 0.0
            )
            adjusted_metrics.append(
                {**metric, "normalized": max(0.0, min(1.0, round(normalized + boost, 3)))}
            )
        return JSONResponse(
            content={
                "project_id": project_id,
                "scenario_id": f"demo-{scenario_hash}",
                "status": "completed",
                "baseline": baseline_payload,
                "adjusted": {
                    **baseline_payload,
                    "metrics": adjusted_metrics or baseline_payload.get("metrics", []),
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
                "narrative": _dashboard_demo_payload_or_default(
                    "project-dashboard-narrative.json",
                    {
                        "project_id": project_id,
                        "summary": "Demo what-if narrative.",
                        "highlights": [],
                        "risks": [],
                        "opportunities": [],
                        "data_quality_notes": [],
                        "computed_at": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            }
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.request_what_if(project_id, payload.model_dump(), headers=headers)
    logger.info(
        "dashboard.whatif.request",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@api_router.get("/api/dashboard/{project_id}/kpis")
@permission_required("analytics.view")
async def get_dashboard_kpis(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-kpis.json",
                {
                    "project_id": project_id,
                    "metrics": [],
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
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


@api_router.get("/api/dashboard/{project_id}/narrative")
@permission_required("analytics.view")
async def get_dashboard_narrative(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-narrative.json",
                {
                    "project_id": project_id,
                    "summary": "Demo narrative.",
                    "highlights": [],
                    "risks": [],
                    "opportunities": [],
                    "data_quality_notes": [],
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
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


@api_router.get("/api/dashboard/{project_id}/risks")
@permission_required("analytics.view")
async def get_dashboard_risks(project_id: str, request: Request) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-risks.json",
                {"project_id": project_id, "items": []},
            )
        )
    return JSONResponse(
        content={
            "project_id": project_id,
            "items": [
                {"id": "risk-1", "title": "Scope volatility", "severity": "High", "owner": "PMO"},
                {
                    "id": "risk-2",
                    "title": "Vendor lead-time",
                    "severity": "Medium",
                    "owner": "Procurement",
                },
            ],
        }
    )


@api_router.get("/api/dashboard/{project_id}/issues")
@permission_required("analytics.view")
async def get_dashboard_issues(project_id: str, request: Request) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-issues.json",
                {"project_id": project_id, "items": []},
            )
        )
    return JSONResponse(
        content={
            "project_id": project_id,
            "items": [
                {
                    "id": "issue-1",
                    "title": "Approval queue delay",
                    "status": "Open",
                    "owner": "Governance",
                },
                {
                    "id": "issue-2",
                    "title": "Test environment outage",
                    "status": "Mitigating",
                    "owner": "Platform",
                },
            ],
        }
    )


@api_router.get("/api/dashboard/{project_id}/aggregations")
@permission_required("analytics.view")
async def get_dashboard_aggregations(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-aggregations.json",
                {
                    "project_id": project_id,
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                    "artifacts": [],
                    "warnings": [],
                },
            )
        )
    if not _unified_dashboards_enabled():
        raise HTTPException(status_code=404, detail="Unified dashboards are not enabled")
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_project_aggregations(project_id, headers=headers)
    logger.info(
        "dashboard.aggregations.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@api_router.post("/api/dashboard/{project_id}/export-pack", response_model=DashboardExportResponse)
@permission_required("analytics.view")
async def export_dashboard_pack(project_id: str, request: Request) -> DashboardExportResponse:
    _require_session(request)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "project_id": project_id,
        "generated_at": generated_at,
        "health": _dashboard_demo_payload_or_default("project-dashboard-health.json", {}),
        "trends": _dashboard_demo_payload_or_default("project-dashboard-trends.json", {}),
        "quality": _dashboard_demo_payload_or_default("project-dashboard-quality.json", {}),
        "kpis": _dashboard_demo_payload_or_default("project-dashboard-kpis.json", {}),
        "narrative": _dashboard_demo_payload_or_default("project-dashboard-narrative.json", {}),
    }
    file_name = f"dashboard-pack-{_slugify_filename(project_id)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    output_path = DEMO_DOWNLOADS_DIR / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return DashboardExportResponse(
        project_id=project_id,
        file_name=file_name,
        download_path=f"/storage/downloads/{file_name}",
        generated_at=generated_at,
    )


@api_router.get("/api/analytics/powerbi/{report_type}")
@permission_required("analytics.view")
async def get_powerbi_embed(report_type: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _analytics_client()
    response = await client.get_powerbi_report(report_type, headers=headers)
    logger.info(
        "dashboard.powerbi.embed.fetch",
        extra={"tenant_id": session.get("tenant_id"), "report_type": report_type},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@api_router.get("/api/connector-gallery/types")
async def list_connector_types(request: Request) -> list[dict[str, Any]]:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    types = _load_connector_registry()
    logger.info("connector_gallery.types.list", extra={"tenant_id": tenant_id})
    return types


@api_router.get("/api/connector-gallery/instances")
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


@api_router.post("/api/connector-gallery/instances")
async def create_connector_instance(payload: ConnectorInstanceCreate, request: Request) -> Response:
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


@api_router.patch("/api/connector-gallery/instances/{connector_id}")
async def update_connector_instance(
    connector_id: str, payload: ConnectorInstanceUpdate, request: Request
) -> Response:
    session = _require_session(request)
    tenant_id = _tenant_id_from_request(request, session)
    headers = build_forward_headers(request, session)
    update_payload = payload.model_dump(exclude_none=True)
    client = _connector_hub_client()
    try:
        response = await client.update_connector(connector_id, update_payload, headers=headers)
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


@api_router.get("/api/connector-gallery/instances/{connector_id}/health")
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


@api_router.post("/api/document-canvas/documents")
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


@api_router.get("/api/document-canvas/documents")
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


@api_router.get("/api/document-canvas/documents/{document_id}")
async def get_document_canvas_document(document_id: str, request: Request) -> dict[str, Any]:
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


@api_router.get("/api/audit/evidence/export")
@permission_required("audit.view")
async def export_audit_evidence(request: Request) -> Response:
    session = _require_session(request)
    audit_url = os.getenv("AUDIT_LOG_SERVICE_URL")
    if not audit_url:
        raise HTTPException(status_code=503, detail="Audit log service unavailable")
    headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    headers["X-Tenant-ID"] = session.get("tenant_id") or "unknown"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{audit_url}/audit/evidence/export", headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    filename = f"audit-evidence-{session.get('tenant_id', 'tenant')}.zip"
    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "application/zip"),
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


@api_router.get("/api/portfolio/{portfolio_id}/demand")
@permission_required("portfolio.view")
async def list_portfolio_demand(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    items = [item for item in store.get("items", []) if item.get("portfolio_id") == portfolio_id]
    return {"items": items}


@api_router.post("/api/portfolio/{portfolio_id}/demand")
@permission_required("config.manage")
async def create_portfolio_demand(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    demand_id = payload.get("id") or f"dem-{uuid4().hex[:10]}"
    row = {"id": demand_id, "portfolio_id": portfolio_id, **payload}
    row.setdefault("status", "intake")
    store.setdefault("items", []).append(row)
    _write_json(DEMAND_STORE_PATH, store)
    _audit_record(
        request,
        "portfolio.demand.create",
        {"resource": "demand", "portfolio_id": portfolio_id, "demand_id": demand_id},
    )
    return row


@api_router.patch("/api/portfolio/{portfolio_id}/demand/{demand_id}")
@permission_required("config.manage")
async def patch_portfolio_demand(
    portfolio_id: str, demand_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(DEMAND_STORE_PATH, {"items": []})
    for row in store.get("items", []):
        if row.get("portfolio_id") == portfolio_id and row.get("id") == demand_id:
            row.update(payload)
            _write_json(DEMAND_STORE_PATH, store)
            _audit_record(
                request,
                "portfolio.demand.update",
                {"resource": "demand", "portfolio_id": portfolio_id, "demand_id": demand_id},
            )
            return row
    raise HTTPException(status_code=404, detail="Demand not found")


@api_router.post("/api/portfolio/{portfolio_id}/prioritisation/score")
@permission_required("portfolio.view")
async def score_prioritisation(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    demand = _load_store(DEMAND_STORE_PATH, {"items": []}).get("items", [])
    model = _load_store(
        PRIORITISATION_STORE_PATH,
        {"weights": {"value": 0.5, "effort": 0.2, "risk": 0.3}, "runs": []},
    )
    weights = model.get("weights", {"value": 0.5, "effort": 0.2, "risk": 0.3})
    rows = []
    for item in demand:
        if item.get("portfolio_id") != portfolio_id:
            continue
        value = float(item.get("value", 5))
        effort = float(item.get("effort", 5))
        risk = float(item.get("risk", 5))
        score = round(
            value * weights.get("value", 0.5)
            + (10 - effort) * weights.get("effort", 0.2)
            + (10 - risk) * weights.get("risk", 0.3),
            3,
        )
        rows.append({**item, "score": score})
    rows.sort(key=lambda x: x["score"], reverse=True)
    run = {
        "id": f"run-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": rows,
    }
    model.setdefault("runs", []).append(run)
    _write_json(PRIORITISATION_STORE_PATH, model)
    return run


@api_router.get("/api/portfolio/{portfolio_id}/capacity")
@permission_required("portfolio.view")
async def get_capacity(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(CAPACITY_STORE_PATH, {"entries": []})
    return {
        "entries": [e for e in store.get("entries", []) if e.get("portfolio_id") == portfolio_id]
    }


@api_router.post("/api/portfolio/{portfolio_id}/capacity")
@permission_required("config.manage")
async def upsert_capacity(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(CAPACITY_STORE_PATH, {"entries": []})
    entry = {
        "id": payload.get("id") or f"cap-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        **payload,
    }
    entries = [e for e in store.get("entries", []) if e.get("id") != entry["id"]]
    entries.append(entry)
    store["entries"] = entries
    _write_json(CAPACITY_STORE_PATH, store)
    return entry


@api_router.post("/api/portfolio/{portfolio_id}/scenarios/run")
@permission_required("portfolio.view")
async def run_scenarios(
    portfolio_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    name = payload.get("name", "scenario")
    demand = _load_store(DEMAND_STORE_PATH, {"items": []}).get("items", [])
    selected = [d for d in demand if d.get("portfolio_id") == portfolio_id][
        : payload.get("limit", 10)
    ]
    score = round(
        sum(float(d.get("value", 5)) - float(d.get("effort", 5)) * 0.3 for d in selected), 3
    )
    budget = round(sum(float(d.get("cost", 100)) for d in selected), 2)
    record = {
        "id": payload.get("id") or f"scn-{uuid4().hex[:8]}",
        "portfolio_id": portfolio_id,
        "name": name,
        "value_score": score,
        "budget": budget,
        "selected_ids": [d.get("id") for d in selected],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "published": False,
    }
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": [], "published_decisions": []})
    store.setdefault("scenarios", []).append(record)
    _write_json(SCENARIOS_STORE_PATH, store)
    return record


@api_router.get("/api/portfolio/{portfolio_id}/scenarios/compare")
@permission_required("portfolio.view")
async def compare_scenarios(portfolio_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": []})
    rows = [s for s in store.get("scenarios", []) if s.get("portfolio_id") == portfolio_id]
    rows.sort(key=lambda s: s.get("value_score", 0), reverse=True)
    return {"scenarios": rows}


@api_router.post("/api/portfolio/{portfolio_id}/scenarios/{scenario_id}/publish")
@permission_required("intake.approve")
async def publish_scenario_decision(
    portfolio_id: str, scenario_id: str, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": [], "published_decisions": []})
    target = None
    for row in store.get("scenarios", []):
        if row.get("portfolio_id") == portfolio_id and row.get("id") == scenario_id:
            row["published"] = True
            target = row
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    decision = {
        "portfolio_id": portfolio_id,
        "scenario_id": scenario_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("published_decisions", []).append(decision)
    _write_json(SCENARIOS_STORE_PATH, store)
    if _demo_mode_enabled():
        demo_outbox.push(
            "sor_publish",
            {
                "tenant_id": session.get("tenant_id") or "demo-tenant",
                "resource": "scenario_decision",
                **decision,
            },
        )
    _audit_record(
        request,
        "portfolio.scenario.publish",
        {"resource": "scenario", "portfolio_id": portfolio_id, "scenario_id": scenario_id},
    )
    return {"status": "published", "decision": decision}


@api_router.get("/api/finance/budgets")
@permission_required("portfolio.view")
async def list_finance_budgets(workspace_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "finance_budget.json", {"budgets": []})
    rows = [b for b in store.get("budgets", []) if b.get("workspace_id") == workspace_id]
    return {"budgets": rows}


@api_router.post("/api/finance/budgets")
@permission_required("config.manage")
async def create_finance_budget(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "finance_budget.json"
    store = _load_store(path, {"budgets": []})
    prior = [
        b for b in store.get("budgets", []) if b.get("workspace_id") == payload.get("workspace_id")
    ]
    version = len(prior) + 1
    row = {"id": f"bud-{uuid4().hex[:8]}", "version": version, **payload}
    if prior:
        row["diff"] = {
            k: row.get("amounts", {}).get(k, 0) - prior[-1].get("amounts", {}).get(k, 0)
            for k in set(row.get("amounts", {})) | set(prior[-1].get("amounts", {}))
        }
    else:
        row["diff"] = {}
    store.setdefault("budgets", []).append(row)
    _write_json(path, store)
    return row


@api_router.post("/api/finance/change-requests")
@permission_required("portfolio.view")
async def submit_change_request(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    path = STORAGE_DIR / "finance_change_requests.json"
    store = _load_store(path, {"change_requests": []})
    row = {
        "id": f"cr-{uuid4().hex[:8]}",
        "status": "submitted",
        "submitted_by": session.get("subject", "user"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    store.setdefault("change_requests", []).append(row)
    _write_json(path, store)
    return row


@api_router.post("/api/finance/change-requests/{request_id}/decision")
@permission_required("intake.approve")
async def decide_change_request(
    request_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "finance_change_requests.json"
    store = _load_store(path, {"change_requests": []})
    for row in store.get("change_requests", []):
        if row.get("id") == request_id:
            if payload.get("decision") not in {"approve", "reject"}:
                raise HTTPException(status_code=400, detail="decision must be approve|reject")
            row["status"] = "approved" if payload.get("decision") == "approve" else "rejected"
            row["decision_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(path, store)
            return row
    raise HTTPException(status_code=404, detail="Change request not found")


@api_router.get("/api/finance/evidence/export")
@permission_required("audit.view")
async def export_finance_evidence(workspace_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    budgets = _load_store(STORAGE_DIR / "finance_budget.json", {"budgets": []}).get("budgets", [])
    changes = _load_store(
        STORAGE_DIR / "finance_change_requests.json", {"change_requests": []}
    ).get("change_requests", [])
    artifacts = {
        "workspace_id": workspace_id,
        "budgets": [b for b in budgets if b.get("workspace_id") == workspace_id],
        "change_requests": [c for c in changes if c.get("workspace_id") == workspace_id],
        "approvals": _approval_payload().get("approvals", []),
    }
    return artifacts


@api_router.get("/api/agile/backlog")
@permission_required("portfolio.view")
async def agile_backlog(program_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "agile_backlog.json", {"items": []})
    return {"items": [i for i in store.get("items", []) if i.get("program_id") == program_id]}


@api_router.post("/api/agile/backlog")
@permission_required("config.manage")
async def agile_upsert_backlog(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "agile_backlog.json"
    store = _load_store(path, {"items": []})
    row = {"id": payload.get("id") or f"agl-{uuid4().hex[:8]}", **payload}
    store["items"] = [i for i in store.get("items", []) if i.get("id") != row["id"]]
    store["items"].append(row)
    _write_json(path, store)
    return row


@api_router.post("/api/agile/pi/create")
@permission_required("config.manage")
async def agile_create_pi(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "agile_pi.json"
    store = _load_store(path, {"pis": []})
    row = {
        "id": payload.get("id") or f"pi-{uuid4().hex[:8]}",
        "iterations": payload.get("iterations", []),
        "teams": payload.get("teams", []),
        **payload,
    }
    store.setdefault("pis", []).append(row)
    _write_json(path, store)
    return row


@api_router.get("/api/agile/predictability")
@permission_required("analytics.view")
async def agile_predictability(program_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    backlog = _load_store(STORAGE_DIR / "agile_backlog.json", {"items": []}).get("items", [])
    rows = [r for r in backlog if r.get("program_id") == program_id]
    planned = sum(float(r.get("planned_points", 0)) for r in rows) or 1
    achieved = sum(float(r.get("achieved_points", 0)) for r in rows)
    score = round(achieved / planned, 3)
    metrics = {
        "program_id": program_id,
        "planned": planned,
        "achieved": achieved,
        "predictability": score,
    }
    path = STORAGE_DIR / "agile_metrics.json"
    store = _load_store(path, {"history": []})
    store.setdefault("history", []).append(
        {**metrics, "at": datetime.now(timezone.utc).isoformat()}
    )
    _write_json(path, store)
    return metrics


@api_router.get("/api/comments")
@permission_required("portfolio.view")
async def list_comments(workspace_id: str, artifact_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(COMMENTS_STORE_PATH, {"comments": []})
    return {
        "comments": [
            c
            for c in store.get("comments", [])
            if c.get("workspace_id") == workspace_id and c.get("artifact_id") == artifact_id
        ]
    }


@api_router.post("/api/comments")
@permission_required("portfolio.view")
async def create_comment(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(COMMENTS_STORE_PATH, {"comments": []})
    comment = {
        "id": f"cmt-{uuid4().hex[:10]}",
        "author": session.get("subject", "user"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    store.setdefault("comments", []).append(comment)
    _write_json(COMMENTS_STORE_PATH, store)
    mentions = [part[1:] for part in str(payload.get("text", "")).split() if part.startswith("@")]
    if mentions:
        nstore = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
        notifications = _ensure_notifications(nstore, session.get("tenant_id") or "demo-tenant")
        for m in mentions:
            notifications.append(
                {
                    "id": f"ntf-{uuid4().hex[:10]}",
                    "user_id": m,
                    "message": f"Mentioned in comment {comment['id']}",
                    "read": False,
                    "created_at": comment["created_at"],
                }
            )
        _write_json(NOTIFICATIONS_STORE_PATH, nstore)
    return comment


@api_router.get("/api/notifications")
@permission_required("portfolio.view")
async def list_notifications(request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
    return {"notifications": store.get("notifications", [])}


@api_router.post("/api/notifications/{notification_id}/read")
@permission_required("portfolio.view")
async def mark_notification_read(notification_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
    for n in store.get("notifications", []):
        if n.get("id") == notification_id:
            n["read"] = True
            _write_json(NOTIFICATIONS_STORE_PATH, store)
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@api_router.post("/api/sync/diff")
@permission_required("portfolio.view")
async def sync_diff(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    source = payload.get("source", [])
    target = payload.get("target", [])
    by_id = {item["id"]: item for item in target if isinstance(item, dict) and item.get("id")}
    diffs = []
    conflicts = []
    for item in source:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        t = by_id.get(item["id"])
        if not t:
            diffs.append({"id": item["id"], "type": "create", "incoming": item})
        elif t != item:
            conflict = {
                "id": item["id"],
                "incoming": item,
                "current": t,
                "status": "requires_decision",
            }
            conflicts.append(conflict)
            diffs.append({"id": item["id"], "type": "update", "incoming": item, "current": t})
    store = _load_store(SYNC_STORE_PATH, {"conflicts": []})
    store["conflicts"] = conflicts
    _write_json(SYNC_STORE_PATH, store)
    return {"diffs": diffs, "conflicts": conflicts}


@api_router.get("/api/sync/conflicts")
@permission_required("portfolio.view")
async def get_sync_conflicts(request: Request) -> dict[str, Any]:
    _require_session(request)
    return _load_store(SYNC_STORE_PATH, {"conflicts": []})


@api_router.post("/api/sync/conflicts/{conflict_id}/resolve")
@permission_required("intake.approve")
async def resolve_sync_conflict(
    conflict_id: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(SYNC_STORE_PATH, {"conflicts": []})
    for c in store.get("conflicts", []):
        if c.get("id") == conflict_id:
            decision = payload.get("decision")
            if decision not in {"incoming", "current"}:
                raise HTTPException(status_code=400, detail="decision must be incoming|current")
            c["status"] = "resolved"
            c["resolution"] = decision
            _write_json(SYNC_STORE_PATH, store)
            return c
    raise HTTPException(status_code=404, detail="Conflict not found")


@api_router.post("/api/sync/publish")
@permission_required("intake.approve")
async def sync_publish(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    session = _require_session(request)
    if _demo_mode_enabled():
        demo_outbox.push(
            "sync_publish", {"tenant_id": session.get("tenant_id") or "demo-tenant", **payload}
        )
    _audit_record(
        request,
        "sync.publish",
        {"resource": "sync", "entity_type": payload.get("entity_type", "unknown")},
    )
    return {"status": "queued", "demo_mode": _demo_mode_enabled()}


@api_router.post("/api/alerts/compute")
@permission_required("analytics.view")
async def compute_alerts(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    seed = abs(hash(payload.get("workspace_id", "demo"))) % 100
    alerts = [
        {
            "id": "schedule-slip",
            "score": round((seed % 37) / 100 + 0.55, 3),
            "type": "schedule_slip_risk",
        },
        {
            "id": "budget-overrun",
            "score": round((seed % 29) / 100 + 0.5, 3),
            "type": "budget_overrun_risk",
        },
        {
            "id": "gate-readiness",
            "score": round((seed % 23) / 100 + 0.45, 3),
            "type": "gate_readiness_risk",
        },
    ]
    store = _load_store(ALERTS_STORE_PATH, {"history": []})
    store.setdefault("history", []).append(
        {
            "workspace_id": payload.get("workspace_id", "demo"),
            "alerts": alerts,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_json(ALERTS_STORE_PATH, store)
    return {"alerts": alerts}


@api_router.post("/api/packs/{pack_type}/generate")
@permission_required("analytics.view")
async def generate_pack(
    pack_type: str, payload: dict[str, Any], request: Request
) -> dict[str, Any]:
    _require_session(request)
    if pack_type not in {"steering", "evidence", "comms"}:
        raise HTTPException(status_code=400, detail="Unsupported pack type")
    store = _load_store(PACKS_STORE_PATH, {"packs": []})
    artifact = {
        "id": f"pack-{uuid4().hex[:8]}",
        "pack_type": pack_type,
        "workspace_id": payload.get("workspace_id"),
        "title": f"{pack_type.title()} Pack",
        "content": payload.get("content", "Auto-generated pack"),
        "editable": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("packs", []).append(artifact)
    _write_json(PACKS_STORE_PATH, store)
    return artifact


@api_router.post("/api/packs/{pack_id}/publish")
@permission_required("intake.approve")
async def publish_pack(pack_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    store = _load_store(PACKS_STORE_PATH, {"packs": []})
    for pack in store.get("packs", []):
        if pack.get("id") == pack_id:
            pack["published_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(PACKS_STORE_PATH, store)
            if _demo_mode_enabled():
                demo_outbox.push(
                    "sor_publish",
                    {
                        "tenant_id": session.get("tenant_id") or "demo-tenant",
                        "resource": "pack",
                        "pack_id": pack_id,
                    },
                )
            _audit_record(request, "pack.publish", {"resource": "pack", "pack_id": pack_id})
            return {"status": "published", "pack_id": pack_id}
    raise HTTPException(status_code=404, detail="Pack not found")


@api_router.get("/api/boards/config")
@permission_required("portfolio.view")
async def get_board_config(workspace_id: str, entity: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    store = _load_store(STORAGE_DIR / "board_configs.json", {"configs": []})
    for cfg in store.get("configs", []):
        if cfg.get("workspace_id") == workspace_id and cfg.get("entity") == entity:
            return cfg
    return {"workspace_id": workspace_id, "entity": entity, "view": "table", "columns": []}


@api_router.post("/api/boards/config")
@permission_required("config.manage")
async def save_board_config(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "board_configs.json"
    store = _load_store(path, {"configs": []})
    configs = [
        c
        for c in store.get("configs", [])
        if not (
            c.get("workspace_id") == payload.get("workspace_id")
            and c.get("entity") == payload.get("entity")
        )
    ]
    configs.append(payload)
    store["configs"] = configs
    _write_json(path, store)
    return payload


@api_router.get("/api/automations")
@permission_required("portfolio.view")
async def list_automations(request: Request) -> dict[str, Any]:
    _require_session(request)
    return _load_store(STORAGE_DIR / "automations.json", {"automations": [], "history": []})


@api_router.post("/api/automations")
@permission_required("config.manage")
async def create_automation(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_session(request)
    path = STORAGE_DIR / "automations.json"
    store = _load_store(path, {"automations": [], "history": []})
    row = {
        "id": payload.get("id") or f"auto-{uuid4().hex[:8]}",
        "enabled": payload.get("enabled", True),
        **payload,
    }
    store.setdefault("automations", []).append(row)
    _write_json(path, store)
    return row


@api_router.post("/api/automations/{automation_id}/run")
@permission_required("config.manage")
async def run_automation(automation_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    path = STORAGE_DIR / "automations.json"
    store = _load_store(path, {"automations": [], "history": []})
    match = next((a for a in store.get("automations", []) if a.get("id") == automation_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Automation not found")
    run = {
        "id": f"run-{uuid4().hex[:8]}",
        "automation_id": automation_id,
        "status": "completed",
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("history", []).append(run)
    _write_json(path, store)
    if match.get("action") == "notify":
        nstore = _load_store(NOTIFICATIONS_STORE_PATH, {"notifications": []})
        _ensure_notifications(nstore, session.get("tenant_id") or "demo-tenant").append(
            {
                "id": f"ntf-{uuid4().hex[:8]}",
                "user_id": "*",
                "message": f"Automation {automation_id} executed",
                "read": False,
                "created_at": run["executed_at"],
            }
        )
        _write_json(NOTIFICATIONS_STORE_PATH, nstore)
    _audit_record(
        request, "automation.run", {"resource": "automation", "automation_id": automation_id}
    )
    return run


@app.get("/api/portfolio-health")
async def legacy_portfolio_health(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    if _demo_mode_enabled():
        fixture_path = REPO_ROOT / "examples" / "demo-scenarios" / "portfolio-health.json"
        if fixture_path.exists():
            return JSONResponse(content=json.loads(fixture_path.read_text(encoding="utf-8")))
    return JSONResponse(content=_mock_portfolio_health(portfolio_id, project_id))


@app.get("/api/lifecycle-metrics")
async def legacy_lifecycle_metrics(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    if _demo_mode_enabled():
        fixture_path = REPO_ROOT / "examples" / "demo-scenarios" / "lifecycle-metrics.json"
        if fixture_path.exists():
            return JSONResponse(content=json.loads(fixture_path.read_text(encoding="utf-8")))
    return JSONResponse(content=_mock_lifecycle_metrics(portfolio_id, project_id))


@api_router.get("/")
async def index() -> FileResponse:
    if FRONTEND_DIST_DIR.exists():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
    return FileResponse(STATIC_DIR / "index.html")


@api_router.get("/app")
async def v1_app_entrypoint() -> RedirectResponse:
    return RedirectResponse(url="/app", status_code=307)


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8501, reload=False)
