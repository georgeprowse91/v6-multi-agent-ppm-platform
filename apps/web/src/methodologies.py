from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
METHODOLOGY_DOCS_ROOT = REPO_ROOT / "docs" / "methodology"
METHODOLOGY_STORAGE_PATH = Path(__file__).resolve().parents[1] / "storage" / "methodology_definitions.json"


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


def _node_to_activity(node: dict[str, Any], prereqs: list[str]) -> dict[str, Any]:
    children = sorted(node.get("children", []) or [], key=lambda item: item["order"])
    child_activities: list[dict[str, Any]] = []
    previous_child_id: str | None = None
    for child in children:
        child_prereqs = [previous_child_id] if previous_child_id else []
        child_activities.append(_node_to_activity(child, child_prereqs))
        if not child.get("parallel"):
            previous_child_id = child["id"]

    return {
        "id": node["id"],
        "name": node["title"],
        "description": f"WBS {node['wbs']}",
        "assistant_prompts": [],
        "prerequisites": prereqs,
        "category": "methodology",
        "recommended_canvas_tab": "document",
        "wbs": node["wbs"],
        "type": node["type"],
        "order": node["order"],
        "children": child_activities,
        "metadata": {
            "repeatable": bool(node.get("repeatable", False)),
            "parallel": bool(node.get("parallel", False)),
            "gates": node.get("gates", []),
        },
    }


def _normalize_methodology_from_nodes(payload: dict[str, Any], methodology_id: str) -> dict[str, Any]:
    seen: set[str] = set()
    nodes = payload.get("nodes", [])
    for node in nodes:
        _validate_node(node, methodology_id, seen)

    stages = []
    previous_stage_id: str | None = None
    previous_stage_last_activity_id: str | None = None
    for node in sorted(nodes, key=lambda item: item["order"]):
        activities = []
        previous_activity_id: str | None = previous_stage_last_activity_id
        for activity_node in sorted(node.get("children", []) or [], key=lambda item: item["order"]):
            prereqs = [previous_activity_id] if previous_activity_id else []
            activities.append(_node_to_activity(activity_node, prereqs))
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
        "monitoring": [],
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
            "gates": _load_yaml(METHODOLOGY_DOCS_ROOT / methodology_id / "gates.yaml").get("gates", []),
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
