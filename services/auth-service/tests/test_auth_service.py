from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("auth_service_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _build_token(secret: str, tenant_id: str) -> str:
    return jwt.encode({"sub": "user-1", "tenant_id": tenant_id}, secret, algorithm="HS256")


def test_validate_and_me(monkeypatch) -> None:
    secret = "test-secret"
    monkeypatch.setenv("AUTH_JWT_SECRET", secret)
    token = _build_token(secret, "tenant-a")

    with TestClient(module.app) as client:
        response = client.post("/v1/auth/validate", json={"token": token})
        assert response.status_code == 200
        payload = response.json()
        assert payload["active"] is True
        assert payload["subject"] == "user-1"

        response = client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-a"},
        )
        assert response.status_code == 200
        me_payload = response.json()
        assert me_payload["tenant_id"] == "tenant-a"
        assert me_payload["subject"] == "user-1"
