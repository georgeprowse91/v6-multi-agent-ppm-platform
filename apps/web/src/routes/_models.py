"""Pydantic models shared across route modules.

Extracted from legacy_main.py to avoid circular imports.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from routes._deps import CanvasTab, TemplateMapping

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "web-ui"
    dependencies: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Config / Session
# ---------------------------------------------------------------------------


class UIConfig(BaseModel):
    api_gateway_url: str
    workflow_service_url: str
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


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# WBS / Schedule / Dependency / Roadmap
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class WorkflowStartRequest(BaseModel):
    workflow_id: str


class WorkflowStartResponse(BaseModel):
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Methodology / Workspace
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Agent gallery
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Template / Project
# ---------------------------------------------------------------------------


class TemplateAgentConfig(BaseModel):
    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)


class TemplateConnectorConfig(BaseModel):
    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)


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
    template_id: str = ""
    template_version: str = "1.0"
    created_at: str
    methodology: dict[str, Any]
    agent_config: TemplateAgentConfig
    connector_config: TemplateConnectorConfig
    initial_tabs: list[TemplateTab] = Field(default_factory=list)
    dashboards: list[TemplateTab] = Field(default_factory=list)


class TemplateApplyRequest(BaseModel):
    project_name: str
    version: str | None = None


class TemplateApplyResponse(BaseModel):
    project: ProjectRecord
    template: TemplateDefinition
    methodology: dict[str, Any]
    template_mapping: TemplateMapping | None = None
    related_templates: list[TemplateMapping] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Documents / Knowledge
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------


class AssistantSendRequest(BaseModel):
    project_id: str
    message: str
    prompt_id: str | None = None
    prompt_description: str | None = None
    prompt_tags: list[str] = Field(default_factory=list)


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


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


class LLMPreferenceRequest(BaseModel):
    scope: Literal["tenant", "project", "user"]
    project_id: str | None = None
    provider: str
    model_id: str


class LLMPreferenceResponse(BaseModel):
    provider: str
    model_id: str


# ---------------------------------------------------------------------------
# Dashboard / Connectors / Document Canvas
# ---------------------------------------------------------------------------


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
