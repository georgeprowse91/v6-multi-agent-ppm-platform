from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Iterable


class ErpClient(ABC):
    """Abstract base class for ERP system clients (e.g. SAP, Oracle, NetSuite)."""

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
    """Placeholder ERP client that logs calls but performs no operations."""

    def __init__(self, system_name: str) -> None:
        self.system_name = system_name
        self._logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        self._logger.info("Authenticating with %s (noop)", self.system_name)

    def create_record(self, resource: str, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Noop create_record on %s.%s: %s", self.system_name, resource, data)
        return {}

    def update_record(self, resource: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.info(
            "Noop update_record on %s.%s id=%s: %s",
            self.system_name,
            resource,
            record_id,
            data,
        )
        return {}

    def list_records(self, resource: str, filters: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        self._logger.info(
            "Noop list_records on %s.%s with filters=%s",
            self.system_name,
            resource,
            filters,
        )
        return []
