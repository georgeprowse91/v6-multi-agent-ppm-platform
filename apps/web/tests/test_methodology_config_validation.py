from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
METHODOLOGY_ROOT = ROOT / "docs" / "methodology"


def _walk(nodes, seen, parent_order=None):
    for node in nodes:
        assert node.get("id")
        assert node.get("title")
        assert node.get("order") is not None
        assert node["id"] not in seen
        seen.add(node["id"])
        if parent_order is not None:
            assert node["order"] >= parent_order
        children = node.get("children", [])
        if children:
            orders = [child["order"] for child in children]
            assert orders == sorted(orders)
            _walk(children, seen, node["order"])


def test_methodology_nodes_are_valid_and_stable():
    for map_file in METHODOLOGY_ROOT.glob("*/map.yaml"):
        payload = yaml.safe_load(map_file.read_text()) or {}
        if "nodes" not in payload:
            continue
        seen = set()
        _walk(payload["nodes"], seen)


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
            assert gate["associated_wbs"] in wbs, f"{methodology_id}:{gate['id']} invalid associated_wbs"
