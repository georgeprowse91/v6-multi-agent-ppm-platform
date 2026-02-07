import logging
from fastapi.testclient import TestClient
from integrations.connectors.planview.src.main import app


def test_planview_outbound_sync(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    def mock_send(records, tenant_id, *, include_schema):
        assert tenant_id == "test-tenant"
        assert isinstance(records, list)

    monkeypatch.setattr("integrations.connectors.planview.src.main.send_to_external_system", mock_send)

    client = TestClient(app)
    payload = {
        "records": [{"id": "abc", "name": "Planview Example"}],
        "tenant_id": "test-tenant",
        "live": True,
        "include_schema": False,
    }
    response = client.post("/connectors/planview/sync/outbound", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
