from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("aiosqlite")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_service_main", MODULE_PATH)
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


def test_schema_registration_and_entity_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    schema_payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
        },
        "additionalProperties": False,
    }

    with TestClient(module.app) as client:
        response = client.post(
            "/v1/schemas",
            json={"name": "demo", "schema": schema_payload},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        first_version = response.json()["version"]
        assert first_version == 1

        response = client.post(
            "/v1/schemas",
            json={"name": "demo", "schema": schema_payload},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        second_version = response.json()["version"]
        assert second_version == 2

        response = client.get("/v1/schemas/demo/versions", headers=_auth_headers(monkeypatch))
        assert response.status_code == 200
        versions = [item["version"] for item in response.json()]
        assert versions == [1, 2]

        response = client.get("/v1/schemas/demo/latest", headers=_auth_headers(monkeypatch))
        assert response.status_code == 200
        assert response.json()["version"] == 2

        entity_payload = {"id": "entity-1", "name": "Canon"}
        response = client.post(
            "/entities/demo",
            json={"tenant_id": "tenant-a", "data": entity_payload},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        stored = response.json()
        assert stored["schema_version"] == 2

        response = client.get(f"/entities/demo/{stored['id']}", headers=_auth_headers(monkeypatch))
        assert response.status_code == 200
        fetched = response.json()
        assert fetched["data"] == entity_payload


def test_connector_ingest(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "true")

    fixture = (
        Path(__file__).resolve().parents[3]
        / "integrations"
        / "connectors"
        / "jira"
        / "tests"
        / "fixtures"
        / "projects.json"
    )

    with TestClient(module.app) as client:
        response = client.post(
            "/ingest/connector",
            json={
                "connector_name": "jira",
                "tenant_id": "tenant-a",
                "fixture_path": str(fixture),
                "live": False,
            },
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["schemas"]["project"] == 1

        response = client.get(
            "/entities/project",
            params={"tenant_id": "tenant-a", "limit": 5},
            headers=_auth_headers(monkeypatch),
        )
        assert response.status_code == 200
        entities = response.json()
        assert entities[0]["data"]["id"] == "proj-100"


def test_startup_dev_allows_default_sqlite_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DATA_SERVICE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    with TestClient(module.app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "checks" in payload
    assert "severity" in payload
    assert "observed_at" in payload


def test_readyz_degraded_when_scheduler_heartbeat_stale(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    with TestClient(module.app) as client:
        scheduler = module.get_retention_scheduler()
        assert scheduler is not None
        scheduler._last_heartbeat_at = (
            datetime.now(timezone.utc) - timedelta(hours=4)
        ).isoformat()  # noqa: SLF001
        response = client.get("/readyz")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["checks"]["retention_scheduler_heartbeat"]["status"] == "down"


def test_readyz_degraded_when_database_probe_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    with TestClient(module.app) as client:
        store = module.get_store()

        async def _fail_probe() -> None:
            raise RuntimeError("probe failure")

        monkeypatch.setattr(store, "readiness_probe_transaction", _fail_probe)
        response = client.get("/readyz/deep")
        assert response.status_code == 503
        payload = response.json()
        assert payload["checks"]["database_transaction_probe"]["status"] == "down"


def test_startup_production_rejects_default_sqlite_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DATA_SERVICE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")

    with pytest.raises(
        ValueError,
        match="DATA_SERVICE_DATABASE_URL or DATABASE_URL",
    ):
        with TestClient(module.app):
            pass
