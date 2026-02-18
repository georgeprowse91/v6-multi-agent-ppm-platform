import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import documents


class _StubDocumentService:
    async def list_documents(self, tenant_id: str, limit: int = 20):
        return {"items": [{"id": "doc-1", "tenant_id": tenant_id, "limit": limit}]}


def test_documents_router_contract() -> None:
    app = FastAPI()
    app.include_router(documents.router)
    app.dependency_overrides[documents.get_document_service] = lambda: _StubDocumentService()
    client = TestClient(app)

    response = client.get("/v1/api/document-canvas/documents", params={"tenant_id": "t1", "limit": 5})
    assert response.status_code == 200
    assert response.json()["items"][0]["tenant_id"] == "t1"
