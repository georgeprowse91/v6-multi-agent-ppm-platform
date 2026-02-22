from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from agent_registry import load_agent_registry
from methodologies import available_methodologies, get_methodology_map
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEMPLATES_PATH = DATA_DIR / "templates.json"
TEMPLATE_MAPPINGS_JSON_PATH = DATA_DIR / "template_mappings.json"
TEMPLATE_MAPPINGS_YAML_PATH = DATA_DIR / "template_mappings.yaml"
CONNECTOR_REGISTRY_PATH = REPO_ROOT / "integrations" / "connectors" / "registry" / "connectors.json"

LIFECYCLE_EVENTS = ("generate", "update", "review", "approve", "publish")
CANVAS_TYPES = (
    "document",
    "spreadsheet",
    "kanban",
    "timeline",
    "risk_log",
    "decision_log",
    "dashboard",
    "form",
    "whiteboard",
    "board",
    "backlog",
    "gantt",
    "grid",
    "financial",
    "dependency_map",
    "roadmap",
    "approval",
)
CONNECTOR_CATEGORIES = (
    "portfolio",
    "finance",
    "risk",
    "compliance",
    "delivery",
    "hr",
    "engineering",
    "external_publishing",
)
OUTPUT_FORMATS = ("doc", "table", "markdown", "json", "diff")
TONES = ("executive", "delivery", "assurance")
SIDE_EFFECTS = ("none", "write_connector", "publish_external", "notify")


class MethodologyBinding(BaseModel):
    methodology_id: Literal["predictive", "adaptive", "hybrid"]
    stage_id: str
    activity_id: str
    task_id: str | None = None
    lifecycle_events: list[Literal["generate", "update", "review", "approve", "publish"]]
    required: bool
    gate_refs: list[str] = Field(default_factory=list)


class AgentOrchestrationBinding(BaseModel):
    dag_name: str
    depends_on_templates: list[str] = Field(default_factory=list)
    produces_artifacts: list[str] = Field(default_factory=list)
    side_effects: list[Literal["none", "write_connector", "publish_external", "notify"]] = Field(
        default_factory=list
    )


class AgentBinding(BaseModel):
    generate: list[str] = Field(default_factory=list)
    update: list[str] = Field(default_factory=list)
    review: list[str] = Field(default_factory=list)
    approve: list[str] = Field(default_factory=list)
    publish: list[str] = Field(default_factory=list)
    orchestration: AgentOrchestrationBinding


class ConnectorEndpoint(BaseModel):
    connector_type: str
    system: str
    objects: list[str] = Field(default_factory=list)


class ConnectorBinding(BaseModel):
    category: Literal[
        "portfolio",
        "finance",
        "risk",
        "compliance",
        "delivery",
        "hr",
        "engineering",
        "external_publishing",
    ]
    sources: list[ConnectorEndpoint] = Field(default_factory=list)
    destinations: list[ConnectorEndpoint] = Field(default_factory=list)


class CanvasBinding(BaseModel):
    canvas_type: Literal[
        "document",
        "spreadsheet",
        "kanban",
        "timeline",
        "risk_log",
        "decision_log",
        "dashboard",
        "form",
        "whiteboard",
        "board",
        "backlog",
        "gantt",
        "grid",
        "financial",
        "dependency_map",
        "roadmap",
        "approval",
    ]
    renderer_component: str
    default_view: str


class AssistantIntentBinding(BaseModel):
    intent_id: str
    lifecycle_event: Literal["generate", "update", "review", "approve", "publish"]
    system_prompt_key: str


class AssistantResponseContract(BaseModel):
    input_requirements: list[str] = Field(default_factory=list)
    output_format: Literal["doc", "table", "markdown", "json", "diff"]
    tone: Literal["executive", "delivery", "assurance"]
    review_checklist: list[str] = Field(default_factory=list)


class AssistantBinding(BaseModel):
    intents: list[AssistantIntentBinding] = Field(default_factory=list)
    response_contract: AssistantResponseContract


class TemplateMapping(BaseModel):
    template_id: str
    name: str
    version: int
    methodology_bindings: list[MethodologyBinding]
    agent_bindings: AgentBinding
    connector_binding: ConnectorBinding
    canvas_binding: CanvasBinding
    assistant_binding: AssistantBinding


class TemplateMappingRegistry(BaseModel):
    templates: list[TemplateMapping]


def _load_templates() -> set[str]:
    with TEMPLATES_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(item.get("id")) for item in payload.get("templates", []) if item.get("id")}


def _load_connector_types() -> set[str]:
    with CONNECTOR_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return {
            str(item.get("id")) for item in payload if isinstance(item, dict) and item.get("id")
        }
    return set()


def _find_activity(map_payload: dict[str, Any], stage_id: str, activity_id: str) -> bool:
    for stage in map_payload.get("stages", []):
        if stage.get("id") != stage_id:
            continue
        return any(activity.get("id") == activity_id for activity in stage.get("activities", []))
    return False


def _load_raw_registry() -> dict[str, Any]:
    if TEMPLATE_MAPPINGS_JSON_PATH.exists():
        with TEMPLATE_MAPPINGS_JSON_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    if TEMPLATE_MAPPINGS_YAML_PATH.exists():
        with TEMPLATE_MAPPINGS_YAML_PATH.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    raise ValueError("Template mapping registry file not found")


def _validate_registry(registry: TemplateMappingRegistry) -> TemplateMappingRegistry:
    template_ids = _load_templates()
    connector_types = _load_connector_types()
    methodology_ids = set(available_methodologies())
    valid_agents = {entry.agent_id for entry in load_agent_registry()}

    for mapping in registry.templates:
        if mapping.template_id not in template_ids:
            raise ValueError(f"Unknown template_id `{mapping.template_id}` in template mappings")

        for dependency in mapping.agent_bindings.orchestration.depends_on_templates:
            if dependency not in template_ids:
                raise ValueError(
                    f"Template `{mapping.template_id}` depends on unknown template `{dependency}`"
                )

        for method_binding in mapping.methodology_bindings:
            if method_binding.methodology_id not in methodology_ids:
                raise ValueError(
                    f"Template `{mapping.template_id}` references unknown methodology `{method_binding.methodology_id}`"
                )
            methodology_map = get_methodology_map(method_binding.methodology_id)
            if not _find_activity(
                methodology_map,
                method_binding.stage_id,
                method_binding.activity_id,
            ):
                raise ValueError(
                    "Template "
                    f"`{mapping.template_id}` binding references missing stage/activity "
                    f"`{method_binding.stage_id}`/`{method_binding.activity_id}`"
                )

        for event in LIFECYCLE_EVENTS:
            for agent_id in getattr(mapping.agent_bindings, event):
                if agent_id not in valid_agents:
                    raise ValueError(
                        f"Template `{mapping.template_id}` uses unknown agent_id `{agent_id}`"
                    )

        if mapping.canvas_binding.canvas_type not in CANVAS_TYPES:
            raise ValueError(
                f"Template `{mapping.template_id}` uses invalid canvas_type `{mapping.canvas_binding.canvas_type}`"
            )

        if mapping.connector_binding.category not in CONNECTOR_CATEGORIES:
            raise ValueError(
                f"Template `{mapping.template_id}` uses invalid connector category `{mapping.connector_binding.category}`"
            )

        for endpoint in [
            *mapping.connector_binding.sources,
            *mapping.connector_binding.destinations,
        ]:
            if endpoint.connector_type not in connector_types:
                raise ValueError(
                    f"Template `{mapping.template_id}` references unknown connector type `{endpoint.connector_type}`"
                )

        for intent in mapping.assistant_binding.intents:
            if intent.lifecycle_event not in LIFECYCLE_EVENTS:
                raise ValueError(
                    f"Template `{mapping.template_id}` has invalid assistant lifecycle_event `{intent.lifecycle_event}`"
                )
        contract = mapping.assistant_binding.response_contract
        if contract.output_format not in OUTPUT_FORMATS:
            raise ValueError(f"Template `{mapping.template_id}` has invalid output format")
        if contract.tone not in TONES:
            raise ValueError(f"Template `{mapping.template_id}` has invalid tone")

        if any(
            effect not in SIDE_EFFECTS
            for effect in mapping.agent_bindings.orchestration.side_effects
        ):
            raise ValueError(f"Template `{mapping.template_id}` has invalid side effect")

    return registry


@lru_cache(maxsize=1)
def load_template_mappings() -> TemplateMappingRegistry:
    raw = _load_raw_registry()
    registry = TemplateMappingRegistry.model_validate(raw)
    return _validate_registry(registry)


def get_template_mapping(template_id: str) -> TemplateMapping | None:
    registry = load_template_mappings()
    return next((item for item in registry.templates if item.template_id == template_id), None)


def list_templates_for_methodology_node(
    methodology_id: str,
    stage_id: str,
    activity_id: str,
    task_id: str | None,
    lifecycle_event: Literal["generate", "update", "review", "approve", "publish"] | None = None,
) -> list[TemplateMapping]:
    matches: list[TemplateMapping] = []
    for mapping in load_template_mappings().templates:
        for binding in mapping.methodology_bindings:
            if binding.methodology_id != methodology_id:
                continue
            if binding.stage_id != stage_id or binding.activity_id != activity_id:
                continue
            if task_id is not None and binding.task_id not in (None, task_id):
                continue
            if lifecycle_event and lifecycle_event not in binding.lifecycle_events:
                continue
            matches.append(mapping)
            break
    return matches


def list_required_templates_for_gate(methodology_id: str, gate_ref: str) -> list[TemplateMapping]:
    matches: list[TemplateMapping] = []
    normalized = gate_ref.strip().lower()
    for mapping in load_template_mappings().templates:
        for binding in mapping.methodology_bindings:
            if binding.methodology_id != methodology_id or not binding.required:
                continue
            if any(normalized == gate.strip().lower() for gate in binding.gate_refs):
                matches.append(mapping)
                break
    return matches
