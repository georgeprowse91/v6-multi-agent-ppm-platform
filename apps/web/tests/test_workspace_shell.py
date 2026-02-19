import importlib
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

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

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main


def test_index_links_to_app():
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert 'href="/app"' in index_html
    assert 'href="/workspace"' not in index_html


def test_workspace_shell_layout_strings():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    for label in [
        "Methodology",
        "Monitoring",
        "Approvals",
        "Lessons Learned",
        "Audit Log",
        "Document",
        "Tree",
        "Timeline",
        "Dependency Map",
        "Program Roadmap",
        "Spreadsheet",
        "Dashboard",
        "Assistant",
        "Select an activity to view guidance.",
    ]:
        assert label in app_js
    assert 'path === "/app"' in app_js
    assert 'path === "/workspace"' not in app_js


def test_workspace_css_asset_removed():
    assert not (STATIC_DIR / "workspace.css").exists()

def test_workspace_progress_bar_markup():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "workspace-stage-progress" in app_js
    assert 'style="width: ${progressValue}%"' in app_js
    assert "workspace-stage-progress-bar is-" in app_js


def test_workspace_topbar_active_link_markup():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "workspace-top-link" in app_js
    assert 'aria-current="page"' in app_js
    assert "is-active" in app_js


def test_workspace_route_redirects_to_app():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/workspace?project_id=demo-1&demo=true", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/app?project_id=demo-1&demo=true"
