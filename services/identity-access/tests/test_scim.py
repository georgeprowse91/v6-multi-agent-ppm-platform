from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"


def _load_identity_module() -> object:
    sys.path.insert(0, str(SERVICE_ROOT / "src"))
    module_name = f"identity_access_scim_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def scim_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SCIM_DB_PATH", str(tmp_path / "scim.db"))
    monkeypatch.setenv("SCIM_SERVICE_TOKEN", "env:SCIM_TOKEN")
    monkeypatch.setenv("SCIM_TOKEN", "scim-secret")
    module = _load_identity_module()
    return TestClient(module.app)


def _headers(tenant_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer scim-secret", "X-Tenant-ID": tenant_id}


def test_scim_auth_required(scim_client: TestClient) -> None:
    response = scim_client.get("/scim/v2/Users")
    assert response.status_code == 401


def test_scim_user_group_role_mapping_and_tenant_isolation(scim_client: TestClient) -> None:
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    user_payload = {"userName": "alice@example.com", "displayName": "Alice"}
    response = scim_client.post("/scim/v2/Users", json=user_payload, headers=_headers(tenant_a))
    assert response.status_code == 201
    user_id = response.json()["id"]

    group_payload = {"displayName": "PMO_ADMIN"}
    group_response = scim_client.post(
        "/scim/v2/Groups", json=group_payload, headers=_headers(tenant_a)
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    patch_payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "Add", "path": "members", "value": [{"value": user_id}]}],
    }
    patch_response = scim_client.patch(
        f"/scim/v2/Groups/{group_id}", json=patch_payload, headers=_headers(tenant_a)
    )
    assert patch_response.status_code == 200

    role_response = scim_client.get(f"/scim/internal/roles/{user_id}", headers=_headers(tenant_a))
    assert role_response.status_code == 200
    assert role_response.json()["roles"] == ["PMO_ADMIN"]

    user_response = scim_client.get(f"/scim/v2/Users/{user_id}", headers=_headers(tenant_a))
    assert user_response.status_code == 200
    extension = user_response.json().get("urn:ietf:params:scim:schemas:extension:ppm:2.0:User")
    assert extension["roles"] == ["PMO_ADMIN"]

    tenant_b_response = scim_client.post(
        "/scim/v2/Users", json=user_payload, headers=_headers(tenant_b)
    )
    assert tenant_b_response.status_code == 201
    assert tenant_b_response.json()["id"] != user_id

    list_response = scim_client.get(
        '/scim/v2/Users?filter=userName eq "alice@example.com"', headers=_headers(tenant_a)
    )
    assert list_response.status_code == 200
    assert list_response.json()["totalResults"] == 1
