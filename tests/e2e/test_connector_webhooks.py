from __future__ import annotations

import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
API_ROOT = REPO_ROOT / "apps" / "api-gateway" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402


def _client() -> TestClient:
    if "security.audit_log" not in sys.modules:
        audit_module = types.ModuleType("security.audit_log")

        def _build_event(**kwargs):
            return kwargs

        class _AuditStore:
            def record_event(self, event) -> None:  # noqa: ANN001
                return None

        def _get_audit_log_store():
            return _AuditStore()

        audit_module.build_event = _build_event
        audit_module.get_audit_log_store = _get_audit_log_store

        security_module = types.ModuleType("security")
        security_module.audit_log = audit_module
        sys.modules["security"] = security_module
        sys.modules["security.audit_log"] = audit_module

    from api.routes.integrations import connectors as connectors_route

    app = FastAPI()
    app.include_router(connectors_route.router, prefix="/v1")
    return TestClient(app)


def test_webhook_payload_persisted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_JIRA_WEBHOOK_SECRET", "secret-123")
    client = _client()

    from api.routes.integrations import connectors as connectors_route
    from api.webhook_storage import WebhookEventStore
    from base_connector import ConnectorConfigStore

    config_store = ConnectorConfigStore(tmp_path / "connectors.json")
    config_store.save(
        ConnectorConfig(
            connector_id="jira",
            name="Jira",
            category=ConnectorCategory.PM,
            enabled=True,
        )
    )
    connectors_route._config_store = config_store
    connectors_route._webhook_store = WebhookEventStore(tmp_path / "webhooks.json")

    payload = {"webhookEvent": "jira:issue_updated", "issue": {"key": "ENG-42"}}
    response = client.post(
        "/v1/connectors/jira/webhook",
        headers={"X-Webhook-Secret": "secret-123", "X-Tenant-ID": "tenant-alpha"},
        json=payload,
    )

    assert response.status_code == 200
    stored_events = connectors_route._webhook_store.list_events("jira")
    assert len(stored_events) == 1
    assert stored_events[0]["payload"] == payload


def test_webhook_rejects_invalid_secret(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_JIRA_WEBHOOK_SECRET", "secret-123")
    client = _client()

    from api.routes.integrations import connectors as connectors_route
    from api.webhook_storage import WebhookEventStore
    from base_connector import ConnectorConfigStore

    config_store = ConnectorConfigStore(tmp_path / "connectors.json")
    config_store.save(
        ConnectorConfig(
            connector_id="jira",
            name="Jira",
            category=ConnectorCategory.PM,
            enabled=True,
        )
    )
    connectors_route._config_store = config_store
    connectors_route._webhook_store = WebhookEventStore(tmp_path / "webhooks.json")

    response = client.post(
        "/v1/connectors/jira/webhook",
        headers={"X-Webhook-Secret": "wrong-secret"},
        json={"webhookEvent": "jira:issue_updated"},
    )

    assert response.status_code == 401
    stored_events = connectors_route._webhook_store.list_events("jira")
    assert stored_events == []
