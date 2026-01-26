from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from audit_storage import LocalEncryptedWORMStorage

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("audit_log_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def _auth_headers(monkeypatch, tenant_id: str = "tenant-alpha") -> dict[str, str]:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["auditor"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "audit-log"


def test_ingest_and_fetch_event(monkeypatch) -> None:
    storage_path = (
        Path(__file__).resolve().parents[3] / "services" / "audit-log" / "storage" / "immutable"
    )
    if storage_path.exists():
        for path in storage_path.glob("*.enc"):
            path.unlink()
    monkeypatch.setenv(
        "AUDIT_LOG_ENCRYPTION_KEY", "Y2hhbmdlLW1lLW5vdC1wcm9kLWsxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
    )
    monkeypatch.setenv("AUDIT_WORM_LOCAL_PATH", str(storage_path))

    payload = {
        "id": "evt-123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "tenant-alpha",
        "actor": {"id": "user-1", "type": "user", "roles": ["auditor"]},
        "action": "project.create",
        "resource": {"id": "proj-9", "type": "project"},
        "outcome": "success",
        "classification": "internal",
        "metadata": {"ip": "127.0.0.1"},
        "trace_id": "trace-1",
        "correlation_id": "corr-1",
    }

    response = client.post("/audit/events", json=payload, headers=_auth_headers(monkeypatch))
    assert response.status_code == 200
    assert response.json()["event"]["id"] == "evt-123"

    fetch = client.get("/audit/events/evt-123", headers=_auth_headers(monkeypatch))
    assert fetch.status_code == 200
    assert fetch.json()["action"] == "project.create"

    assert storage_path.exists()
    encrypted_files = list(storage_path.glob("*.enc"))
    assert encrypted_files

    storage = LocalEncryptedWORMStorage(
        storage_path, "Y2hhbmdlLW1lLW5vdC1wcm9kLWsxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
    )
    stored = storage.fetch_event("evt-123")
    assert stored
    assert stored["retention_policy"] == "internal-1y"
    assert stored["retention_until"]


def test_immutable_audit_event(monkeypatch) -> None:
    storage_path = (
        Path(__file__).resolve().parents[3] / "services" / "audit-log" / "storage" / "immutable"
    )
    if storage_path.exists():
        for path in storage_path.glob("*.enc"):
            path.unlink()
    monkeypatch.setenv(
        "AUDIT_LOG_ENCRYPTION_KEY", "Y2hhbmdlLW1lLW5vdC1wcm9kLWsxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
    )
    monkeypatch.setenv("AUDIT_WORM_LOCAL_PATH", str(storage_path))

    payload = {
        "id": "evt-immutable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "tenant-alpha",
        "actor": {"id": "user-2", "type": "user", "roles": ["auditor"]},
        "action": "portfolio.update",
        "resource": {"id": "port-1", "type": "portfolio"},
        "outcome": "success",
        "classification": "internal",
    }

    response = client.post("/audit/events", json=payload, headers=_auth_headers(monkeypatch))
    assert response.status_code == 200

    duplicate = client.post("/audit/events", json=payload, headers=_auth_headers(monkeypatch))
    assert duplicate.status_code == 409
