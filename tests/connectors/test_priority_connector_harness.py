from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi import HTTPException

from tests.connectors.connector_test_harness import (
    ConnectorHarnessCase,
    SequenceTransport,
    assert_connector_contract,
    bootstrap_connector_imports,
    build_items_payload,
)

bootstrap_connector_imports()

from asana_connector import AsanaConnector
from azure_devops_connector import AzureDevOpsConnector
from base_connector import ConnectorCategory, ConnectorConfig
from confluence_connector import ConfluenceConnector
from monday_connector import MondayConnector
from rest_connector import RestConnector
from servicenow_grc_connector import ServiceNowGrcConnector

from connectors.salesforce.src import router as salesforce_router
from connectors.salesforce.src.main import (
    SalesforceConfig,
)
from connectors.salesforce.src.main import (
    _fetch_projects as salesforce_fetch_projects,
)
from connectors.salesforce.src.main import (
    _request_with_refresh as salesforce_request_with_refresh,
)
from connectors.sdk.src.auth import OAuthToken
from connectors.sdk.src.http_client import HttpClient
from connectors.sdk.src.sync_router import OutboundSyncRequest


@dataclass
class DummyTokenManager:
    token: str = "token-a"
    refresh_calls: int = 0

    def get_access_token(self) -> str:
        return self.token

    def refresh(self) -> OAuthToken:
        self.refresh_calls += 1
        self.token = f"token-{self.refresh_calls}"
        return OAuthToken(access_token=self.token, refresh_token="refresh", expires_at=None)


PRIORITY_CONNECTOR_CASES = [
    ConnectorHarnessCase(
        connector_id="azure_devops",
        connector_class=AzureDevOpsConnector,
        category=ConnectorCategory.PM,
        env_vars={"AZURE_DEVOPS_ORG_URL": "https://api.example.com", "AZURE_DEVOPS_PAT": "token"},
        read_resource="projects",
        write_resource="work_items",
        auth_path="/_apis/projects",
        read_path="/_apis/projects",
        write_path="/_apis/wit/workitems",
        items_path="value",
    ),
    ConnectorHarnessCase(
        connector_id="asana",
        connector_class=AsanaConnector,
        category=ConnectorCategory.PM,
        env_vars={"ASANA_INSTANCE_URL": "https://api.example.com", "ASANA_ACCESS_TOKEN": "token"},
        read_resource="projects",
        write_resource="tasks",
        auth_path="/projects",
        read_path="/projects",
        write_path="/tasks",
        items_path="data",
    ),
    ConnectorHarnessCase(
        connector_id="monday",
        connector_class=MondayConnector,
        category=ConnectorCategory.PM,
        env_vars={"MONDAY_INSTANCE_URL": "https://api.example.com", "MONDAY_API_TOKEN": "token"},
        read_resource="boards",
        write_resource="items",
        auth_path="/v2/boards",
        read_path="/v2/boards",
        write_path="/v2/items",
        items_path="data.boards",
    ),
    ConnectorHarnessCase(
        connector_id="confluence",
        connector_class=ConfluenceConnector,
        category=ConnectorCategory.DOC_MGMT,
        env_vars={
            "CONFLUENCE_URL": "https://api.example.com",
            "CONFLUENCE_EMAIL": "qa@example.com",
            "CONFLUENCE_API_TOKEN": "token",
        },
        read_resource="spaces",
        write_resource="pages",
        auth_path="/wiki/rest/api/space",
        read_path="/wiki/rest/api/space",
        write_path="/wiki/rest/api/content",
        items_path="results",
    ),
    ConnectorHarnessCase(
        connector_id="servicenow",
        connector_class=ServiceNowGrcConnector,
        category=ConnectorCategory.GRC,
        env_vars={
            "SERVICENOW_URL": "https://api.example.com",
            "SERVICENOW_CLIENT_ID": "client",
            "SERVICENOW_CLIENT_SECRET": "secret",
            "SERVICENOW_REFRESH_TOKEN": "refresh",
            "SERVICENOW_TOKEN_URL": "https://id.example.com/token",
        },
        read_resource="profiles",
        write_resource="risks",
        auth_path="/api/now/table/sn_grc_profile",
        read_path="/api/now/table/sn_grc_profile",
        write_path="/api/now/table/sn_risk",
        items_path="result",
    ),
]


def _build_connector(
    case: ConnectorHarnessCase, monkeypatch: pytest.MonkeyPatch, transport: Any
) -> Any:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)
    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )
    if case.connector_id == "servicenow":
        return case.connector_class(config, transport=transport, token_manager=DummyTokenManager())
    return case.connector_class(config, transport=transport)


@pytest.mark.parametrize("case", PRIORITY_CONNECTOR_CASES)
def test_connector_contract_checklist(case: ConnectorHarnessCase) -> None:
    assert_connector_contract(case)


@pytest.mark.parametrize("case", PRIORITY_CONNECTOR_CASES)
def test_authentication_success_and_failure(
    case: ConnectorHarnessCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    ok_transport = SequenceTransport(
        {
            ("GET", case.auth_path): httpx.Response(
                200, json=build_items_payload(case.items_path, [{"id": "1"}])
            )
        }
    )
    connector = _build_connector(case, monkeypatch, ok_transport.transport)
    assert connector.authenticate() is True

    fail_transport = SequenceTransport(
        {("GET", case.auth_path): httpx.Response(401, json={"error": "unauthorized"})}
    )
    connector = _build_connector(case, monkeypatch, fail_transport.transport)
    assert connector.authenticate() is False


def test_oauth_token_refresh_behavior_for_priority_connectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = next(item for item in PRIORITY_CONNECTOR_CASES if item.connector_id == "servicenow")
    responses = {
        ("GET", case.read_path): [
            httpx.Response(401, json={"error": "expired"}),
            httpx.Response(200, json={"result": [{"sys_id": "prof-1"}]}),
        ]
    }
    seq = SequenceTransport(responses)
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)
    config = ConnectorConfig(
        connector_id="servicenow",
        name="servicenow",
        category=case.category,
        instance_url="https://api.example.com",
    )
    token_manager = DummyTokenManager()
    connector = ServiceNowGrcConnector(config, transport=seq.transport, token_manager=token_manager)

    records = connector.read("profiles")

    assert records == [{"sys_id": "prof-1"}]
    assert token_manager.refresh_calls == 1


@pytest.mark.parametrize("case", PRIORITY_CONNECTOR_CASES)
def test_fetch_transform_and_malformed_payload(
    case: ConnectorHarnessCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = [{"id": "p1", "name": "Alpha"}]
    seq = SequenceTransport(
        {
            ("GET", case.auth_path): httpx.Response(
                200, json=build_items_payload(case.items_path, [{"id": "ok"}])
            ),
            ("GET", case.read_path): httpx.Response(
                200, json=build_items_payload(case.items_path, expected)
            ),
        }
    )
    connector = _build_connector(case, monkeypatch, seq.transport)
    if case.connector_id == "asana":
        assert RestConnector.read(connector, case.read_resource) == expected
    else:
        assert connector.read(case.read_resource) == expected

    malformed = SequenceTransport(
        {
            ("GET", case.auth_path): httpx.Response(
                200, json=build_items_payload(case.items_path, [{"id": "ok"}])
            ),
            ("GET", case.read_path): httpx.Response(200, json={"unexpected": "shape"}),
        }
    )
    connector = _build_connector(case, monkeypatch, malformed.transport)
    if case.connector_id == "asana":
        assert RestConnector.read(connector, case.read_resource) == []
    else:
        assert connector.read(case.read_resource) == []


@pytest.mark.parametrize("status", [403, 429])
def test_http_error_status_handling(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    case = PRIORITY_CONNECTOR_CASES[0]
    seq = SequenceTransport(
        {("GET", case.auth_path): httpx.Response(status, json={"error": "blocked"})}
    )
    connector = _build_connector(case, monkeypatch, seq.transport)
    assert connector.authenticate() is False


def test_transient_network_failure_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    case = PRIORITY_CONNECTOR_CASES[0]
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectError("transient", request=request)
        return httpx.Response(200, json={"value": [{"id": "p1"}]})

    connector = _build_connector(case, monkeypatch, httpx.MockTransport(handler))
    assert connector.read(case.read_resource) == [{"id": "p1"}]
    assert attempts["count"] == 4


@pytest.mark.parametrize("case", PRIORITY_CONNECTOR_CASES)
def test_outbound_write_and_idempotency(
    case: ConnectorHarnessCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted_payloads: list[list[dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=build_items_payload(case.items_path, [{"id": "ok"}]))
        if request.method == "POST" and request.url.path == case.write_path:
            payload = json.loads(request.content.decode("utf-8"))
            posted_payloads.append(payload)
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"error": "not found"})

    connector = _build_connector(case, monkeypatch, httpx.MockTransport(handler))
    data = [{"id": "dup", "name": "A"}, {"id": "dup", "name": "A"}]
    if case.connector_id == "asana":
        response = RestConnector.write(connector, case.write_resource, data)
    else:
        response = connector.write(case.write_resource, data)

    assert len(posted_payloads) == 1
    assert len(posted_payloads[0]) == 1
    assert response == posted_payloads[0]


def test_salesforce_token_refresh_fetch_mapping_and_outbound_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"token_refresh": 0}

    class Token:
        def __init__(self) -> None:
            self.token = "expired"

        def get_access_token(self) -> str:
            return self.token

        def refresh(self) -> OAuthToken:
            calls["token_refresh"] += 1
            self.token = "fresh"
            return OAuthToken(access_token="fresh", refresh_token="r", expires_at=None)

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization")
        if auth == "Bearer expired":
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(
            200, json={"records": [{"Id": "001", "Name": "SF Project", "Status__c": "Active"}]}
        )

    config = SalesforceConfig(
        instance_url="https://salesforce.example.com",
        client_id="client",
        client_secret="secret",
        refresh_token="refresh",
        token_url="https://login.salesforce.com/oauth2/token",
        rate_limit_per_minute=120,
    )
    token_mgr = Token()
    client = HttpClient(
        base_url=config.instance_url,
        headers={"Accept": "application/json"},
        transport=httpx.MockTransport(handler),
    )

    response = salesforce_request_with_refresh(
        client, token_mgr, "GET", "/services/data/v57.0/sobjects/Project__c"
    )
    assert response.status_code == 200
    assert calls["token_refresh"] == 1

    records = salesforce_fetch_projects(client, token_mgr)
    assert records == [
        {
            "source": "project",
            "id": "001",
            "name": "SF Project",
            "status": "Active",
            "start_date": None,
            "end_date": None,
            "owner": None,
        }
    ]

    monkeypatch.setattr(
        salesforce_router, "map_records", lambda *_args, **_kwargs: [{"id": "1", "name": "x"}]
    )

    outbound = salesforce_router.sync_outbound(
        OutboundSyncRequest(
            tenant_id="tenant-a",
            records=[{"id": "1", "name": "x"}],
            include_schema=False,
            live=False,
        )
    )
    assert outbound["status"] == "dry_run"

    with pytest.raises(HTTPException):
        salesforce_router.sync_outbound(
            OutboundSyncRequest(
                tenant_id="tenant-a", records=[{"id": "1"}], include_schema=False, live=True
            )
        )
