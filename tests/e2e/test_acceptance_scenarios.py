from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

import jwt
from fastapi.testclient import TestClient


def _load_app(path: Path, module_name: str):
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app


def _client_for(path_parts: list[str], module_name: str) -> TestClient:
    path = Path(__file__).resolve().parents[2].joinpath(*path_parts)
    return TestClient(_load_app(path, module_name))


def _auth_headers() -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}


def test_api_root_status(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "api-gateway", "src", "api", "main.py"], "api_main")
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_api_version_metadata(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "api-gateway", "src", "api", "main.py"], "api_main_version")
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["service"] == "multi-agent-ppm-api"


def test_api_status_with_orchestrator(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    path = Path(__file__).resolve().parents[2] / "apps" / "api-gateway" / "src" / "api" / "main.py"
    spec = spec_from_file_location("api_main_status", path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    orchestrator = MagicMock(initialized=True)
    orchestrator.get_agent_count.return_value = 12
    module.orchestrator = orchestrator

    client = TestClient(module.app)
    response = client.get("/v1/status", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["agents_loaded"] == 12


def test_api_healthz(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "api-gateway", "src", "api", "main.py"], "api_main_health")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_identity_healthz() -> None:
    client = _client_for(["services", "identity-access", "src", "main.py"], "identity_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "identity-access"


def test_identity_token_validation(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {"sub": "user-123", "tenant_id": "tenant-alpha", "aud": "ppm-platform"},
        "test-secret",
        algorithm="HS256",
    )
    client = _client_for(
        ["services", "identity-access", "src", "main.py"], "identity_main_validate"
    )
    response = client.post("/v1/auth/validate", json={"token": token})
    assert response.status_code == 200
    assert response.json()["active"] is True


def test_workflow_service_healthz() -> None:
    client = _client_for(["apps", "workflow-service", "src", "main.py"], "workflow_main_health")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "workflow-service"


def test_workflow_service_start(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "workflow-service", "src", "main.py"], "workflow_main_start")
    payload = {
        "workflow_id": "intake-triage",
        "tenant_id": "tenant-alpha",
        "classification": "internal",
        "payload": {"request": "upgrade"},
        "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
    }
    response = client.post("/v1/workflows/start", json=payload, headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_document_service_healthz(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "document-service", "src", "main.py"], "document_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "document-service"


def test_document_service_create_and_list(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("DOCUMENT_DB_PATH", str(tmp_path / "documents.db"))
    client = _client_for(["apps", "document-service", "src", "main.py"], "document_main_write")

    response = client.post(
        "/v1/documents",
        json={"name": "spec", "content": "hello", "classification": "internal"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200

    list_response = client.get("/v1/documents", headers=_auth_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_policy_engine_healthz() -> None:
    client = _client_for(["services", "policy-engine", "src", "main.py"], "policy_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "policy-engine"


def test_data_sync_service_healthz() -> None:
    client = _client_for(["services", "data-sync-service", "src", "main.py"], "data_sync_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "data-sync-service"


def test_audit_log_service_healthz() -> None:
    client = _client_for(["services", "audit-log", "src", "main.py"], "audit_log_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "audit-log"


def test_connector_hub_healthz(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "connector-hub", "src", "main.py"], "connector_hub_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "connector-hub"


def test_analytics_service_healthz(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "analytics-service", "src", "main.py"], "analytics_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "analytics-service"


def test_orchestration_service_healthz(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    client = _client_for(["apps", "orchestration-service", "src", "main.py"], "orchestration_main")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "orchestration-service"
