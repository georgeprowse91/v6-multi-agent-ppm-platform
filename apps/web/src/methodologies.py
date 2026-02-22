from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
METHODOLOGY_DOCS_ROOT = REPO_ROOT / "docs" / "methodology"
METHODOLOGY_STORAGE_PATH = (
    Path(__file__).resolve().parents[1] / "storage" / "methodology_definitions.json"
)


DEFAULT_STAGE_RELATIONSHIPS: dict[str, dict[str, dict[str, Any]]] = {
    "adaptive": {
        "default": {
            "template_id": "project_management_plan_template",
            "agent_id": "project-lifecycle-governance",
            "connector_id": "jira",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Review stage deliverables and dependencies",
                "Prepare next-step recommendations for the team",
            ],
        },
        "0.1": {
            "template_id": "project-charter",
            "agent_id": "demand-intake",
            "connector_id": "jira",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Draft the project charter from intake details",
                "Validate required triage fields before review",
            ],
        },
        "0.2": {
            "template_id": "product-strategy-canvas",
            "agent_id": "portfolio-strategy-optimisation",
            "connector_id": "power-bi",
            "canvas_ui": "dashboard",
            "assistant_suggested_actions": [
                "Score initiative value versus effort",
                "Generate a prioritisation recommendation for governance",
            ],
        },
        "0.3": {
            "template_id": "project_management_plan_template",
            "agent_id": "project-definition-scope",
            "connector_id": "confluence",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Create a mobilisation checklist",
                "Suggest initial operating cadence and governance roles",
            ],
        },
        "0.4": {
            "template_id": "overall_product_backlog_template",
            "agent_id": "project-definition-scope",
            "connector_id": "jira",
            "canvas_ui": "tree",
            "assistant_suggested_actions": [
                "Refine epics into backlog-ready slices",
                "Identify acceptance criteria gaps",
            ],
        },
        "0.5": {
            "template_id": "sprint-planning-template",
            "agent_id": "schedule-planning",
            "connector_id": "azure-devops",
            "canvas_ui": "timeline",
            "assistant_suggested_actions": [
                "Generate sprint goals and draft plan",
                "Flag dependencies that can jeopardize sprint commitments",
            ],
        },
        "0.6": {
            "template_id": "issue-log",
            "agent_id": "risk-issue-management",
            "connector_id": "servicenow",
            "canvas_ui": "dependency-map",
            "assistant_suggested_actions": [
                "Correlate blockers across work items",
                "Recommend mitigation and escalation path",
            ],
        },
    },
    "predictive": {
        "default": {
            "template_id": "project_management_plan_template",
            "agent_id": "project-lifecycle-governance",
            "connector_id": "microsoft-project",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Assess completion against the baseline plan",
                "Prepare governance actions for upcoming reviews",
            ],
        },
        "0.1": {
            "template_id": "it-project-charter",
            "agent_id": "demand-intake",
            "connector_id": "servicenow",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Draft a structured initiation brief",
                "Validate baseline intake completeness",
            ],
        },
        "0.2": {
            "template_id": "business_requirements_document_template",
            "agent_id": "project-definition-scope",
            "connector_id": "confluence",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Generate requirements traceability starter set",
                "Highlight missing stakeholder requirements",
            ],
        },
        "0.3": {
            "template_id": "project_management_plan_template",
            "agent_id": "schedule-planning",
            "connector_id": "microsoft-project",
            "canvas_ui": "timeline",
            "assistant_suggested_actions": [
                "Build draft milestone baseline",
                "Propose critical path checks",
            ],
        },
        "0.4": {
            "template_id": "risk_register_template",
            "agent_id": "risk-issue-management",
            "connector_id": "sharepoint",
            "canvas_ui": "spreadsheet",
            "assistant_suggested_actions": [
                "Generate risk heatmap inputs",
                "Recommend mitigations for high exposure items",
            ],
        },
        "0.5": {
            "template_id": "status-report-template",
            "agent_id": "stakeholder-comms",
            "connector_id": "power-bi",
            "canvas_ui": "dashboard",
            "assistant_suggested_actions": [
                "Produce stage-gate readiness summary",
                "Draft executive status narrative",
            ],
        },
    },
    "hybrid": {
        "default": {
            "template_id": "hybrid-project-management-plan-template",
            "agent_id": "workflow-process-engine",
            "connector_id": "jira",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Balance predictive controls with adaptive delivery feedback",
                "Recommend integrated actions for the next governance checkpoint",
            ],
        },
        "0.1": {
            "template_id": "it-project-charter",
            "agent_id": "demand-intake",
            "connector_id": "jira",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Capture both delivery and product outcomes",
                "Prepare intake pack for triage board",
            ],
        },
        "0.2": {
            "template_id": "hybrid-project-management-plan-template",
            "agent_id": "portfolio-strategy-optimisation",
            "connector_id": "power-bi",
            "canvas_ui": "dashboard",
            "assistant_suggested_actions": [
                "Blend strategic score with delivery complexity",
                "Recommend initiative sequencing",
            ],
        },
        "0.3": {
            "template_id": "project_management_plan_template",
            "agent_id": "project-lifecycle-governance",
            "connector_id": "confluence",
            "canvas_ui": "program-roadmap",
            "assistant_suggested_actions": [
                "Define hybrid governance cadence",
                "Draft Gate 0 entry checklist",
            ],
        },
        "0.4": {
            "template_id": "software-requirements-specification-template",
            "agent_id": "project-definition-scope",
            "connector_id": "azure-devops",
            "canvas_ui": "tree",
            "assistant_suggested_actions": [
                "Link requirements to releases and milestones",
                "Identify baseline assumptions requiring sign-off",
            ],
        },
        "0.5": {
            "template_id": "safe_program_increment_planning_template",
            "agent_id": "workflow-process-engine",
            "connector_id": "jira",
            "canvas_ui": "timeline",
            "assistant_suggested_actions": [
                "Draft rolling-wave plan for next release increment",
                "Highlight cross-team integration risks",
            ],
        },
        "0.6": {
            "template_id": "sprint-review-template",
            "agent_id": "quality-management",
            "connector_id": "github",
            "canvas_ui": "document",
            "assistant_suggested_actions": [
                "Summarize increment outcomes",
                "Recommend quality improvements for next cycle",
            ],
        },
    },
}

DEFAULT_MONITORING_RELATIONSHIPS: dict[str, dict[str, Any]] = {
    "adaptive": {
        "template_id": "status-report-template",
        "agent_id": "project-lifecycle-governance",
        "connector_id": "power-bi",
        "canvas_ui": "dashboard",
        "assistant_suggested_actions": [
            "Review iteration throughput and quality trends",
            "Highlight interventions for the next sprint cycle",
        ],
    },
    "predictive": {
        "template_id": "status-report-template",
        "agent_id": "project-lifecycle-governance",
        "connector_id": "power-bi",
        "canvas_ui": "dashboard",
        "assistant_suggested_actions": [
            "Assess stage-gate readiness from control tower metrics",
            "Escalate baseline variances and corrective actions",
        ],
    },
    "hybrid": {
        "template_id": "status-report-template",
        "agent_id": "workflow-process-engine",
        "connector_id": "power-bi",
        "canvas_ui": "dashboard",
        "assistant_suggested_actions": [
            "Balance predictive controls with adaptive outcomes",
            "Prioritise cross-team actions from live delivery signals",
        ],
    },
}


def _build_monitoring_activities(methodology_id: str) -> list[dict[str, Any]]:
    relationships = DEFAULT_MONITORING_RELATIONSHIPS.get(methodology_id, {})
    monitoring_nodes = [
        {
            "id": "monitoring-project-performance-insights",
            "name": "Project Performance & Insights Dashboard",
            "description": "Control tower dashboard for cross-lifecycle project performance.",
            "category": "monitoring",
            "recommended_canvas_tab": "dashboard",
            "assistant_prompts": relationships.get("assistant_suggested_actions", []),
            "prerequisites": [],
            "metadata": {
                "template_id": relationships.get("template_id"),
                "agent_id": relationships.get("agent_id"),
                "connector_id": relationships.get("connector_id"),
                "relationships": relationships,
            },
        },
        {
            "id": "monitoring-cross-cutting-risk-control",
            "name": "Cross-cutting Risk & Issue Control",
            "description": "Track and govern risk, issue, and dependency posture across all stages.",
            "category": "monitoring",
            "recommended_canvas_tab": "spreadsheet",
            "assistant_prompts": [
                "Review top risks and unresolved blockers",
                "Generate mitigation and escalation actions",
            ],
            "prerequisites": [],
            "metadata": {
                "template_id": "risk_register_template",
                "agent_id": "risk-issue-management",
                "connector_id": "servicenow",
            },
        },
        {
            "id": "monitoring-benefits-value-realisation",
            "name": "Benefits & Value Realisation Tracking",
            "description": "Monitor benefits attainment, KPI drift, and corrective governance actions.",
            "category": "monitoring",
            "recommended_canvas_tab": "document",
            "assistant_prompts": [
                "Compare realised outcomes versus expected benefits",
                "Prepare value-realisation commentary for governance",
            ],
            "prerequisites": [],
            "metadata": {
                "template_id": "benefits-realisation-plan",
                "agent_id": "analytics-insights",
                "connector_id": "power-bi",
            },
        },
    ]
    for index, node in enumerate(monitoring_nodes, start=1):
        node["order"] = index
    return monitoring_nodes


def _resolve_relationships(
    methodology_id: str,
    node: dict[str, Any],
    inherited: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node_relationships = node.get("relationships")
    if isinstance(node_relationships, dict) and node_relationships:
        return node_relationships

    stage_wbs = str(node.get("wbs", "")).split(".")
    stage_key = ".".join(stage_wbs[:2]) if len(stage_wbs) > 1 else str(node.get("wbs", ""))
    defaults = DEFAULT_STAGE_RELATIONSHIPS.get(methodology_id, {})
    return inherited or defaults.get(stage_key, defaults.get("default", {}))


def _load_methodology_overrides() -> dict[str, Any]:
    if not METHODOLOGY_STORAGE_PATH.exists():
        return {"methodologies": {}}
    with METHODOLOGY_STORAGE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _validate_node(node: dict[str, Any], methodology_id: str, seen: set[str]) -> None:
    required = ("id", "wbs", "title", "type", "order")
    for key in required:
        if key not in node:
            raise ValueError(f"{methodology_id}: node missing `{key}`")
    if node["id"] in seen:
        raise ValueError(f"{methodology_id}: duplicate node id `{node['id']}`")
    seen.add(node["id"])
    for child in node.get("children", []) or []:
        _validate_node(child, methodology_id, seen)


def _node_to_activity(
    node: dict[str, Any],
    prereqs: list[str],
    methodology_id: str,
    inherited_relationships: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relationships = _resolve_relationships(methodology_id, node, inherited_relationships)
    children = sorted(node.get("children", []) or [], key=lambda item: item["order"])
    child_activities: list[dict[str, Any]] = []
    previous_child_id: str | None = None
    for child in children:
        child_prereqs = [previous_child_id] if previous_child_id else []
        child_activities.append(
            _node_to_activity(child, child_prereqs, methodology_id, relationships)
        )
        if not child.get("parallel"):
            previous_child_id = child["id"]

    return {
        "id": node["id"],
        "name": node["title"],
        "description": f"WBS {node['wbs']}",
        "assistant_prompts": relationships.get("assistant_suggested_actions", []),
        "prerequisites": prereqs,
        "category": "methodology",
        "recommended_canvas_tab": relationships.get("canvas_ui", "document"),
        "wbs": node["wbs"],
        "type": node["type"],
        "order": node["order"],
        "children": child_activities,
        "metadata": {
            "repeatable": bool(node.get("repeatable", False)),
            "parallel": bool(node.get("parallel", False)),
            "gates": node.get("gates", []),
            "template_id": relationships.get("template_id"),
            "agent_id": relationships.get("agent_id"),
            "connector_id": relationships.get("connector_id"),
            "relationships": relationships,
        },
    }


def _normalize_methodology_from_nodes(
    payload: dict[str, Any], methodology_id: str
) -> dict[str, Any]:
    seen: set[str] = set()
    nodes = payload.get("nodes", [])
    for node in nodes:
        _validate_node(node, methodology_id, seen)

    stages = []
    previous_stage_id: str | None = None
    previous_stage_last_activity_id: str | None = None
    for node in sorted(nodes, key=lambda item: item["order"]):
        stage_relationships = _resolve_relationships(methodology_id, node)
        activities = []
        previous_activity_id: str | None = previous_stage_last_activity_id
        for activity_node in sorted(node.get("children", []) or [], key=lambda item: item["order"]):
            prereqs = [previous_activity_id] if previous_activity_id else []
            activities.append(
                _node_to_activity(
                    activity_node,
                    prereqs,
                    methodology_id,
                    stage_relationships,
                )
            )
            if not activity_node.get("parallel"):
                previous_activity_id = activity_node["id"]

        stage = {
            "id": node["id"],
            "name": node["title"],
            "description": f"WBS {node['wbs']}",
            "activities": activities,
            "prerequisites": [previous_stage_id] if previous_stage_id else [],
            "order": node["order"],
            "metadata": {
                "wbs": node["wbs"],
                "type": node["type"],
                "parallel": bool(node.get("parallel", False)),
                "repeatable": bool(node.get("repeatable", False)),
                "gates": node.get("gates", []),
                "template_id": stage_relationships.get("template_id"),
                "agent_id": stage_relationships.get("agent_id"),
                "connector_id": stage_relationships.get("connector_id"),
                "canvas_ui": stage_relationships.get("canvas_ui", "document"),
                "assistant_suggested_actions": stage_relationships.get(
                    "assistant_suggested_actions", []
                ),
            },
        }
        stages.append(stage)
        if not node.get("parallel"):
            previous_stage_id = node["id"]
            previous_stage_last_activity_id = previous_activity_id

    return {
        "id": payload.get("id", methodology_id),
        "name": payload.get("name", methodology_id.title()),
        "description": payload.get("description", ""),
        "type": payload.get("type", "custom"),
        "version": str(payload.get("version", "1.0")),
        "stages": stages,
        "monitoring": _build_monitoring_activities(methodology_id),
        "navigation_nodes": nodes,
        "gates": _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "gates.yaml").get("gates", []),
    }


def _load_methodology_map(methodology_id: str) -> dict[str, Any]:
    payload = _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "map.yaml")
    if not payload:
        raise ValueError(f"Methodology `{methodology_id}` has no map.yaml")

    if payload.get("nodes"):
        return _normalize_methodology_from_nodes(payload, methodology_id)

    if payload.get("stages"):
        # legacy shape passthrough
        return {
            "id": payload.get("methodology", methodology_id),
            "name": payload.get("methodology", methodology_id).title(),
            "description": payload.get("description", ""),
            "type": payload.get("methodology", "custom"),
            "version": str(payload.get("version", "1.0")),
            "stages": payload.get("stages", []),
            "monitoring": payload.get("monitoring", []),
            "navigation_nodes": payload.get("stages", []),
            "gates": _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "gates.yaml").get(
                "gates", []
            ),
        }

    raise ValueError(f"Methodology `{methodology_id}` map.yaml must contain `nodes` or `stages`.")


def _discover_methodology_ids() -> list[str]:
    return sorted(path.parent.name for path in METHODOLOGY_DOCS_ROOT.glob("*/map.yaml"))


def _load_all_methodologies() -> dict[str, dict[str, Any]]:
    maps: dict[str, dict[str, Any]] = {}
    for methodology_id in _discover_methodology_ids():
        maps[methodology_id] = _load_methodology_map(methodology_id)

    if "adaptive" in maps:
        maps["adaptive"] = maps["adaptive"]
    if "predictive" in maps:
        maps["predictive"] = maps["predictive"]
    return maps


METHODOLOGY_MAPS = _load_all_methodologies()


def available_methodologies() -> list[str]:
    overrides = _load_methodology_overrides().get("methodologies", {})
    keys = set(METHODOLOGY_MAPS.keys())
    keys.update(overrides.keys())
    return sorted(keys)


def get_default_methodology_map(methodology_id: str | None) -> dict[str, Any]:
    if methodology_id and methodology_id in METHODOLOGY_MAPS:
        return METHODOLOGY_MAPS[methodology_id]
    return METHODOLOGY_MAPS.get("adaptive") or next(iter(METHODOLOGY_MAPS.values()))


def get_methodology_map(methodology_id: str | None) -> dict[str, Any]:
    selected_id = methodology_id if methodology_id in METHODOLOGY_MAPS else "adaptive"
    overrides = _load_methodology_overrides().get("methodologies", {})
    override_payload = overrides.get(selected_id, {})
    override_map = override_payload.get("map") if isinstance(override_payload, dict) else None
    if override_map:
        return override_map
    return get_default_methodology_map(selected_id)
