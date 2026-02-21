import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import connectors


class _StubConnectorService:
    async def list_instances(self):
        return [{"id": "conn-1", "status": "healthy"}]


def test_connectors_router_contract() -> None:
    app = FastAPI()
    app.include_router(connectors.router)
    app.dependency_overrides[connectors.get_connector_service] = lambda: _StubConnectorService()
    client = TestClient(app)

    response = client.get("/v1/api/connector-gallery/instances")
    assert response.status_code == 200
    assert response.json() == [{"id": "conn-1", "status": "healthy"}]
