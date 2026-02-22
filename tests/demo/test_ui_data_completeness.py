from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "data" / "demo"
WEB_DEMO_SEED = REPO_ROOT / "apps" / "web" / "data" / "demo_seed.json"

UI_MINIMUM_COUNTS = {
    "projects": 10,
    "tasks": 100,
    "risks": 30,
    "issues": 30,
    "approvals": 10,
    "vendors": 10,
    "contracts": 10,
}

NAVIGATION_SECTION_BACKING_DATA = {
    "approvals": "approvals",
    "connectors": "connectors",
    "audit_log": "audit_log",
    "dashboards": "dashboards",
    "notifications": "notifications",
    "demo_run": "demo_run_log",
}


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_demo_ui_minimum_visible_counts() -> None:
    """Protect the demo UX from sparse datasets that render empty pages."""
    demo_data = {path.stem: _read_json(path) for path in DEMO_DIR.glob("*.json")}

    for entity_name, minimum in UI_MINIMUM_COUNTS.items():
        assert entity_name in demo_data, f"Missing demo dataset: {entity_name}.json"
        records = demo_data[entity_name]
        assert isinstance(records, list), f"{entity_name}.json must contain a list of records"
        assert (
            len(records) >= minimum
        ), f"{entity_name}.json only has {len(records)} records; expected at least {minimum}"


def test_web_demo_seed_has_required_ui_data() -> None:
    """Validate web demo seed data expected by UI navigation and demo flows."""
    assert WEB_DEMO_SEED.exists(), "apps/web/data/demo_seed.json must exist for demo mode"

    seed = _read_json(WEB_DEMO_SEED)

    users = seed.get("users")
    assert isinstance(users, list) and users, "apps/web/data/demo_seed.json must include demo users"

    if "conversations" in seed:
        conversations = seed.get("conversations")
        assert (
            isinstance(conversations, list) and conversations
        ), "apps/web/data/demo_seed.json includes conversations, but it is empty"

    for section, data_key in NAVIGATION_SECTION_BACKING_DATA.items():
        assert (
            data_key in seed
        ), f"apps/web/data/demo_seed.json missing backing data for '{section}' navigation section"
        section_data = seed[data_key]
        assert (
            section_data
        ), f"apps/web/data/demo_seed.json has empty backing data for '{section}' navigation section"


def test_demo_run_log_fixture_exists_and_has_agents() -> None:
    """Ensure demo run activity fixture exists for the demo run page."""
    demo_run_log_path = REPO_ROOT / "apps" / "web" / "data" / "demo" / "demo_run_log.json"
    assert demo_run_log_path.exists(), "apps/web/data/demo/demo_run_log.json must exist"

    run_log = _read_json(demo_run_log_path)
    agents = run_log.get("agents") if isinstance(run_log, dict) else None
    assert isinstance(agents, list) and agents, "demo run log must include a non-empty agents list"
    assert len(agents) >= 25, "demo run log should include the full 25-agent execution record"
