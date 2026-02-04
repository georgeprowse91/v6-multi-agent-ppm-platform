from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("email_validator")


def _load_web_app():
    module_path = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "main.py"
    spec = spec_from_file_location("web_main_governance", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_governance_api_endpoints() -> None:
    web = _load_web_app()
    client = TestClient(web.app)
    endpoints = {
        "/api/approvals": ("pending_count", "items", "queues"),
        "/api/workflow-monitoring": ("status_board", "runs", "bottlenecks"),
        "/api/document-search": ("query", "results", "filters"),
        "/api/lessons-learned": ("categories", "entries", "recommendations"),
        "/api/audit-log": ("entries", "filters", "evidence_packs"),
    }

    for path, required_keys in endpoints.items():
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        for key in required_keys:
            assert key in payload
