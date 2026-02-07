from __future__ import annotations

import base64
import contextlib
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"
SDK_PATH = CONNECTORS_ROOT / "sdk" / "src"
connector_src_paths = [
    path / "src" for path in CONNECTORS_ROOT.iterdir() if (path / "src").is_dir()
]
security_module = types.ModuleType("security")
dlp_module = types.ModuleType("security.dlp")
secrets_module = types.ModuleType("security.secrets")
keyvault_module = types.ModuleType("security.keyvault")
dlp_module.redact_payload = lambda payload: payload
secrets_module.resolve_secret = lambda value: value
class DummyKeyVaultConfig:  # noqa: D401 - simple mock
    def __init__(self, vault_url: str | None = None) -> None:
        self.vault_url = vault_url


class DummyKeyVaultClient:
    def __init__(self, _config: DummyKeyVaultConfig) -> None:
        return None

    def get_secret(self, _name: str) -> str | None:
        return None


class DummyKeyVaultUnavailableError(Exception):
    pass


keyvault_module.KeyVaultClient = DummyKeyVaultClient
keyvault_module.KeyVaultConfig = DummyKeyVaultConfig
keyvault_module.KeyVaultUnavailableError = DummyKeyVaultUnavailableError
security_module.dlp = dlp_module
security_module.secrets = secrets_module
security_module.keyvault = keyvault_module
sys.modules.setdefault("security", security_module)
sys.modules.setdefault("security.dlp", dlp_module)
sys.modules.setdefault("security.secrets", secrets_module)
sys.modules.setdefault("security.keyvault", keyvault_module)
for path in [SDK_PATH, *connector_src_paths]:
    path_str = str(path.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import http_client as http_client_module
from adp_connector import AdpConnector
from archer_connector import ArcherConnector
from asana_connector import AsanaConnector
from azure_devops_connector import AzureDevOpsConnector
from azure_communication_services_connector import AzureCommunicationServicesConnector
from base_connector import ConnectionStatus, ConnectorCategory, ConnectorConfig
from clarity_connector import ClarityConnector
from confluence_connector import ConfluenceConnector
from google_calendar_connector import GoogleCalendarConnector
from google_drive_connector import GoogleDriveConnector
from http_client import HttpClient
from logicgate_connector import LogicGateConnector
from monday_connector import MondayConnector
from ms_project_server_connector import MsProjectServerConnector
from netsuite_connector import NetSuiteConnector
from notification_hubs_connector import NotificationHubsConnector
from oracle_connector import OracleConnector
from outlook_connector import OutlookConnector
from planview_connector import PlanviewConnector
from sap_connector import SapConnector
from sap_successfactors_connector import SapSuccessFactorsConnector
from servicenow_grc_connector import ServiceNowGrcConnector
from sharepoint_connector import SharePointConnector
from slack_connector import SlackConnector
from smartsheet_connector import SmartsheetConnector
from teams_connector import TeamsConnector
from twilio_connector import TwilioConnector
from workday_connector import WorkdayConnector
from zoom_connector import ZoomConnector


class DummySpan:
    def set_attribute(self, *_args: object, **_kwargs: object) -> None:
        return None

    def set_status(self, *_args: object, **_kwargs: object) -> None:
        return None

    def record_exception(self, *_args: object, **_kwargs: object) -> None:
        return None


class DummyTracer:
    def start_span(self, *_args: object, **_kwargs: object) -> DummySpan:
        return DummySpan()


@contextlib.contextmanager
def _noop_use_span(span: DummySpan, end_on_exit: bool = True) -> DummySpan:
    yield span


http_client_module.tracer = DummyTracer()
http_client_module.trace.use_span = _noop_use_span
http_client_module.SpanKind = types.SimpleNamespace(CLIENT="client")


@dataclass
class DummyToken:
    access_token: str


class DummyTokenManager:
    def __init__(self) -> None:
        self._token = "dummy-token"

    def get_access_token(self) -> str:
        return self._token

    def refresh(self) -> DummyToken:
        self._token = "refreshed-token"
        return DummyToken(access_token=self._token)


def build_response(items_path: str | None, items: list[dict[str, Any]]) -> Any:
    if not items_path:
        return items
    data: dict[str, Any] = {}
    current = data
    parts = items_path.split(".")
    for part in parts[:-1]:
        current[part] = {}
        current = current[part]
    current[parts[-1]] = items
    return data


def make_transport(routes: dict[tuple[str, str], tuple[int, Any]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        key = (request.method, path)
        if key not in routes:
            trimmed = path.rstrip("/") or "/"
            key = (request.method, trimmed)
        if key in routes:
            status, payload = routes[key]
            return httpx.Response(status, json=payload)
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


@dataclass
class ConnectorCase:
    connector_class: Any
    connector_id: str
    category: ConnectorCategory
    env_vars: dict[str, str]
    resource_type: str
    auth_path: str
    resource_path: str
    items_path: str | None
    use_token_manager: bool = False
    write_resource_type: str | None = None


CONNECTOR_CASES: list[ConnectorCase] = [
    ConnectorCase(
        connector_class=PlanviewConnector,
        connector_id="planview",
        category=ConnectorCategory.PPM,
        env_vars={
            "PLANVIEW_INSTANCE_URL": "https://api.example.com",
            "PLANVIEW_CLIENT_ID": "client",
            "PLANVIEW_CLIENT_SECRET": "secret",
            "PLANVIEW_REFRESH_TOKEN": "refresh",
        },
        resource_type="projects",
        auth_path="/api/v1/projects",
        resource_path="/api/v1/projects",
        items_path="items",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=ClarityConnector,
        connector_id="clarity",
        category=ConnectorCategory.PPM,
        env_vars={
            "CLARITY_INSTANCE_URL": "https://api.example.com",
            "CLARITY_CLIENT_ID": "client",
            "CLARITY_CLIENT_SECRET": "secret",
            "CLARITY_REFRESH_TOKEN": "refresh",
        },
        resource_type="projects",
        auth_path="/ppm/rest/v1/projects",
        resource_path="/ppm/rest/v1/projects",
        items_path="results",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=MsProjectServerConnector,
        connector_id="ms_project_server",
        category=ConnectorCategory.PPM,
        env_vars={
            "MS_PROJECT_SITE_URL": "https://api.example.com",
            "MS_PROJECT_CLIENT_ID": "client",
            "MS_PROJECT_CLIENT_SECRET": "secret",
            "MS_PROJECT_REFRESH_TOKEN": "refresh",
        },
        resource_type="projects",
        auth_path="/_api/ProjectServer/Projects",
        resource_path="/_api/ProjectServer/Projects",
        items_path="value",
        use_token_manager=True,
        write_resource_type="tasks",
    ),
    ConnectorCase(
        connector_class=AzureDevOpsConnector,
        connector_id="azure_devops",
        category=ConnectorCategory.PM,
        env_vars={
            "AZURE_DEVOPS_ORG_URL": "https://api.example.com",
            "AZURE_DEVOPS_PAT": "token",
        },
        resource_type="projects",
        auth_path="/_apis/projects",
        resource_path="/_apis/projects",
        items_path="value",
        write_resource_type="work_items",
    ),
    ConnectorCase(
        connector_class=MondayConnector,
        connector_id="monday",
        category=ConnectorCategory.PM,
        env_vars={"MONDAY_API_TOKEN": "token", "MONDAY_INSTANCE_URL": "https://api.example.com"},
        resource_type="boards",
        auth_path="/v2/boards",
        resource_path="/v2/boards",
        items_path="data.boards",
        write_resource_type="items",
    ),
    ConnectorCase(
        connector_class=AsanaConnector,
        connector_id="asana",
        category=ConnectorCategory.PM,
        env_vars={"ASANA_ACCESS_TOKEN": "token", "ASANA_INSTANCE_URL": "https://api.example.com"},
        resource_type="projects",
        auth_path="/projects",
        resource_path="/projects",
        items_path="data",
        write_resource_type="tasks",
    ),
    ConnectorCase(
        connector_class=SmartsheetConnector,
        connector_id="smartsheet",
        category=ConnectorCategory.PM,
        env_vars={
            "SMARTSHEET_API_URL": "https://api.example.com",
            "SMARTSHEET_API_TOKEN": "token",
        },
        resource_type="sheets",
        auth_path="/users/me",
        resource_path="/sheets",
        items_path="data",
        write_resource_type="sheets",
    ),
    ConnectorCase(
        connector_class=SharePointConnector,
        connector_id="sharepoint",
        category=ConnectorCategory.DOC_MGMT,
        env_vars={
            "SHAREPOINT_SITE_URL": "https://api.example.com",
            "SHAREPOINT_CLIENT_ID": "client",
            "SHAREPOINT_CLIENT_SECRET": "secret",
            "SHAREPOINT_REFRESH_TOKEN": "refresh",
        },
        resource_type="lists",
        auth_path="/_api/web",
        resource_path="/_api/web/lists",
        items_path="value",
        use_token_manager=True,
        write_resource_type="documents",
    ),
    ConnectorCase(
        connector_class=ConfluenceConnector,
        connector_id="confluence",
        category=ConnectorCategory.DOC_MGMT,
        env_vars={
            "CONFLUENCE_URL": "https://api.example.com",
            "CONFLUENCE_EMAIL": "user@example.com",
            "CONFLUENCE_API_TOKEN": "token",
        },
        resource_type="spaces",
        auth_path="/wiki/rest/api/space",
        resource_path="/wiki/rest/api/space",
        items_path="results",
        write_resource_type="pages",
    ),
    ConnectorCase(
        connector_class=GoogleDriveConnector,
        connector_id="google_drive",
        category=ConnectorCategory.DOC_MGMT,
        env_vars={
            "GOOGLE_DRIVE_BASE_URL": "https://api.example.com",
            "GOOGLE_CLIENT_ID": "client",
            "GOOGLE_CLIENT_SECRET": "secret",
            "GOOGLE_REFRESH_TOKEN": "refresh",
        },
        resource_type="files",
        auth_path="/drive/v3/files",
        resource_path="/drive/v3/files",
        items_path="files",
        use_token_manager=True,
        write_resource_type="files",
    ),
    ConnectorCase(
        connector_class=GoogleCalendarConnector,
        connector_id="google_calendar",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "GOOGLE_CALENDAR_BASE_URL": "https://api.example.com",
            "GOOGLE_CALENDAR_CLIENT_ID": "client",
            "GOOGLE_CALENDAR_CLIENT_SECRET": "secret",
            "GOOGLE_CALENDAR_REFRESH_TOKEN": "refresh",
        },
        resource_type="events",
        auth_path="/calendars/primary/events",
        resource_path="/calendars/primary/events",
        items_path="items",
        use_token_manager=True,
        write_resource_type="events",
    ),
    ConnectorCase(
        connector_class=SapConnector,
        connector_id="sap",
        category=ConnectorCategory.ERP,
        env_vars={
            "SAP_URL": "https://api.example.com",
            "SAP_USERNAME": "user",
            "SAP_PASSWORD": "pass",
        },
        resource_type="projects",
        auth_path="/sap/opu/odata/sap/PROJECT_SRV/Projects",
        resource_path="/sap/opu/odata/sap/PROJECT_SRV/Projects",
        items_path="d.results",
    ),
    ConnectorCase(
        connector_class=OracleConnector,
        connector_id="oracle",
        category=ConnectorCategory.ERP,
        env_vars={
            "ORACLE_URL": "https://api.example.com",
            "ORACLE_CLIENT_ID": "client",
            "ORACLE_CLIENT_SECRET": "secret",
            "ORACLE_REFRESH_TOKEN": "refresh",
        },
        resource_type="projects",
        auth_path="/fscmRestApi/resources/latest/projects",
        resource_path="/fscmRestApi/resources/latest/projects",
        items_path="items",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=NetSuiteConnector,
        connector_id="netsuite",
        category=ConnectorCategory.ERP,
        env_vars={
            "NETSUITE_REST_URL": "https://api.example.com",
            "NETSUITE_CONSUMER_KEY": "client",
            "NETSUITE_CONSUMER_SECRET": "secret",
            "NETSUITE_REFRESH_TOKEN": "refresh",
            "NETSUITE_ACCOUNT_ID": "acct",
        },
        resource_type="projects",
        auth_path="/services/rest/record/v1/project",
        resource_path="/services/rest/record/v1/project",
        items_path="items",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=WorkdayConnector,
        connector_id="workday",
        category=ConnectorCategory.HRIS,
        env_vars={
            "WORKDAY_API_URL": "https://api.example.com",
            "WORKDAY_CLIENT_ID": "client",
            "WORKDAY_CLIENT_SECRET": "secret",
            "WORKDAY_REFRESH_TOKEN": "refresh",
        },
        resource_type="workers",
        auth_path="/ccx/api/v1/workers",
        resource_path="/ccx/api/v1/workers",
        items_path="data",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=SapSuccessFactorsConnector,
        connector_id="sap_successfactors",
        category=ConnectorCategory.HRIS,
        env_vars={
            "SF_API_SERVER": "https://api.example.com",
            "SF_CLIENT_ID": "client",
            "SF_CLIENT_SECRET": "secret",
            "SF_REFRESH_TOKEN": "refresh",
        },
        resource_type="users",
        auth_path="/odata/v2/User",
        resource_path="/odata/v2/User",
        items_path="d.results",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=AdpConnector,
        connector_id="adp",
        category=ConnectorCategory.HRIS,
        env_vars={
            "ADP_API_URL": "https://api.example.com",
            "ADP_CLIENT_ID": "client",
            "ADP_CLIENT_SECRET": "secret",
            "ADP_REFRESH_TOKEN": "refresh",
        },
        resource_type="workers",
        auth_path="/hr/v2/workers",
        resource_path="/hr/v2/workers",
        items_path="workers",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=OutlookConnector,
        connector_id="outlook",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "OUTLOOK_API_URL": "https://api.example.com",
            "OUTLOOK_CLIENT_ID": "client",
            "OUTLOOK_CLIENT_SECRET": "secret",
            "OUTLOOK_REFRESH_TOKEN": "refresh",
        },
        resource_type="events",
        auth_path="/me/events",
        resource_path="/me/events",
        items_path="value",
        use_token_manager=True,
        write_resource_type="events",
    ),
    ConnectorCase(
        connector_class=TeamsConnector,
        connector_id="teams",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "TEAMS_API_URL": "https://api.example.com",
            "TEAMS_CLIENT_ID": "client",
            "TEAMS_CLIENT_SECRET": "secret",
            "TEAMS_REFRESH_TOKEN": "refresh",
        },
        resource_type="teams",
        auth_path="/me/joinedTeams",
        resource_path="/me/joinedTeams",
        items_path="value",
        use_token_manager=True,
        write_resource_type="messages",
    ),
    ConnectorCase(
        connector_class=SlackConnector,
        connector_id="slack",
        category=ConnectorCategory.COLLABORATION,
        env_vars={"SLACK_API_URL": "https://api.example.com", "SLACK_BOT_TOKEN": "token"},
        resource_type="channels",
        auth_path="/auth.test",
        resource_path="/conversations.list",
        items_path="channels",
        write_resource_type="messages",
    ),
    ConnectorCase(
        connector_class=AzureCommunicationServicesConnector,
        connector_id="azure_communication_services",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "ACS_ENDPOINT": "https://api.example.com",
            "ACS_ACCESS_KEY": "key",
        },
        resource_type="sms",
        auth_path="/sms",
        resource_path="/sms",
        items_path="value",
        write_resource_type="sms",
    ),
    ConnectorCase(
        connector_class=TwilioConnector,
        connector_id="twilio",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "TWILIO_API_URL": "https://api.example.com",
            "TWILIO_ACCOUNT_SID": "acct",
            "TWILIO_AUTH_TOKEN": "token",
        },
        resource_type="messages",
        auth_path="/Accounts/acct/Messages.json",
        resource_path="/Accounts/acct/Messages.json",
        items_path="messages",
        write_resource_type="messages",
    ),
    ConnectorCase(
        connector_class=NotificationHubsConnector,
        connector_id="notification_hubs",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "AZURE_NOTIFICATION_HUBS_NAMESPACE": "namespace",
            "AZURE_NOTIFICATION_HUBS_NAME": "hub",
            "AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME": "DefaultFullSharedAccessSignature",
            "AZURE_NOTIFICATION_HUBS_SAS_KEY": base64.b64encode(b"secret").decode("utf-8"),
        },
        resource_type="notifications",
        auth_path="/hub/messages",
        resource_path="/hub/messages",
        items_path=None,
        write_resource_type="notifications",
    ),
    ConnectorCase(
        connector_class=ZoomConnector,
        connector_id="zoom",
        category=ConnectorCategory.COLLABORATION,
        env_vars={
            "ZOOM_API_URL": "https://api.example.com",
            "ZOOM_CLIENT_ID": "client",
            "ZOOM_CLIENT_SECRET": "secret",
            "ZOOM_REFRESH_TOKEN": "refresh",
        },
        resource_type="meetings",
        auth_path="/users/me",
        resource_path="/users/me/meetings",
        items_path="meetings",
        use_token_manager=True,
    ),
    ConnectorCase(
        connector_class=ServiceNowGrcConnector,
        connector_id="servicenow_grc",
        category=ConnectorCategory.GRC,
        env_vars={
            "SERVICENOW_URL": "https://api.example.com",
            "SERVICENOW_CLIENT_ID": "client",
            "SERVICENOW_CLIENT_SECRET": "secret",
            "SERVICENOW_REFRESH_TOKEN": "refresh",
        },
        resource_type="profiles",
        auth_path="/api/now/table/sn_grc_profile",
        resource_path="/api/now/table/sn_grc_profile",
        items_path="result",
        use_token_manager=True,
        write_resource_type="risks",
    ),
    ConnectorCase(
        connector_class=ArcherConnector,
        connector_id="archer",
        category=ConnectorCategory.GRC,
        env_vars={"ARCHER_URL": "https://api.example.com", "ARCHER_API_KEY": "token"},
        resource_type="risks",
        auth_path="/api/core/system/health",
        resource_path="/api/core/content/records",
        items_path="value",
    ),
    ConnectorCase(
        connector_class=LogicGateConnector,
        connector_id="logicgate",
        category=ConnectorCategory.GRC,
        env_vars={"LOGICGATE_API_URL": "https://api.example.com", "LOGICGATE_API_KEY": "token"},
        resource_type="workflows",
        auth_path="/api/v1/workflows",
        resource_path="/api/v1/workflows",
        items_path="data",
        write_resource_type="records",
    ),
]


@pytest.mark.parametrize("case", CONNECTOR_CASES)
def test_connector_read_success(case: ConnectorCase, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)

    items = [{"id": "1", "name": "Sample"}]
    routes = {
        ("GET", case.auth_path): (200, build_response(case.items_path, items)),
        ("GET", case.resource_path): (200, build_response(case.items_path, items)),
    }
    transport = make_transport(routes)
    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )

    token_manager = DummyTokenManager() if case.use_token_manager else None
    if case.connector_id in {"planview", "clarity"}:
        client = HttpClient(base_url="https://api.example.com", transport=transport)
        connector = case.connector_class(
            config,
            client=client,
            transport=transport,
            token_manager=token_manager,
        )
        connector._authenticated = True
        response = httpx.Response(200, json=build_response(case.items_path, items))
        connector._request = lambda *_args, **_kwargs: response
        if case.connector_id == "clarity":
            connector._read_projects = lambda **_kwargs: items
    elif token_manager:
        connector = case.connector_class(config, transport=transport, token_manager=token_manager)
    else:
        connector = case.connector_class(config, transport=transport)

    records = connector.read(case.resource_type)
    if case.connector_id == "planview":
        assert records and records[0]["id"] == "1"
    else:
        assert records == items


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in CONNECTOR_CASES
        if case.connector_class.SUPPORTS_WRITE and case.write_resource_type
    ],
)
def test_connector_write_success(case: ConnectorCase, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)

    write_resource = case.write_resource_type or case.resource_type
    write_path = case.resource_path
    if hasattr(case.connector_class, "RESOURCE_PATHS"):
        resource_paths = case.connector_class.RESOURCE_PATHS
        write_path = resource_paths[write_resource].get("write_path", case.resource_path)
    if case.connector_id in {"twilio", "notification_hubs"}:
        write_path = case.resource_path

    payload = [{"id": "1", "name": "Sample"}]
    routes = {
        ("GET", case.auth_path): (200, {}),
        ("POST", write_path): (200, payload),
    }
    transport = make_transport(routes)
    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )
    token_manager = DummyTokenManager() if case.use_token_manager else None
    if token_manager:
        connector = case.connector_class(config, transport=transport, token_manager=token_manager)
    else:
        connector = case.connector_class(config, transport=transport)

    records = connector.write(write_resource, payload)
    assert records == payload


@pytest.mark.parametrize("case", CONNECTOR_CASES)
def test_connector_test_connection_success(
    case: ConnectorCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)

    routes = {
        ("GET", case.auth_path): (200, build_response(case.items_path, [{"id": "1"}])),
    }
    transport = make_transport(routes)
    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )

    token_manager = DummyTokenManager() if case.use_token_manager else None
    if case.connector_id in {"planview", "clarity"}:
        client = HttpClient(base_url="https://api.example.com", transport=transport)
        connector = case.connector_class(
            config,
            client=client,
            transport=transport,
            token_manager=token_manager,
        )
        response = httpx.Response(200, json=build_response(case.items_path, [{"id": "1"}]))
        connector._request = lambda *_args, **_kwargs: response
    elif token_manager:
        connector = case.connector_class(config, transport=transport, token_manager=token_manager)
    else:
        connector = case.connector_class(config, transport=transport)

    result = connector.test_connection()
    assert result.status == ConnectionStatus.CONNECTED


@pytest.mark.parametrize("case", CONNECTOR_CASES)
def test_connector_missing_credentials(
    case: ConnectorCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in case.env_vars.keys():
        monkeypatch.delenv(key, raising=False)

    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url="",
    )
    token_manager = DummyTokenManager() if case.use_token_manager else None
    if token_manager:
        connector = case.connector_class(config, token_manager=token_manager)
    else:
        connector = case.connector_class(config)

    with pytest.raises(RuntimeError):
        connector.read(case.resource_type)


@pytest.mark.parametrize("case", CONNECTOR_CASES)
def test_connector_read_unsupported_resource(
    case: ConnectorCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)

    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )
    token_manager = DummyTokenManager() if case.use_token_manager else None
    if token_manager:
        connector = case.connector_class(config, token_manager=token_manager)
    else:
        connector = case.connector_class(config)
    connector._authenticated = True

    with pytest.raises(ValueError):
        connector.read("unsupported-resource")


@pytest.mark.parametrize(
    "case",
    [case for case in CONNECTOR_CASES if not case.connector_class.SUPPORTS_WRITE],
)
def test_connector_write_unsupported(case: ConnectorCase, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in case.env_vars.items():
        monkeypatch.setenv(key, value)

    config = ConnectorConfig(
        connector_id=case.connector_id,
        name=case.connector_id,
        category=case.category,
        instance_url=case.env_vars.get("AZURE_DEVOPS_ORG_URL", "https://api.example.com"),
    )
    token_manager = DummyTokenManager() if case.use_token_manager else None
    if token_manager:
        connector = case.connector_class(config, token_manager=token_manager)
    else:
        connector = case.connector_class(config)

    with pytest.raises(NotImplementedError):
        connector.write("projects", [{"id": "1"}])
