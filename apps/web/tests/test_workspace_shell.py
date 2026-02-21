import importlib
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

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


def test_root_serves_spa_entrypoint_contract():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_workspace_route_contract_is_retired():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/workspace", follow_redirects=False)

    assert response.status_code == 404


def test_workspace_demo_query_route_contract_is_retired():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/workspace?demo=true", follow_redirects=False)

    assert response.status_code == 404


def test_legacy_workspace_shell_static_assets_are_not_served():
    client = TestClient(importlib.reload(main).app)

    for asset_path in [
        "/static/workspace.html",
        "/static/workspace-shell.html",
        "/static/workspace-shell.js",
        "/static/workspace.js",
    ]:
        response = client.get(asset_path, follow_redirects=False)
        assert response.status_code == 404


def test_app_shell_route_contract_remains_healthy():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/app", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/app"


def test_session_api_contract_is_json_for_spa_bootstrap():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is False
    assert "tenant_id" in payload
    assert "roles" in payload


def test_workspace_state_api_route_remains_registered_for_spa_clients():
    client = TestClient(importlib.reload(main).app)
    response = client.get("/v1/api/workspace/demo-1", follow_redirects=False)

    assert response.status_code in {200, 401}
