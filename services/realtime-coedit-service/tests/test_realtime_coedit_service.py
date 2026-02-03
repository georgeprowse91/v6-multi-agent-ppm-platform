from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("realtime_coedit_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _build_token(secret: str, tenant_id: str) -> str:
    return jwt.encode(
        {"sub": "user-1", "tenant_id": tenant_id, "roles": ["editor"]},
        secret,
        algorithm="HS256",
    )


def test_session_create_and_history(monkeypatch) -> None:
    secret = "test-secret"
    monkeypatch.setenv("IDENTITY_JWT_SECRET", secret)
    token = _build_token(secret, "tenant-a")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-a"}

    with TestClient(module.app) as client:
        response = client.post(
            "/v1/sessions",
            json={"document_id": "doc-1", "initial_content": "hello", "classification": "internal"},
            headers=headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["document_id"] == "doc-1"

        history = client.get("/v1/documents/doc-1/history?limit=10&offset=0", headers=headers)
        assert history.status_code == 200
        assert history.headers["X-Total-Count"] == "1"
        entries = history.json()
        assert entries[0]["content"] == "hello"
