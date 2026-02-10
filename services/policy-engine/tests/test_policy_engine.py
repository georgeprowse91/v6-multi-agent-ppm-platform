from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

sys.path.insert(0, str(SERVICE_ROOT / "src"))
os.environ.setdefault("IDENTITY_JWT_SECRET", "test-secret")

spec = spec_from_file_location("policy_engine_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def _auth_headers(monkeypatch, tenant_id: str = "tenant-alpha") -> dict[str, str]:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["policy_admin"],
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
    assert response.json()["service"] == "policy-engine"


def test_policy_evaluate_allow(monkeypatch) -> None:
    bundle = {
        "apiVersion": "ppm.policies/v1",
        "kind": "PolicyBundle",
        "metadata": {"name": "demo", "version": "1.0.0", "owner": "qa", "scope": "test"},
        "policies": [
            {
                "id": "test-001",
                "name": "Require owner",
                "description": "Ensure metadata owner is set",
                "severity": "low",
                "enforcement": "advisory",
                "rules": [
                    {
                        "field": "metadata.owner",
                        "operator": "contains",
                        "value": "qa",
                    }
                ],
            }
        ],
    }
    response = client.post(
        "/v1/policies/evaluate", json={"bundle": bundle}, headers=_auth_headers(monkeypatch)
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"


def test_rbac_evaluate_allow(monkeypatch) -> None:
    payload = {
        "tenant_id": "tenant-alpha",
        "roles": ["portfolio_admin"],
        "permission": "project.read",
        "classification": "internal",
    }
    response = client.post("/v1/rbac/evaluate", json=payload, headers=_auth_headers(monkeypatch))
    assert response.status_code == 200
    assert response.json()["decision"] == "allow"


def test_abac_evaluate_allow(monkeypatch) -> None:
    payload = {
        "tenant_id": "tenant-alpha",
        "subject": {"sub": "user-123", "business_unit": "finance"},
        "action": "project.read",
        "resource": {"id": "proj-1", "business_unit": "finance", "classification": "internal"},
        "context": {"path": "/v1/projects/proj-1"},
    }
    response = client.post("/v1/abac/evaluate", json=payload, headers=_auth_headers(monkeypatch))
    assert response.status_code == 200
    assert response.json()["decision"] == "allow"


def test_abac_evaluate_deny(monkeypatch) -> None:
    payload = {
        "tenant_id": "tenant-alpha",
        "subject": {"sub": "user-123", "employment_type": "contractor"},
        "action": "project.read",
        "resource": {"id": "proj-1", "classification": "restricted"},
    }
    response = client.post("/v1/abac/evaluate", json=payload, headers=_auth_headers(monkeypatch))
    assert response.status_code == 200
    assert response.json()["decision"] == "deny"


def test_compliance_evaluate_denies_without_consent(monkeypatch) -> None:
    payload = {
        "payload": {
            "personal_data": {"email": "user@example.com"},
            "consent": {"granted": False},
        }
    }
    response = client.post(
        "/v1/compliance/evaluate", json=payload, headers=_auth_headers(monkeypatch)
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "deny"
