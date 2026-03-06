from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[5]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

logger = logging.getLogger(__name__)


def _parse_response(response: Any) -> dict[str, Any]:
    """Return the JSON body of a connector response, or a minimal accepted sentinel on failure."""
    try:
        return response.json()
    except Exception:
        return {"status": "accepted"}


class HrisClient(ABC):
    """
    Abstract base class for HRIS clients (e.g. Workday, SAP SuccessFactors, ADP).
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the HRIS system."""

    @abstractmethod
    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new employee record."""

    @abstractmethod
    def update_employee(self, employee_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an employee record."""

    @abstractmethod
    def list_employees(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        """List employees."""


class NoopHrisClient(HrisClient):
    """
    Fallback HRIS client used when the target system is not configured.

    Returns empty results and logs all calls. Callers should check
    environment variables to determine if a real client is available.
    """

    def __init__(self, system_name: str) -> None:
        self.system_name = system_name
        self._logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        self._logger.info("Authenticating with %s (noop)", self.system_name)

    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Noop create_employee on %s: %s", self.system_name, data)
        return {}

    def update_employee(self, employee_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Noop update_employee on %s id=%s: %s", self.system_name, employee_id, data)
        return {}

    def list_employees(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        self._logger.info("Noop list_employees on %s with filters=%s", self.system_name, filters)
        return []


# ---------------------------------------------------------------------------
# Workday HRIS Client
# ---------------------------------------------------------------------------


class WorkdayHrisClient(HrisClient):
    """
    HRIS client backed by the Workday connector.

    Authentication uses OAuth2 (WORKDAY_CLIENT_ID / WORKDAY_CLIENT_SECRET /
    WORKDAY_REFRESH_TOKEN).  The instance URL is taken from WORKDAY_API_URL.
    All reads and writes are delegated to the :class:`WorkdayConnector`.
    """

    def __init__(self, instance_url: str = "") -> None:
        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from workday_connector import WorkdayConnector

        url = instance_url or resolve_secret(os.getenv("WORKDAY_API_URL")) or ""
        config = ConnectorConfig(
            connector_id="workday",
            name="Workday",
            category=ConnectorCategory.HRIS,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = WorkdayConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"Workday authentication failed: {result.message}")
        self._authenticated = True
        logger.info("Workday HRIS client authenticated successfully")

    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get("workers", {})
        write_path = resource_cfg.get("write_path", "/ccx/api/v1/workers")
        write_method = resource_cfg.get("write_method", "POST")
        return _parse_response(self._connector._request(write_method, write_path, json=data))

    def update_employee(self, employee_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = self._connector.RESOURCE_PATHS.get("workers", {})
        write_path = resource_cfg.get("write_path", "/ccx/api/v1/workers")
        return _parse_response(self._connector._request("PATCH", f"{write_path}/{employee_id}", json=data))

    def list_employees(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read("workers", filters=filters)


# ---------------------------------------------------------------------------
# SAP SuccessFactors HRIS Client
# ---------------------------------------------------------------------------


class SuccessFactorsHrisClient(HrisClient):
    """
    HRIS client backed by the SAP SuccessFactors connector.

    Authentication uses OAuth2 (SAP_SF_CLIENT_ID / SAP_SF_PRIVATE_KEY /
    SAP_SF_API_KEY).  The instance URL is taken from SAP_SF_API_URL.
    """

    def __init__(self, instance_url: str = "") -> None:
        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from sap_successfactors_connector import SapSuccessFactorsConnector

        url = instance_url or resolve_secret(os.getenv("SAP_SF_API_URL")) or ""
        config = ConnectorConfig(
            connector_id="sap_successfactors",
            name="SAP SuccessFactors",
            category=ConnectorCategory.HRIS,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = SapSuccessFactorsConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"SAP SuccessFactors authentication failed: {result.message}")
        self._authenticated = True
        logger.info("SAP SuccessFactors HRIS client authenticated successfully")

    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = getattr(self._connector, "RESOURCE_PATHS", {}).get("employees", {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", "/odata/v2/User")
        return _parse_response(self._connector._request("POST", write_path, json=data))

    def update_employee(self, employee_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resource_cfg = getattr(self._connector, "RESOURCE_PATHS", {}).get("employees", {})
        write_path = resource_cfg.get("write_path") or resource_cfg.get("path", "/odata/v2/User")
        return _parse_response(self._connector._request("PATCH", f"{write_path}('{employee_id}')", json=data))

    def list_employees(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read("employees", filters=filters)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_hris_client(system: str, instance_url: str = "") -> HrisClient:
    """
    Factory function that returns the appropriate :class:`HrisClient` for the
    given HRIS system name.

    Supported values for *system*: ``"workday"``, ``"sap_successfactors"``.
    Falls back to :class:`NoopHrisClient` for unrecognised systems so that
    callers are never broken by a missing connector.

    Args:
        system: HRIS system identifier (case-insensitive).
        instance_url: Optional override for the system's base URL.

    Returns:
        A configured :class:`HrisClient` instance.
    """
    key = system.lower().strip()
    if key == "workday":
        return WorkdayHrisClient(instance_url=instance_url)
    if key in ("sap_successfactors", "successfactors"):
        return SuccessFactorsHrisClient(instance_url=instance_url)
    logger.warning(
        "Unknown HRIS system '%s'; falling back to NoopHrisClient. "
        "Supported systems: workday, sap_successfactors.",
        system,
    )
    return NoopHrisClient(system_name=system)
