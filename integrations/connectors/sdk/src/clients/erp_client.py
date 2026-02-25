from __future__ import annotations

import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

# Ensure the SDK src directory is on the path so sub-modules resolve.
_SDK_SRC = Path(__file__).resolve().parents[1]
if str(_SDK_SRC) not in sys.path:
    sys.path.insert(0, str(_SDK_SRC))

logger = logging.getLogger(__name__)


def _parse_response(response: Any) -> dict[str, Any]:
    """Return the JSON body of a connector response, or a minimal accepted sentinel on failure."""
    try:
        return response.json()
    except Exception:
        return {"status": "accepted"}


class ErpClient(ABC):
    """
    Abstract base class for ERP system clients (e.g. SAP, Oracle, NetSuite).
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the ERP system."""

    @abstractmethod
    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new record in the ERP system."""

    @abstractmethod
    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing record in the ERP system."""

    @abstractmethod
    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        """List records from the ERP system."""


class NoopErpClient(ErpClient):
    """
    Placeholder ERP client that logs calls but performs no operations.
    Use this when the target ERP system is not yet configured.
    """

    def __init__(self, system_name: str) -> None:
        self.system_name = system_name

    def authenticate(self) -> None:
        logger.info("Authenticating with %s (noop)", self.system_name)

    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        logger.info("Noop create_record on %s.%s: %s", self.system_name, resource, data)
        return {}

    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        logger.info("Noop update_record on %s.%s id=%s: %s", self.system_name, resource, record_id, data)
        return {}

    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        logger.info("Noop list_records on %s.%s with filters=%s", self.system_name, resource, filters)
        return []


# ---------------------------------------------------------------------------
# SAP ERP Client
# ---------------------------------------------------------------------------


class SapErpClient(ErpClient):
    """
    ERP client backed by the SAP connector.

    Authentication uses HTTP Basic Auth (SAP_USERNAME / SAP_PASSWORD).
    The instance URL is taken from SAP_URL.  All reads and writes are
    delegated to the :class:`SapConnector` REST connector.
    """

    def __init__(self, instance_url: str = "") -> None:
        _connectors_root = Path(__file__).resolve().parents[4]
        _sap_src = _connectors_root / "sap" / "src"
        if str(_sap_src) not in sys.path:
            sys.path.insert(0, str(_sap_src))

        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from sap_connector import SapConnector

        url = instance_url or resolve_secret(os.getenv("SAP_URL")) or ""
        config = ConnectorConfig(
            connector_id="sap",
            name="SAP",
            category=ConnectorCategory.ERP,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = SapConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"SAP authentication failed: {result.message}")
        self._authenticated = True
        logger.info("SAP ERP client authenticated successfully")

    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get(resource, {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", f"/{resource}")
        write_method = resource_cfg.get("write_method", "POST")
        return _parse_response(self._connector._request(write_method, write_path, json=data))

    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get(resource, {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", f"/{resource}")
        return _parse_response(self._connector._request("PATCH", f"{write_path}('{record_id}')", json=data))

    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read(resource, filters=filters)


# ---------------------------------------------------------------------------
# Oracle ERP Client
# ---------------------------------------------------------------------------


class OracleErpClient(ErpClient):
    """
    ERP client backed by the Oracle connector.

    Authentication uses OAuth2 (ORACLE_CLIENT_ID / ORACLE_CLIENT_SECRET /
    ORACLE_REFRESH_TOKEN).  The instance URL is taken from ORACLE_INSTANCE_URL.
    """

    def __init__(self, instance_url: str = "") -> None:
        _connectors_root = Path(__file__).resolve().parents[4]
        _oracle_src = _connectors_root / "oracle" / "src"
        if str(_oracle_src) not in sys.path:
            sys.path.insert(0, str(_oracle_src))

        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from oracle_connector import OracleConnector

        url = instance_url or resolve_secret(os.getenv("ORACLE_INSTANCE_URL")) or ""
        config = ConnectorConfig(
            connector_id="oracle",
            name="Oracle",
            category=ConnectorCategory.ERP,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = OracleConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"Oracle authentication failed: {result.message}")
        self._authenticated = True
        logger.info("Oracle ERP client authenticated successfully")

    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = getattr(self._connector, "RESOURCE_PATHS", {}).get(resource, {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", f"/fscmRestApi/resources/11.13.18.05/{resource}")
        return _parse_response(self._connector._request("POST", write_path, json=data))

    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = getattr(self._connector, "RESOURCE_PATHS", {}).get(resource, {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", f"/fscmRestApi/resources/11.13.18.05/{resource}")
        return _parse_response(self._connector._request("PATCH", f"{write_path}/{record_id}", json=data))

    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read(resource, filters=filters)


# ---------------------------------------------------------------------------
# NetSuite ERP Client
# ---------------------------------------------------------------------------


class NetSuiteErpClient(ErpClient):
    """
    ERP client backed by the NetSuite connector.

    Authentication uses OAuth2 (NETSUITE_CONSUMER_KEY / NETSUITE_CONSUMER_SECRET /
    NETSUITE_REFRESH_TOKEN).  The instance URL is taken from NETSUITE_REST_URL.
    """

    def __init__(self, instance_url: str = "") -> None:
        _connectors_root = Path(__file__).resolve().parents[4]
        _netsuite_src = _connectors_root / "netsuite" / "src"
        if str(_netsuite_src) not in sys.path:
            sys.path.insert(0, str(_netsuite_src))

        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from netsuite_connector import NetSuiteConnector

        url = instance_url or resolve_secret(os.getenv("NETSUITE_REST_URL")) or ""
        config = ConnectorConfig(
            connector_id="netsuite",
            name="NetSuite",
            category=ConnectorCategory.ERP,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = NetSuiteConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"NetSuite authentication failed: {result.message}")
        self._authenticated = True
        logger.info("NetSuite ERP client authenticated successfully")

    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get(resource, {})
        path = resource_cfg.get("path", f"/services/rest/record/v1/{resource}")
        return _parse_response(self._connector._request("POST", path, json=data))

    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get(resource, {})
        path = resource_cfg.get("path", f"/services/rest/record/v1/{resource}")
        return _parse_response(self._connector._request("PATCH", f"{path}/{record_id}", json=data))

    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read(resource, filters=filters)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_erp_client(system: str, instance_url: str = "") -> ErpClient:
    """
    Factory function that returns the appropriate :class:`ErpClient` for the
    given ERP system name.

    Supported values for *system*: ``"sap"``, ``"oracle"``, ``"netsuite"``.
    Falls back to :class:`NoopErpClient` for unrecognised systems so that
    callers are never broken by a missing connector.

    Args:
        system: ERP system identifier (case-insensitive).
        instance_url: Optional override for the system's base URL.

    Returns:
        A configured :class:`ErpClient` instance.
    """
    key = system.lower().strip()
    if key == "sap":
        return SapErpClient(instance_url=instance_url)
    if key in ("oracle", "oracle_fusion", "oracle_cloud"):
        return OracleErpClient(instance_url=instance_url)
    if key in ("netsuite", "net_suite"):
        return NetSuiteErpClient(instance_url=instance_url)
    logger.warning(
        "Unknown ERP system '%s'; falling back to NoopErpClient. "
        "Supported systems: sap, oracle, netsuite.",
        system,
    )
    return NoopErpClient(system_name=system)
