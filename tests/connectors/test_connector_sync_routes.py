from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules.pop("connectors", None)

os.environ.setdefault("CONNECTOR_TELEMETRY_DISABLED", "1")

CONNECTORS_ROOT = REPO_ROOT / "connectors"


def _load_router(connector_id: str):  # noqa: ANN001
    base_pkg = sys.modules.setdefault("connectors", types.ModuleType("connectors"))
    base_pkg.__path__ = [str(CONNECTORS_ROOT)]
    connector_pkg_name = f"connectors.{connector_id}"
    connector_pkg = sys.modules.setdefault(
        connector_pkg_name, types.ModuleType(connector_pkg_name)
    )
    connector_pkg.__path__ = [str(CONNECTORS_ROOT / connector_id)]
    src_pkg_name = f"{connector_pkg_name}.src"
    src_pkg = sys.modules.setdefault(src_pkg_name, types.ModuleType(src_pkg_name))
    src_pkg.__path__ = [str(CONNECTORS_ROOT / connector_id / "src")]

    router_path = CONNECTORS_ROOT / connector_id / "src" / "router.py"
    spec = importlib.util.spec_from_file_location(f"{src_pkg_name}.router", router_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to load router for {connector_id}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.router


CONNECTOR_ROUTERS = [
    ("planview", _load_router("planview")),
    ("clarity", _load_router("clarity")),
    ("sap", _load_router("sap")),
    ("workday", _load_router("workday")),
    ("salesforce", _load_router("salesforce")),
    ("slack", _load_router("slack")),
    ("teams", _load_router("teams")),
    ("servicenow", _load_router("servicenow")),
]


def _client(router) -> TestClient:  # noqa: ANN001
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize("connector_id,router", CONNECTOR_ROUTERS)
def test_inbound_sync_records(connector_id: str, router) -> None:  # noqa: ANN001
    client = _client(router)
    payload = {
        "tenant_id": "tenant-alpha",
        "records": [
            {
                "id": "proj-100",
                "name": "Alpha",
                "status": "execution",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "owner": "Dana",
            }
        ],
    }
    response = client.post(f"/connectors/{connector_id}/sync/inbound", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["tenant_id"] == "tenant-alpha"
    assert body[0]["id"] == "proj-100"
    assert body[0]["name"] == "Alpha"


@pytest.mark.parametrize("connector_id,router", CONNECTOR_ROUTERS)
def test_outbound_sync_dry_run(connector_id: str, router) -> None:  # noqa: ANN001
    client = _client(router)
    payload = {
        "tenant_id": "tenant-bravo",
        "records": [
            {
                "id": "proj-200",
                "name": "Bravo",
                "status": "planning",
                "start_date": "2024-02-01",
                "end_date": "2024-10-31",
                "owner": "Lee",
            }
        ],
    }
    response = client.post(f"/connectors/{connector_id}/sync/outbound", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    assert body["records"][0]["tenant_id"] == "tenant-bravo"
