from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_WEB_SRC = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"


def _load_web_app():
    # Ensure web/src is first in sys.path to prevent config.py namespace collision
    web_src_str = str(_WEB_SRC.resolve())
    if web_src_str not in sys.path:
        sys.path.insert(0, web_src_str)

    # Clear cached web modules so each load gets a fresh app instance.
    # bootstrap.py returns a module-level singleton (legacy_app); without clearing,
    # the second test re-uses the already-started app and add_middleware() raises
    # RuntimeError("Cannot add middleware after an application has started").
    for mod_name in list(sys.modules):
        if mod_name in {"bootstrap", "legacy_main", "middleware", "routes",
                        "web_main_legacy_redirects"}:
            sys.modules.pop(mod_name, None)

    module_path = _WEB_SRC / "main.py"
    spec = spec_from_file_location("web_main_legacy_redirects", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_legacy_routes_always_redirect_to_spa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_GATEWAY_URL", "http://api-gateway:8000")
    monkeypatch.setenv("IDENTITY_ACCESS_URL", "http://identity:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_URL", "http://workflow:8000")
    try:
        import config as _web_cfg  # noqa: PLC0415
        _web_cfg.get_settings.cache_clear()
    except Exception:  # noqa: BLE001
        pass
    web = _load_web_app()
    client = TestClient(web.app)

    redirects = {
        "/v1/approvals": "/app/approvals",
        "/v1/workflow-monitoring": "/app/workflows/monitoring",
        "/v1/document-search": "/app/knowledge/documents",
        "/v1/lessons-learned": "/app/knowledge/lessons",
        "/v1/audit-log": "/app/admin/audit",
    }

    for route, destination in redirects.items():
        response = client.get(route, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == destination


def test_migration_map_reports_redirect_compatibility(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_GATEWAY_URL", "http://api-gateway:8000")
    monkeypatch.setenv("IDENTITY_ACCESS_URL", "http://identity:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_URL", "http://workflow:8000")
    try:
        import config as _web_cfg  # noqa: PLC0415
        _web_cfg.get_settings.cache_clear()
    except Exception:  # noqa: BLE001
        pass
    web = _load_web_app()
    client = TestClient(web.app)

    response = client.get("/v1/ui/migration-map")
    assert response.status_code == 200

    payload = response.json()
    assert "legacy_ui_enabled" not in payload
    assert payload["migration_status"] == {
        "legacy_ui_retired": True,
        "notes": "Legacy UI has been fully retired; compatibility is redirect-only.",
    }
    assert (
        payload["compatibility"]["legacy_html"]
        == "Legacy HTML compatibility removed; routes redirect to SPA."
    )
