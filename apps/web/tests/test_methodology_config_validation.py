import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
METHODOLOGY_ROOT = ROOT / "docs" / "methodology"
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from methodologies import _load_methodology_map  # noqa: E402


def _walk_nodes(nodes, seen_ids, methodology_id):
    for node in nodes:
        assert node.get("id"), f"{methodology_id}: node missing `id`"
        assert node.get(
            "title"
        ), f"{methodology_id}:{node.get('id', '<unknown>')}: node missing `title`"
        assert node.get("order") is not None, f"{methodology_id}:{node['id']}: node missing `order`"
        assert node["id"] not in seen_ids, f"{methodology_id}: duplicate node id `{node['id']}`"
        seen_ids.add(node["id"])
        children = node.get("children", [])
        if children:
            orders = [child["order"] for child in children]
            assert orders == sorted(
                orders
            ), f"{methodology_id}:{node['id']}: children are not stably ordered"
            _walk_nodes(children, seen_ids, methodology_id)


def test_yaml_schema_validation_fails_fast_with_clear_error():
    for map_file in METHODOLOGY_ROOT.glob("*/map.yaml"):
        methodology_id = map_file.parent.name
        try:
            _load_methodology_map(methodology_id)
        except ValueError as exc:
            pytest.fail(f"{methodology_id}: invalid methodology schema in {map_file}: {exc}")


def test_methodology_nodes_have_unique_ids_and_stable_ordering():
    for map_file in METHODOLOGY_ROOT.glob("*/map.yaml"):
        payload = yaml.safe_load(map_file.read_text()) or {}
        nodes = payload.get("nodes", [])
        if not nodes:
            continue
        seen_ids = set()
        _walk_nodes(nodes, seen_ids, map_file.parent.name)


def test_loaded_methodologies_have_non_empty_stages_and_unique_activity_ids():
    for map_file in METHODOLOGY_ROOT.glob("*/map.yaml"):
        payload = yaml.safe_load(map_file.read_text()) or {}
        if not payload.get("nodes"):
            continue

        methodology_id = map_file.parent.name
        methodology_map = _load_methodology_map(methodology_id)

        stages = methodology_map.get("stages", [])
        assert stages, f"{methodology_id}: expected non-empty stages"

        activity_ids = []
        for stage in stages:
            activities = stage.get("activities", [])
            assert activities, f"{methodology_id}:{stage.get('id')}: expected non-empty activities"
            stage_orders = [activity["order"] for activity in activities]
            assert stage_orders == sorted(
                stage_orders
            ), f"{methodology_id}:{stage.get('id')}: activities are not stably ordered"
            activity_ids.extend(activity["id"] for activity in activities)

        assert len(activity_ids) == len(
            set(activity_ids)
        ), f"{methodology_id}: duplicate activity ids found in normalized map"


def test_gates_reference_existing_wbs():
    for map_file in METHODOLOGY_ROOT.glob("*/map.yaml"):
        payload = yaml.safe_load(map_file.read_text()) or {}
        nodes = payload.get("nodes", [])
        if not nodes:
            continue
        methodology_id = map_file.parent.name
        wbs = set()

        def collect(items):
            for item in items:
                wbs.add(item["wbs"])
                collect(item.get("children", []))

        collect(nodes)
        gates_file = map_file.parent / "gates.yaml"
        if not gates_file.exists():
            continue
        gates = (yaml.safe_load(gates_file.read_text()) or {}).get("gates", [])
        for gate in gates:
            assert (
                gate["associated_wbs"] in wbs
            ), f"{methodology_id}:{gate['id']} invalid associated_wbs"
