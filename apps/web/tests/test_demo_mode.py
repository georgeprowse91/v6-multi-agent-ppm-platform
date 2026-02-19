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


def test_demo_scenario_files_exist():
    for filename in [
        "approvals.json",
        "workflow-monitoring.json",
        "wbs.json",
        "schedule.json",
    ]:
        assert (DEMO_DIR / filename).exists()


def test_workspace_demo_route_redirects_to_spa_entrypoint():
    import importlib
    import sys
    import types

    from fastapi.testclient import TestClient

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if "email_validator" not in sys.modules:
        module = types.ModuleType("email_validator")
        module.EmailNotValidError = ValueError
        module.validate_email = lambda value, **kwargs: types.SimpleNamespace(email=value)
        sys.modules["email_validator"] = module

    if "event_bus" not in sys.modules:
        module = types.ModuleType("event_bus")
        module.EventHandler = object
        module.EventRecord = dict

        class _Bus:
            async def publish(self, *args, **kwargs):
                return None

        module.ServiceBusEventBus = _Bus
        module.get_event_bus = lambda *args, **kwargs: _Bus()
        sys.modules["event_bus"] = module

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    import main

    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/workspace?demo=true", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/app?demo=true"
