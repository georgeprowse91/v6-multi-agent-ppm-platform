from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_client(module_path: Path, module_name: str) -> TestClient:
    spec = spec_from_file_location(module_name, module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    sys.path.insert(0, str(module_path.parent))
    spec.loader.exec_module(module)
    return TestClient(module.app)


def _auth_headers(tenant_id: str = "tenant-alpha") -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def _auth_headers_missing_tenant() -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}


def _auth_headers_mismatch() -> dict[str, str]:
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
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-beta"}


def _set_auth_env(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")


def test_audit_log_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "audit-log" / "src" / "main.py", "audit_log_auth"
    )

    response = client.post("/v1/audit/events", json={"id": "evt-1"})
    assert response.status_code == 401

    response = client.post(
        "/v1/audit/events", json={"id": "evt-1"}, headers={"Authorization": "Bearer foo"}
    )
    assert response.status_code == 401

    payload = {
        "id": "evt-1",
        "timestamp": "2024-01-01T00:00:00Z",
        "tenant_id": "tenant-alpha",
        "actor": {"id": "user-1", "type": "user", "roles": ["auditor"]},
        "action": "project.read",
        "resource": {"id": "proj-1", "type": "project"},
        "outcome": "success",
        "classification": "internal",
    }
    response = client.post("/v1/audit/events", json=payload, headers=_auth_headers_mismatch())
    assert response.status_code == 403

    response = client.post("/v1/audit/events", json=payload, headers=_auth_headers_missing_tenant())
    assert response.status_code == 403


def test_data_sync_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "data-sync-service" / "src" / "main.py",
        "data_sync_auth",
    )

    response = client.post("/v1/sync/run", json={"connector": "jira", "dry_run": True})
    assert response.status_code == 401

    response = client.post(
        "/v1/sync/run",
        json={"connector": "jira", "dry_run": True},
        headers={"Authorization": "Bearer foo"},
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/sync/run",
        json={"connector": "jira", "dry_run": True},
        headers=_auth_headers_mismatch(),
    )
    assert response.status_code == 403

    response = client.post(
        "/v1/sync/run",
        json={"connector": "jira", "dry_run": True},
        headers=_auth_headers_missing_tenant(),
    )
    assert response.status_code == 403


def test_notification_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "notification-service" / "src" / "main.py",
        "notification_auth",
    )

    payload = {"template": "welcome", "variables": {}, "channel": "stdout"}
    response = client.post("/v1/notifications/send", json=payload)
    assert response.status_code == 401

    response = client.post(
        "/v1/notifications/send", json=payload, headers={"Authorization": "Bearer foo"}
    )
    assert response.status_code == 401

    response = client.post("/v1/notifications/send", json=payload, headers=_auth_headers_mismatch())
    assert response.status_code == 403

    response = client.post(
        "/v1/notifications/send", json=payload, headers=_auth_headers_missing_tenant()
    )
    assert response.status_code == 403


def test_policy_engine_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "policy-engine" / "src" / "main.py",
        "policy_engine_auth",
    )

    response = client.post(
        "/v1/rbac/evaluate",
        json={"tenant_id": "tenant-alpha", "roles": [], "permission": "project.read"},
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/rbac/evaluate",
        json={"tenant_id": "tenant-alpha", "roles": [], "permission": "project.read"},
        headers={"Authorization": "Bearer foo"},
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/rbac/evaluate",
        json={"tenant_id": "tenant-alpha", "roles": [], "permission": "project.read"},
        headers=_auth_headers_mismatch(),
    )
    assert response.status_code == 403

    response = client.post(
        "/v1/rbac/evaluate",
        json={"tenant_id": "tenant-alpha", "roles": [], "permission": "project.read"},
        headers=_auth_headers_missing_tenant(),
    )
    assert response.status_code == 403


def test_telemetry_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "telemetry-service" / "src" / "main.py",
        "telemetry_auth",
    )

    response = client.post(
        "/v1/telemetry/ingest", json={"source": "api", "payload": {"message": "hello"}}
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/telemetry/ingest",
        json={"source": "api", "payload": {"message": "hello"}},
        headers={"Authorization": "Bearer foo"},
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/telemetry/ingest",
        json={"source": "api", "payload": {"message": "hello"}},
        headers=_auth_headers_mismatch(),
    )
    assert response.status_code == 403

    response = client.post(
        "/v1/telemetry/ingest",
        json={"source": "api", "payload": {"message": "hello"}},
        headers=_auth_headers_missing_tenant(),
    )
    assert response.status_code == 403


def test_workflow_service_requires_auth(monkeypatch) -> None:
    _set_auth_env(monkeypatch)
    client = _load_client(
        REPO_ROOT / "services" / "workflow-service" / "src" / "main.py",
        "workflow_service_auth",
    )

    payload = {
        "workflow_id": "intake-triage",
        "tenant_id": "tenant-alpha",
        "classification": "internal",
        "payload": {"request": "run"},
        "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
    }
    response = client.post("/v1/workflows/start", json=payload)
    assert response.status_code == 401

    response = client.post(
        "/v1/workflows/start", json=payload, headers={"Authorization": "Bearer foo"}
    )
    assert response.status_code == 401

    response = client.post("/v1/workflows/start", json=payload, headers=_auth_headers_mismatch())
    assert response.status_code == 403

    response = client.post(
        "/v1/workflows/start", json=payload, headers=_auth_headers_missing_tenant()
    )
    assert response.status_code == 403
