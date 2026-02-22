import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes import workspace


class _StubWorkspaceService:
    def get_state(self, project_id: str):
        return {"project_id": project_id, "tabs": []}


def test_workspace_router_contract() -> None:
    app = FastAPI()
    app.include_router(workspace.router)
    app.dependency_overrides[workspace.get_workspace_service] = lambda: _StubWorkspaceService()
    client = TestClient(app)

    response = client.get("/v1/api/workspace/prj-1")
    assert response.status_code == 200
    assert response.json() == {"project_id": "prj-1", "tabs": []}
