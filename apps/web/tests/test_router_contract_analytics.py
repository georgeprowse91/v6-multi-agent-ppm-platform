import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import analytics


class _StubAnalyticsService:
    async def get_report(self, report_type: str, project_id: str | None):
        return {"report_type": report_type, "project_id": project_id}


def test_analytics_router_contract() -> None:
    app = FastAPI()
    app.include_router(analytics.router)
    app.dependency_overrides[analytics.get_analytics_service] = lambda: _StubAnalyticsService()
    client = TestClient(app)

    response = client.get("/v1/api/analytics/powerbi/executive", params={"project_id": "p-1"})
    assert response.status_code == 200
    assert response.json() == {"report_type": "executive", "project_id": "p-1"}
