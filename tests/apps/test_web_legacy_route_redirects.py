from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient


def _load_web_app():
    module_path = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "main.py"
    spec = spec_from_file_location("web_main_legacy_redirects", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_legacy_routes_always_redirect_to_spa() -> None:
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


def test_migration_map_reports_redirect_compatibility() -> None:
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
    assert payload["compatibility"]["legacy_html"] == "Legacy HTML compatibility removed; routes redirect to SPA."
