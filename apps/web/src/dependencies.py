from __future__ import annotations

from pathlib import Path

from analytics_proxy import AnalyticsServiceClient
from connector_hub_proxy import ConnectorHubClient
from data_service_proxy import DataServiceClient
from document_proxy import DocumentServiceClient
from orchestrator_proxy import OrchestratorProxyClient
from workspace_state_store import WorkspaceStateStore


DATA_SERVICE_BASE_URL = "http://localhost:8601"
ORCHESTRATOR_BASE_URL = "http://localhost:8702"
DOCUMENT_SERVICE_BASE_URL = "http://localhost:8701"
ANALYTICS_BASE_URL = "http://localhost:8703"
CONNECTOR_HUB_BASE_URL = "http://localhost:8704"
WORKSPACE_STATE_PATH = Path(__file__).resolve().parents[1] / "storage" / "workspace_state.json"


def get_data_service_client() -> DataServiceClient:
    return DataServiceClient(base_url=DATA_SERVICE_BASE_URL)


def get_orchestrator_proxy_client() -> OrchestratorProxyClient:
    return OrchestratorProxyClient(base_url=ORCHESTRATOR_BASE_URL)


def get_document_service_client() -> DocumentServiceClient:
    return DocumentServiceClient(base_url=DOCUMENT_SERVICE_BASE_URL)


def get_analytics_client() -> AnalyticsServiceClient:
    return AnalyticsServiceClient(base_url=ANALYTICS_BASE_URL)


def get_connector_hub_client() -> ConnectorHubClient:
    return ConnectorHubClient(base_url=CONNECTOR_HUB_BASE_URL)


def get_workspace_state_store() -> WorkspaceStateStore:
    return WorkspaceStateStore(WORKSPACE_STATE_PATH)
