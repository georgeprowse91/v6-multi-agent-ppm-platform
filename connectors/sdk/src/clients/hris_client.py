from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable
import logging


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
    Placeholder HRIS client that logs calls but performs no operations.
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
