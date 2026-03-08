from __future__ import annotations

import enum
import importlib.machinery
import sys
import types
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
API_SRC = REPO_ROOT / "services" / "api-gateway" / "src"
FEATURE_FLAGS_SRC = REPO_ROOT / "packages" / "feature-flags" / "src"
COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
SECURITY_SRC = REPO_ROOT / "packages" / "security" / "src"

for path in (REPO_ROOT, API_SRC, FEATURE_FLAGS_SRC, COMMON_SRC, SECURITY_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


if "slowapi" not in sys.modules:
    slowapi_mod = types.ModuleType("slowapi")

    class Limiter:
        def __init__(self, *args, **kwargs):
            pass

        def exempt(self, fn):
            return fn

    def _rate_limit_exceeded_handler(*_args, **_kwargs):
        return None

    slowapi_mod.Limiter = Limiter
    slowapi_mod._rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    sys.modules["slowapi"] = slowapi_mod

if "slowapi.errors" not in sys.modules:
    slowapi_errors = types.ModuleType("slowapi.errors")

    class RateLimitExceeded(Exception):  # noqa: N818
        pass

    slowapi_errors.RateLimitExceeded = RateLimitExceeded
    sys.modules["slowapi.errors"] = slowapi_errors

if "slowapi.middleware" not in sys.modules:
    slowapi_middleware = types.ModuleType("slowapi.middleware")

    class SlowAPIMiddleware:
        pass

    slowapi_middleware.SlowAPIMiddleware = SlowAPIMiddleware
    sys.modules["slowapi.middleware"] = slowapi_middleware
if "slowapi.util" not in sys.modules:
    slowapi_util = types.ModuleType("slowapi.util")

    def get_remote_address(_request=None):
        return "test-client"

    slowapi_util.get_remote_address = get_remote_address
    sys.modules["slowapi.util"] = slowapi_util


# Optional dependency shim
if "cryptography" not in sys.modules:
    cryptography = types.ModuleType("cryptography")
    hazmat = types.ModuleType("cryptography.hazmat")
    primitives = types.ModuleType("cryptography.hazmat.primitives")
    asymmetric = types.ModuleType("cryptography.hazmat.primitives.asymmetric")
    rsa = types.ModuleType("cryptography.hazmat.primitives.asymmetric.rsa")
    for module, name in [
        (cryptography, "cryptography"),
        (hazmat, "cryptography.hazmat"),
        (primitives, "cryptography.hazmat.primitives"),
        (asymmetric, "cryptography.hazmat.primitives.asymmetric"),
        (rsa, "cryptography.hazmat.primitives.asymmetric.rsa"),
    ]:
        module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None)

    class RSAPublicKey:  # pragma: no cover
        pass

    rsa.RSAPublicKey = RSAPublicKey
    asymmetric.rsa = rsa
    primitives.asymmetric = asymmetric
    hazmat.primitives = primitives
    cryptography.hazmat = hazmat
    sys.modules.update(
        {
            "cryptography": cryptography,
            "cryptography.hazmat": hazmat,
            "cryptography.hazmat.primitives": primitives,
            "cryptography.hazmat.primitives.asymmetric": asymmetric,
            "cryptography.hazmat.primitives.asymmetric.rsa": rsa,
        }
    )


# Connector SDK shims for route imports
class ConnectorCategory(enum.Enum):
    PPM = "ppm"
    COMPLIANCE = "compliance"


class SyncDirection(enum.Enum):
    INBOUND = "inbound"


class SyncFrequency(enum.Enum):
    DAILY = "daily"


class ConnectionStatus(enum.Enum):
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class ConnectorConfig:
    connector_id: str
    name: str
    category: ConnectorCategory
    instance_url: str = ""
    project_key: str = ""
    mcp_server_url: str = ""
    mcp_client_id: str = ""
    mcp_client_secret: str = ""
    mcp_scope: str = ""
    mcp_api_key: str = ""
    mcp_api_key_header: str = ""
    mcp_oauth_token: str = ""
    mcp_tool_map: dict = field(default_factory=dict)
    prefer_mcp: bool = False
    mcp_enabled: bool = True
    mcp_enabled_operations: list[str] = field(default_factory=list)
    mcp_disabled_operations: list[str] = field(default_factory=list)
    sync_direction: SyncDirection = SyncDirection.INBOUND
    sync_frequency: SyncFrequency = SyncFrequency.DAILY
    custom_fields: dict = field(default_factory=dict)
    mcp_server_id: str = ""
    protocol: str = ""
    protocol_version: str = ""
    mcp_scopes: list[str] = field(default_factory=list)
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    mcp_tools: list[str] = field(default_factory=list)
    tool_map: dict = field(default_factory=dict)
    resource_map: dict = field(default_factory=dict)
    prompt_map: dict = field(default_factory=dict)
    health_status: str = "unknown"
    enabled: bool = True
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_sync_at: datetime | None = None


class ConnectorConfigStore:
    def __init__(self, _path):
        pass


@dataclass
class ProjectConnectorConfig:
    ppm_project_id: str
    connector_id: str
    name: str
    category: ConnectorCategory
    enabled: bool = True
    sync_direction: SyncDirection = SyncDirection.INBOUND
    sync_frequency: SyncFrequency = SyncFrequency.DAILY


class ProjectConnectorConfigStore:
    def __init__(self, _path):
        pass


class ConnectorStatus(enum.Enum):
    AVAILABLE = "available"
    COMING_SOON = "coming_soon"


if "base_connector" not in sys.modules:
    base_connector_mod = types.ModuleType("base_connector")
    base_connector_mod.ConnectionStatus = ConnectionStatus
    base_connector_mod.ConnectorCategory = ConnectorCategory
    base_connector_mod.ConnectorConfig = ConnectorConfig
    base_connector_mod.ConnectorConfigStore = ConnectorConfigStore
    base_connector_mod.SyncDirection = SyncDirection
    base_connector_mod.SyncFrequency = SyncFrequency
    sys.modules["base_connector"] = base_connector_mod

if "project_connector_store" not in sys.modules:
    proj_mod = types.ModuleType("project_connector_store")
    proj_mod.ProjectConnectorConfig = ProjectConnectorConfig
    proj_mod.ProjectConnectorConfigStore = ProjectConnectorConfigStore
    sys.modules["project_connector_store"] = proj_mod

if "connector_registry" not in sys.modules:
    reg_mod = types.ModuleType("connector_registry")
    reg_mod.ConnectorStatus = ConnectorStatus
    reg_mod.get_all_connectors = lambda: []
    reg_mod.get_connector_definition = lambda _connector_id: None
    reg_mod.get_connectors_by_category = lambda _category: []
    sys.modules["connector_registry"] = reg_mod

if "connectors.mcp_client.client" not in sys.modules:
    client_mod = types.ModuleType("connectors.mcp_client.client")

    class MCPClient:
        def __init__(self, **_kwargs):
            pass

        async def list_tools(self):
            return []

    client_mod.MCPClient = MCPClient
    sys.modules["connectors.mcp_client.client"] = client_mod

if "connectors.mcp_client.errors" not in sys.modules:
    err_mod = types.ModuleType("connectors.mcp_client.errors")

    class MCPAuthenticationError(Exception):
        pass

    class MCPResponseError(Exception):
        pass

    class MCPServerError(Exception):
        pass

    class MCPTransportError(Exception):
        pass

    err_mod.MCPAuthenticationError = MCPAuthenticationError
    err_mod.MCPResponseError = MCPResponseError
    err_mod.MCPServerError = MCPServerError
    err_mod.MCPTransportError = MCPTransportError
    sys.modules["connectors.mcp_client.errors"] = err_mod

if "regulatory_compliance_connector" not in sys.modules:
    reg_connector_mod = types.ModuleType("regulatory_compliance_connector")

    class RegulatoryComplianceConnector:
        def __init__(self, _config):
            pass

    reg_connector_mod.RegulatoryComplianceConnector = RegulatoryComplianceConnector
    sys.modules["regulatory_compliance_connector"] = reg_connector_mod

# workflow and agent import shims
if "workflow_runtime" not in sys.modules:
    wr_mod = types.ModuleType("workflow_runtime")

    class WorkflowRuntime:
        pass

    wr_mod.WorkflowRuntime = WorkflowRuntime
    sys.modules["workflow_runtime"] = wr_mod

if "workflow_storage" not in sys.modules:
    ws_mod = types.ModuleType("workflow_storage")

    class WorkflowStore:
        def __init__(self, _path):
            pass

    ws_mod.WorkflowStore = WorkflowStore
    sys.modules["workflow_storage"] = ws_mod

if "workflow_definitions" not in sys.modules:
    wd_mod = types.ModuleType("workflow_definitions")
    wd_mod.load_definition = lambda *_args, **_kwargs: {}
    wd_mod.seed_definitions = lambda *_args, **_kwargs: None
    sys.modules["workflow_definitions"] = wd_mod

if "agent_client" not in sys.modules:
    ac_mod = types.ModuleType("agent_client")
    ac_mod.get_agent_client = lambda: object()
    sys.modules["agent_client"] = ac_mod

if "agents.runtime" not in sys.modules:
    ar_mod = types.ModuleType("agents.runtime")

    class AgentResponse(BaseModel):
        answer: str = "ok"

    ar_mod.AgentResponse = AgentResponse
    sys.modules["agents.runtime"] = ar_mod
