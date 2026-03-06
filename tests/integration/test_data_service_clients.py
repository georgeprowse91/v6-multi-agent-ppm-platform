from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

pytest.importorskip("aiosqlite")
pytest.importorskip("opentelemetry")

from agents.runtime.src.data_service import DataServiceClient as AgentDataServiceClient
from connectors.sdk.src.data_service_client import (
    DataServiceClient as ConnectorDataServiceClient,
)

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "data-service"
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

_data_svc_src = str(SERVICE_ROOT / "src")
# Ensure data-service/src is first so its ``storage`` module wins over
# data-lineage-service/src/storage.py which conftest may have added earlier.
if _data_svc_src in sys.path:
    sys.path.remove(_data_svc_src)
sys.path.insert(0, _data_svc_src)
# Evict previously-cached modules so the correct ones are found.
sys.modules.pop("storage", None)
# Ensure the real sqlalchemy is used, not the vendor shim.
sys.modules.pop("sqlalchemy", None)

spec = spec_from_file_location("data_service_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _database_url(tmp_path: Path) -> str:
    db_path = tmp_path / "data_service.db"
    return f"sqlite+aiosqlite:///{db_path}"


def _configure_auth(monkeypatch, tenant_id: str = "tenant-a") -> str:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    return jwt.encode(
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


def _schema_payload() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
        },
        "additionalProperties": False,
    }


def test_connector_client_schema_registry(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")
    token = _configure_auth(monkeypatch)

    with TestClient(module.app) as client:
        data_client = ConnectorDataServiceClient(
            base_url="http://test", tenant_id="tenant-a", client=client, auth_token=token
        )
        first = data_client.register_schema("demo", _schema_payload())
        second = data_client.register_schema("demo", _schema_payload())
        assert first["version"] == 1
        assert second["version"] == 2

        versions = data_client.list_schema_versions("demo")
        assert [item["version"] for item in versions] == [1, 2]

        latest = data_client.get_latest_schema("demo")
        assert latest["version"] == 2

        stored = data_client.store_entity(
            "demo",
            {"id": "entity-1", "name": "Canon"},
            entity_id="entity-1",
        )
        fetched = data_client.get_entity("demo", stored["id"])
        assert fetched["data"]["name"] == "Canon"


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_agent_client_schema_registry(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_SERVICE_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "false")
    token = _configure_auth(monkeypatch)

    await module.startup()
    try:
        async with httpx.AsyncClient(app=module.app, base_url="http://test") as http_client:
            data_client = AgentDataServiceClient(
                base_url="http://test", client=http_client, auth_token=token
            )
            registered = await data_client.register_schema(
                "agent-demo", _schema_payload(), tenant_id="tenant-a"
            )
            assert registered["version"] == 1

            schemas = await data_client.list_schemas(tenant_id="tenant-a")
            assert any(schema["name"] == "agent-demo" for schema in schemas)

            stored = await data_client.store_entity(
                "agent-demo",
                {"id": "entity-42", "name": "Atlas"},
                tenant_id="tenant-a",
            )
            fetched = await data_client.get_entity("agent-demo", stored["id"], tenant_id="tenant-a")
            assert fetched["data"]["id"] == "entity-42"
    finally:
        await module.app.state.store.engine.dispose()
