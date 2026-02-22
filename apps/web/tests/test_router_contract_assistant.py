import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes import assistant


class _StubAssistantService:
    async def send(self, payload):
        return {"echo": payload}


def test_assistant_router_contract() -> None:
    app = FastAPI()
    app.include_router(assistant.router)
    app.dependency_overrides[assistant.get_assistant_service] = lambda: _StubAssistantService()
    client = TestClient(app)

    response = client.post("/v1/api/assistant/send", json={"message": "hi"})
    assert response.status_code == 200
    assert response.json() == {"echo": {"message": "hi"}}
