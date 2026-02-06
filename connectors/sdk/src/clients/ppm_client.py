from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Iterable


class PpmClient(ABC):
    """Abstract base class for PPM tool clients (e.g. Planview, Clarity, MS Project Server)."""

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
    """Placeholder PPM client that logs calls but performs no operations."""

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
        self._logger.info(
            "Noop list_projects on %s with filters=%s",
            self.system_name,
            filters,
        )
        return []
