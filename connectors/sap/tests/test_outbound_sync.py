import logging
from fastapi.testclient import TestClient
from connectors.sap.src.main import app


def test_sap_outbound_sync(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    # Mock the outbound hook to prevent real logging or API calls
    def mock_send(records, tenant_id, *, include_schema):
        assert tenant_id == "test-tenant"
        assert isinstance(records, list)

    monkeypatch.setattr("connectors.sap.src.main.send_to_external_system", mock_send)

    client = TestClient(app)
    payload = {
        "records": [{"id": "123", "name": "Example"}],
        "tenant_id": "test-tenant",
        "live": True,
        "include_schema": False,
    }
    response = client.post("/connectors/sap/sync/outbound", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
