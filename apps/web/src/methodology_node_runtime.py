from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_registry import load_agent_registry
from methodologies import available_methodologies, get_methodology_map
from template_mappings import CANVAS_TYPES, get_template_mapping

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RUNTIME_REGISTRY_PATH = DATA_DIR / "methodology_node_runtime.json"
CONNECTOR_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3] / "integrations" / "connectors" / "registry" / "connectors.json"
)
LIFECYCLE_EVENTS = ("view", "generate", "update", "review", "approve", "publish")


class RuntimeKey(BaseModel):
    methodology_id: str
    stage_id: str
    activity_id: str | None = None
    task_id: str | None = None
    lifecycle_event: Literal["view", "generate", "update", "review", "approve", "publish"]


class ConnectorEndpoint(BaseModel):
    category: str
    connector_type: str
    system: str
    objects: list[str] = Field(default_factory=list)


class AgentWorkflow(BaseModel):
    workflow_id: str
    mode: Literal["single", "dag", "sequential"]
    agent_ids: list[str] = Field(default_factory=list)
    dag_ref: str | None = None
    depends_on_templates: list[str] = Field(default_factory=list)
    human_review_required: bool = False


class CanvasResolution(BaseModel):
    canvas_type: str
    renderer_component: str
    default_view: Literal["edit", "preview", "review"]
    focus: dict[str, str] = Field(default_factory=dict)


class AssistantResponseContract(BaseModel):
    output_format: Literal["doc", "table", "json", "diff", "markdown"]
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    validation_checklist: list[str] = Field(default_factory=list)
    escalation_rules: list[str] = Field(default_factory=list)


class AssistantResolution(BaseModel):
    intent_id: str
    system_prompt_key: str
    response_contract: AssistantResponseContract


class RuntimeResolution(BaseModel):
    template_ids: list[str] = Field(default_factory=list)
    agent_workflow: AgentWorkflow
    connectors: dict[str, list[ConnectorEndpoint]]
    canvas: CanvasResolution
    assistant: AssistantResolution


class RuntimeMapping(BaseModel):
    key: RuntimeKey
    resolution: RuntimeResolution


class RuntimeRegistry(BaseModel):
    mappings: list[RuntimeMapping]


def _load_connector_types() -> set[str]:
    with CONNECTOR_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return {
            str(item.get("id")) for item in payload if isinstance(item, dict) and item.get("id")
        }
    return set()


def _collect_nodes(map_payload: dict[str, Any]) -> tuple[set[str], set[tuple[str, str]], set[tuple[str, str, str]]]:
    stages: set[str] = set()
    activities: set[tuple[str, str]] = set()
    tasks: set[tuple[str, str, str]] = set()

    for stage in map_payload.get("stages", []) or []:
        stage_id = str(stage.get("id"))
        if stage_id:
            stages.add(stage_id)
        for activity in stage.get("activities", []) or []:
            activity_id = str(activity.get("id"))
            if stage_id and activity_id:
                activities.add((stage_id, activity_id))

    def walk(nodes: list[dict[str, Any]], stage_id: str | None = None, activity_id: str | None = None) -> None:
        for node in nodes:
            node_type = str(node.get("type", ""))
            node_id = str(node.get("id"))
            if node_type == "phase":
                stages.add(node_id)
                walk(node.get("children", []) or [], node_id, None)
            elif node_type == "activity":
                if stage_id:
                    activities.add((stage_id, node_id))
                walk(node.get("children", []) or [], stage_id, node_id)
            else:
                if stage_id and activity_id:
                    tasks.add((stage_id, activity_id, node_id))
                walk(node.get("children", []) or [], stage_id, activity_id)

    walk(map_payload.get("navigation_nodes", []) or [])
    return stages, activities, tasks


def _validate_registry(registry: RuntimeRegistry) -> RuntimeRegistry:
    methodology_ids = set(available_methodologies())
    valid_agents = {entry.agent_id for entry in load_agent_registry()}
    connector_types = _load_connector_types()

    collected_nodes = {
        methodology_id: _collect_nodes(get_methodology_map(methodology_id))
        for methodology_id in methodology_ids
    }

    seen_keys: set[tuple[str, str, str | None, str | None, str]] = set()
    views_found: set[tuple[str, str, str | None, str | None]] = set()

    for mapping in registry.mappings:
        key = mapping.key
        key_tuple = (
            key.methodology_id,
            key.stage_id,
            key.activity_id,
            key.task_id,
            key.lifecycle_event,
        )
        if key_tuple in seen_keys:
            raise ValueError(f"Duplicate methodology node runtime mapping for {key_tuple}")
        seen_keys.add(key_tuple)

        if key.methodology_id not in methodology_ids:
            raise ValueError(f"Unknown methodology_id `{key.methodology_id}` in runtime registry")

        stages, activities, tasks = collected_nodes[key.methodology_id]
        if key.stage_id not in stages:
            raise ValueError(f"Unknown stage_id `{key.stage_id}` for methodology `{key.methodology_id}`")
        if key.activity_id is not None and (key.stage_id, key.activity_id) not in activities:
            raise ValueError(
                f"Unknown activity_id `{key.activity_id}` under stage `{key.stage_id}` ({key.methodology_id})"
            )
        if key.task_id is not None and key.activity_id is None:
            raise ValueError("task_id cannot be set when activity_id is null")

        if key.lifecycle_event == "view":
            views_found.add((key.methodology_id, key.stage_id, key.activity_id, key.task_id))

        if mapping.resolution.canvas.canvas_type not in CANVAS_TYPES:
            raise ValueError(
                f"Invalid canvas_type `{mapping.resolution.canvas.canvas_type}` for mapping {key_tuple}"
            )

        for template_id in mapping.resolution.template_ids:
            if get_template_mapping(template_id) is None:
                raise ValueError(f"Unknown template_id `{template_id}` in mapping {key_tuple}")

        for agent_id in mapping.resolution.agent_workflow.agent_ids:
            if agent_id not in valid_agents:
                raise ValueError(f"Unknown agent_id `{agent_id}` in mapping {key_tuple}")

        for endpoint in [
            *mapping.resolution.connectors.get("sources", []),
            *mapping.resolution.connectors.get("destinations", []),
        ]:
            if endpoint.connector_type not in connector_types:
                raise ValueError(
                    f"Unknown connector_type `{endpoint.connector_type}` in mapping {key_tuple}"
                )

    for methodology_id, (stages, activities, tasks) in collected_nodes.items():
        for stage_id in stages:
            node_key = (methodology_id, stage_id, None, None)
            if node_key not in views_found:
                raise ValueError(f"Missing required view mapping for stage node {node_key}")
        for stage_id, activity_id in activities:
            node_key = (methodology_id, stage_id, activity_id, None)
            if node_key not in views_found:
                raise ValueError(f"Missing required view mapping for activity node {node_key}")
        for stage_id, activity_id, task_id in tasks:
            node_key = (methodology_id, stage_id, activity_id, task_id)
            if node_key not in views_found:
                continue

    return registry


def _merge_with_template_defaults(mapping: RuntimeMapping) -> dict[str, Any]:
    merged = mapping.model_dump(mode="json")
    template_ids = mapping.resolution.template_ids
    if not template_ids:
        return merged["resolution"]

    base_mapping = get_template_mapping(template_ids[0])
    if base_mapping is None:
        return merged["resolution"]

    event = mapping.key.lifecycle_event
    defaults = {
        "template_ids": [base_mapping.template_id],
        "agent_workflow": {
            "workflow_id": mapping.resolution.agent_workflow.workflow_id,
            "mode": "single" if len(getattr(base_mapping.agent_bindings, event, [])) <= 1 else "sequential",
            "agent_ids": getattr(base_mapping.agent_bindings, event, []),
            "dag_ref": base_mapping.agent_bindings.orchestration.dag_name,
            "depends_on_templates": base_mapping.agent_bindings.orchestration.depends_on_templates,
            "human_review_required": mapping.resolution.agent_workflow.human_review_required,
        },
        "connectors": {
            "sources": [
                {
                    "category": base_mapping.connector_binding.category,
                    "connector_type": endpoint.connector_type,
                    "system": endpoint.system,
                    "objects": endpoint.objects,
                }
                for endpoint in base_mapping.connector_binding.sources
            ],
            "destinations": [
                {
                    "category": base_mapping.connector_binding.category,
                    "connector_type": endpoint.connector_type,
                    "system": endpoint.system,
                    "objects": endpoint.objects,
                }
                for endpoint in base_mapping.connector_binding.destinations
            ],
        },
        "canvas": {
            "canvas_type": base_mapping.canvas_binding.canvas_type,
            "renderer_component": base_mapping.canvas_binding.renderer_component,
            "default_view": base_mapping.canvas_binding.default_view,
            "focus": {"template_id": base_mapping.template_id},
        },
    }

    assistant_intent = next(
        (
            intent
            for intent in base_mapping.assistant_binding.intents
            if intent.lifecycle_event == event and event != "view"
        ),
        None,
    )
    if assistant_intent:
        defaults["assistant"] = {
            "intent_id": assistant_intent.intent_id,
            "system_prompt_key": assistant_intent.system_prompt_key,
            "response_contract": {
                "output_format": base_mapping.assistant_binding.response_contract.output_format,
                "must_include": base_mapping.assistant_binding.response_contract.input_requirements,
                "must_not_include": [],
                "validation_checklist": base_mapping.assistant_binding.response_contract.review_checklist,
                "escalation_rules": [],
            },
        }

    merged_resolution = defaults
    for key, value in merged["resolution"].items():
        if isinstance(value, dict) and isinstance(merged_resolution.get(key), dict):
            merged_resolution[key] = {**merged_resolution[key], **value}
        elif value not in (None, [], {}):
            merged_resolution[key] = value
    return merged_resolution


@lru_cache(maxsize=1)
def load_methodology_node_runtime_registry() -> RuntimeRegistry:
    if not RUNTIME_REGISTRY_PATH.exists():
        raise ValueError(f"Methodology runtime registry not found: {RUNTIME_REGISTRY_PATH}")
    raw = json.loads(RUNTIME_REGISTRY_PATH.read_text(encoding="utf-8"))
    registry = RuntimeRegistry.model_validate(raw)
    return _validate_registry(registry)


def resolve_runtime(
    methodology_id: str,
    stage_id: str,
    activity_id: str | None,
    task_id: str | None,
    lifecycle_event: str,
) -> dict[str, Any]:
    registry = load_methodology_node_runtime_registry()
    matches = [
        mapping
        for mapping in registry.mappings
        if mapping.key.methodology_id == methodology_id
        and mapping.key.stage_id == stage_id
        and mapping.key.lifecycle_event == lifecycle_event
        and mapping.key.activity_id in (activity_id, None)
        and mapping.key.task_id in (task_id, None)
    ]
    if not matches:
        raise ValueError(
            "No runtime mapping found for "
            f"{methodology_id}/{stage_id}/{activity_id}/{task_id} event `{lifecycle_event}`"
        )

    matches.sort(
        key=lambda item: (
            1 if item.key.activity_id is not None else 0,
            1 if item.key.task_id is not None else 0,
        ),
        reverse=True,
    )
    return _merge_with_template_defaults(matches[0])


def list_runtime_actions_for_node(
    methodology_id: str,
    stage_id: str,
    activity_id: str | None,
    task_id: str | None,
) -> list[str]:
    registry = load_methodology_node_runtime_registry()
    events = {
        mapping.key.lifecycle_event
        for mapping in registry.mappings
        if mapping.key.methodology_id == methodology_id
        and mapping.key.stage_id == stage_id
        and mapping.key.activity_id in (activity_id, None)
        and mapping.key.task_id in (task_id, None)
    }
    return [event for event in LIFECYCLE_EVENTS if event in events]
