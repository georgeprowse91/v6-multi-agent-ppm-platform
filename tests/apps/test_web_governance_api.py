from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("email_validator")

_WEB_SRC = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"


def _load_web_app():
    # Ensure web/src is first in sys.path to prevent config.py namespace collision
    # with other services (e.g. orchestration-service) that also have a top-level config.py.
    web_src_str = str(_WEB_SRC.resolve())
    if web_src_str not in sys.path:
        sys.path.insert(0, web_src_str)

    # Clear cached web modules so we get a fresh app instance with all routes registered.
    # bootstrap.py returns a module-level singleton (legacy_app); stale cached modules
    # can cause routes to be missing or middleware to fail.
    for mod_name in list(sys.modules):
        if mod_name in {"bootstrap", "legacy_main", "middleware", "routes",
                        "web_main_governance"}:
            sys.modules.pop(mod_name, None)

    module_path = _WEB_SRC / "main.py"
    spec = spec_from_file_location("web_main_governance", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_governance_api_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set required env vars so web app config validation passes
    monkeypatch.setenv("API_GATEWAY_URL", "http://api-gateway:8000")
    monkeypatch.setenv("IDENTITY_ACCESS_URL", "http://identity:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_URL", "http://workflow:8000")
    # Clear the lru_cache so our env vars take effect
    try:
        import config as _web_cfg  # noqa: PLC0415
        _web_cfg.get_settings.cache_clear()
    except Exception:  # noqa: BLE001
        pass
    web = _load_web_app()
    client = TestClient(web.app)
    # Routes are registered under the /v1 prefix (api_router in legacy_main.py)
    endpoints = {
        "/v1/api/approvals": ("pending_count", "items", "queues"),
        "/v1/api/workflow-monitoring": ("status_board", "runs", "bottlenecks"),
        "/v1/api/document-search": ("query", "results", "filters"),
        "/v1/api/lessons-learned": ("categories", "entries", "recommendations"),
        "/v1/api/audit-log": ("entries", "filters", "evidence_packs"),
    }

    for path, required_keys in endpoints.items():
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        for key in required_keys:
            assert key in payload
