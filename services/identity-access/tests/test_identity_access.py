from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("identity_access_main", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "identity-access"


def test_auth_validate_hs256() -> None:
    os.environ["IDENTITY_JWT_SECRET"] = "dev-secret"
    token = jwt.encode({"sub": "user-123"}, "dev-secret", algorithm="HS256")

    response = client.post("/auth/validate", json={"token": token})
    assert response.status_code == 200
    payload = response.json()
    assert payload["active"] is True
    assert payload["subject"] == "user-123"
