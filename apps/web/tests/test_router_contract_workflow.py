import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes import workflow


class _StubWorkflowService:
    async def start_workflow(self, payload):
        return {"workflow": payload.get("workflow_id"), "status": "started"}


def test_workflow_router_contract() -> None:
    app = FastAPI()
    app.include_router(workflow.router)
    app.dependency_overrides[workflow.get_workflow_service] = lambda: _StubWorkflowService()
    client = TestClient(app)

    response = client.post("/v1/api/workflows/start", json={"workflow_id": "wf-1"})
    assert response.status_code == 200
    assert response.json() == {"workflow": "wf-1", "status": "started"}
