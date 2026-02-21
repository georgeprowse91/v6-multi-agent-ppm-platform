from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "examples" / "demo-scenarios"


def test_demo_mode_references_scenario_assets():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    for filename in [
        "portfolio-health.json",
        "lifecycle-metrics.json",
        "approvals.json",
        "workflow-monitoring.json",
        "wbs.json",
        "schedule.json",
    ]:
        assert filename in app_js


def test_demo_guided_tour_hooks_present():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "startGuidedTour" in app_js
    assert "skipGuidedTour" in app_js
    assert "Shepherd" in app_js


def test_demo_mode_uses_app_routes_instead_of_legacy_workspace_routes():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "/app" in app_js
    assert "/v1/workspace?demo=true" not in app_js
    assert "/workspace?demo=true" not in app_js


def test_demo_scenario_files_exist():
    for filename in [
        "approvals.json",
        "workflow-monitoring.json",
        "wbs.json",
        "schedule.json",
    ]:
        assert (DEMO_DIR / filename).exists()
