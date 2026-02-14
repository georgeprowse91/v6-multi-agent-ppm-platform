from __future__ import annotations

import importlib.util
from pathlib import Path

VALID_CANVAS_TABS = {
    "document",
    "tree",
    "timeline",
    "dependency-map",
    "program-roadmap",
    "spreadsheet",
    "dashboard",
}


def _load_methodologies_module():
    module_path = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "methodologies.py"
    spec = importlib.util.spec_from_file_location("web_methodologies", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_methodology_activities_have_relationship_mappings() -> None:
    module = _load_methodologies_module()

    for methodology_id in ("adaptive", "predictive", "hybrid"):
        methodology_map = module.get_methodology_map(methodology_id)
        assert methodology_map["stages"], f"Expected stages in {methodology_id}"

        for stage in methodology_map["stages"]:
            assert stage["activities"], f"Expected activities for {methodology_id} stage {stage['id']}"
            for activity in stage["activities"]:
                metadata = activity.get("metadata", {})
                assert metadata.get("template_id"), f"{activity['id']} missing template relationship"
                assert metadata.get("agent_id"), f"{activity['id']} missing agent relationship"
                assert metadata.get("connector_id"), f"{activity['id']} missing connector relationship"
                assert activity.get("assistant_prompts"), f"{activity['id']} missing assistant suggested actions"
                assert activity.get("recommended_canvas_tab") in VALID_CANVAS_TABS, (
                    f"{activity['id']} has unsupported canvas tab"
                )
