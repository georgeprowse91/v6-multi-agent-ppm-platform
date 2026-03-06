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


class PpmClient(ABC):
    """
    Abstract base class for PPM tool clients (e.g. Planview, Clarity, MS Project Server).
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the PPM system."""

    @abstractmethod
    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new project."""

    @abstractmethod
    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a project."""

    @abstractmethod
    def list_projects(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        """List projects."""


class NoopPpmClient(PpmClient):
    """
    Fallback PPM client used when the target system is not configured.

    Returns empty results and logs all calls. Callers should check
    environment variables to determine if a real client is available.
    """

    def __init__(self, system_name: str) -> None:
        self.system_name = system_name
        self._logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        self._logger.info("Authenticating with %s (noop)", self.system_name)

    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Noop create_project on %s: %s", self.system_name, data)
        return {}

    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Noop update_project on %s id=%s: %s", self.system_name, project_id, data)
        return {}

    def list_projects(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        self._logger.info("Noop list_projects on %s with filters=%s", self.system_name, filters)
        return []


# ---------------------------------------------------------------------------
# Planview PPM Client
# ---------------------------------------------------------------------------


class PlanviewPpmClient(PpmClient):
    """
    PPM client backed by the Planview connector.

    Authentication uses OAuth2 (PLANVIEW_CLIENT_ID / PLANVIEW_CLIENT_SECRET /
    PLANVIEW_REFRESH_TOKEN).  The instance URL is taken from PLANVIEW_INSTANCE_URL.
    All reads and writes are delegated to the :class:`PlanviewConnector`.
    """

    def __init__(self, instance_url: str = "") -> None:
        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from planview_connector import PlanviewConnector

        url = instance_url or resolve_secret(os.getenv("PLANVIEW_INSTANCE_URL")) or ""
        config = ConnectorConfig(
            connector_id="planview",
            name="Planview",
            category=ConnectorCategory.PPM,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = PlanviewConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"Planview authentication failed: {result.message}")
        self._authenticated = True
        logger.info("Planview PPM client authenticated successfully")

    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        return _parse_response(self._connector._request("POST", "/odata/api/projects", json=data))

    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return _parse_response(
            self._connector._request("PATCH", f"/odata/api/projects('{project_id}')", json=data)
        )

    def list_projects(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read("projects", filters=filters)


# ---------------------------------------------------------------------------
# Clarity PPM Client
# ---------------------------------------------------------------------------


class ClarityPpmClient(PpmClient):
    """
    PPM client backed by the Clarity connector.

    Authentication uses OAuth2 (CLARITY_CLIENT_ID / CLARITY_CLIENT_SECRET /
    CLARITY_REFRESH_TOKEN).  The instance URL is taken from CLARITY_INSTANCE_URL.
    """

    def __init__(self, instance_url: str = "") -> None:
        from connector_secrets import resolve_secret
        from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
        from clarity_connector import ClarityConnector

        url = instance_url or resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or ""
        config = ConnectorConfig(
            connector_id="clarity",
            name="Clarity PPM",
            category=ConnectorCategory.PPM,
            enabled=True,
            sync_direction=SyncDirection("bidirectional"),
            sync_frequency=SyncFrequency("daily"),
            instance_url=url,
        )
        self._connector = ClarityConnector(config)
        self._authenticated = False

    def authenticate(self) -> None:
        result = self._connector.test_connection()
        from base_connector import ConnectionStatus
        if result.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"Clarity authentication failed: {result.message}")
        self._authenticated = True
        logger.info("Clarity PPM client authenticated successfully")

    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        return _parse_response(
            self._connector._request("POST", "/niku/xog/rest/v1/projects", json=data)
        )

    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return _parse_response(
            self._connector._request("PUT", f"/niku/xog/rest/v1/projects/{project_id}", json=data)
        )

    def list_projects(self, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        return self._connector.read("projects", filters=filters)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_ppm_client(system: str, instance_url: str = "") -> PpmClient:
    """
    Factory function that returns the appropriate :class:`PpmClient` for the
    given PPM system name.

    Supported values for *system*: ``"planview"``, ``"clarity"``.
    Falls back to :class:`NoopPpmClient` for unrecognised systems so that
    callers are never broken by a missing connector.

    Args:
        system: PPM system identifier (case-insensitive).
        instance_url: Optional override for the system's base URL.

    Returns:
        A configured :class:`PpmClient` instance.
    """
    key = system.lower().strip()
    if key in ("planview", "planview_enterprise"):
        return PlanviewPpmClient(instance_url=instance_url)
    if key in ("clarity", "clarity_ppm"):
        return ClarityPpmClient(instance_url=instance_url)
    logger.warning(
        "Unknown PPM system '%s'; falling back to NoopPpmClient. "
        "Supported systems: planview, clarity.",
        system,
    )
    return NoopPpmClient(system_name=system)
