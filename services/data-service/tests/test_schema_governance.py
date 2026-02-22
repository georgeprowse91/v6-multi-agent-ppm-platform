from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("aiosqlite")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_service_main_schema_governance", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _database_url(tmp_path: Path) -> str:
    db_path = tmp_path / "data_service.db"
    return f"sqlite+aiosqlite:///{db_path}"


def _auth_headers(monkeypatch, tenant_id: str = "tenant-a") -> dict[str, str]:
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)
    return {"X-Tenant-ID": tenant_id}


def test_schema_registration_rejects_incompatible_update(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    schema_v1 = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "name"],
        "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
        "additionalProperties": False,
    }
    schema_v2_breaking = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "name", "region"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "region": {"type": "string"},
        },
        "additionalProperties": False,
    }

    with TestClient(module.app) as client:
        ok = client.post(
            "/v1/schemas",
            json={"name": "governed", "schema": schema_v1},
            headers=_auth_headers(monkeypatch),
        )
        assert ok.status_code == 200

        rejected = client.post(
            "/v1/schemas",
            json={
                "name": "governed",
                "schema": schema_v2_breaking,
                "compatibility_mode": "full",
            },
            headers=_auth_headers(monkeypatch),
        )
        assert rejected.status_code == 422
        assert "Compatibility mode 'full' violated" in rejected.json()["detail"]


def test_non_dev_ingest_requires_schema_promotion(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    schema_payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "name"],
        "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
        "additionalProperties": False,
    }

    with TestClient(module.app) as client:
        created = client.post(
            "/v1/schemas",
            json={"name": "promoted", "schema": schema_payload, "compatibility_mode": "backward"},
            headers=_auth_headers(monkeypatch),
        )
        assert created.status_code == 200

        blocked = client.post(
            "/entities/promoted",
            json={"tenant_id": "tenant-a", "data": {"id": "e-1", "name": "Alpha"}},
            headers=_auth_headers(monkeypatch),
        )
        assert blocked.status_code == 409

        promoted = client.post(
            "/v1/schemas/promoted/versions/1/promote",
            json={"environment": "staging"},
            headers=_auth_headers(monkeypatch),
        )
        assert promoted.status_code == 200

        allowed = client.post(
            "/entities/promoted",
            json={"tenant_id": "tenant-a", "data": {"id": "e-1", "name": "Alpha"}},
            headers=_auth_headers(monkeypatch),
        )
        assert allowed.status_code == 200
