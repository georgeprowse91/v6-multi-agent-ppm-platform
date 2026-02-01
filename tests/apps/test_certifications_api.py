import importlib.util

import pytest
from fastapi.testclient import TestClient


def _slowapi_available() -> bool:
    return importlib.util.find_spec("slowapi") is not None


@pytest.mark.skipif(not _slowapi_available(), reason="slowapi is not installed")
@pytest.mark.usefixtures("auth_headers")
def test_certification_records_flow(auth_headers, monkeypatch, tmp_path):
    monkeypatch.setenv("CERTIFICATION_STORE_PATH", str(tmp_path / "certifications.json"))
    monkeypatch.setenv("CERTIFICATION_DOCUMENT_ROOT", str(tmp_path / "certification_docs"))

    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/certifications",
        json={
            "connector_id": "jira",
            "compliance_status": "pending",
            "certification_date": "2024-10-01",
            "audit_reference": "SOC2-2024-10",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["connector_id"] == "jira"
    assert payload["compliance_status"] == "pending"

    files = {"file": ("soc2-report.pdf", b"evidence", "application/pdf")}
    response = client.post(
        "/api/v1/certifications/jira/documents",
        data={"uploaded_by": "qa-user"},
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"][0]["filename"] == "soc2-report.pdf"

    response = client.get(
        "/api/v1/certifications/jira",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"]
