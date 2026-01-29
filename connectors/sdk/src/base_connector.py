"""
Base Connector Interface

Defines the abstract base class for all connectors in the PPM platform.
Connectors must implement authentication, test connection, and data operations.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None  # type: ignore  # Optional dependency for config encryption


class ConnectorCategory(str, Enum):
    """Connector categories for organization and mutual exclusivity."""

    PPM = "ppm"  # PPM Tools (Planview, Clarity, MS Project Server)
    PM = "pm"  # PM Tools (Jira, Azure DevOps, Monday.com, Asana)
    DOC_MGMT = "doc_mgmt"  # Document Management (SharePoint, Confluence, Google Drive)
    ERP = "erp"  # ERP Systems (SAP, Oracle, NetSuite)
    HRIS = "hris"  # HRIS (Workday, SAP SuccessFactors, ADP)
    COLLABORATION = "collaboration"  # Collaboration (Teams, Slack, Zoom)
    GRC = "grc"  # GRC (ServiceNow GRC, Archer, LogicGate)


class SyncDirection(str, Enum):
    """Data synchronization direction."""

    INBOUND = "inbound"  # Read from external system
    OUTBOUND = "outbound"  # Write to external system
    BIDIRECTIONAL = "bidirectional"  # Both read and write


class SyncFrequency(str, Enum):
    """Data synchronization frequency."""

    REALTIME = "realtime"  # Via webhooks
    HOURLY = "hourly"
    EVERY_4_HOURS = "every_4_hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


class ConnectionStatus(str, Enum):
    """Connection test result status."""

    CONNECTED = "connected"
    FAILED = "failed"
    UNAUTHORIZED = "unauthorized"
    TIMEOUT = "timeout"
    INVALID_CONFIG = "invalid_config"


@dataclass
class ConnectionTestResult:
    """Result of a connection test."""

    status: ConnectionStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    tested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "tested_at": self.tested_at.isoformat(),
        }


@dataclass
class ConnectorConfig:
    """Configuration for a connector instance."""

    connector_id: str
    name: str
    category: ConnectorCategory
    enabled: bool = False
    sync_direction: SyncDirection = SyncDirection.INBOUND
    sync_frequency: SyncFrequency = SyncFrequency.DAILY

    # Non-secret configuration fields (stored in JSON)
    instance_url: str = ""
    project_key: str = ""  # For project-based connectors like Jira
    custom_fields: dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_sync_at: datetime | None = None
    health_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "category": self.category.value,
            "enabled": self.enabled,
            "sync_direction": self.sync_direction.value,
            "sync_frequency": self.sync_frequency.value,
            "instance_url": self.instance_url,
            "project_key": self.project_key,
            "custom_fields": self.custom_fields,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "health_status": self.health_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectorConfig":
        return cls(
            connector_id=data["connector_id"],
            name=data["name"],
            category=ConnectorCategory(data["category"]),
            enabled=data.get("enabled", False),
            sync_direction=SyncDirection(data.get("sync_direction", "inbound")),
            sync_frequency=SyncFrequency(data.get("sync_frequency", "daily")),
            instance_url=data.get("instance_url", ""),
            project_key=data.get("project_key", ""),
            custom_fields=data.get("custom_fields", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(timezone.utc),
            last_sync_at=datetime.fromisoformat(data["last_sync_at"])
            if data.get("last_sync_at")
            else None,
            health_status=data.get("health_status", "unknown"),
        )


T = TypeVar("T", bound="BaseConnector")


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    Connectors must implement:
    - authenticate(): Validate credentials and establish connection
    - test_connection(): Test if the connection is working
    - read(): Read data from the external system
    - write(): Write data to the external system (optional for read-only connectors)
    """

    # Class-level connector metadata (override in subclasses)
    CONNECTOR_ID: str = "base"
    CONNECTOR_NAME: str = "Base Connector"
    CONNECTOR_VERSION: str = "1.0.0"
    CONNECTOR_CATEGORY: ConnectorCategory = ConnectorCategory.PM
    SUPPORTS_WRITE: bool = False  # Override to enable write operations

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the external system.

        Returns True if authentication is successful, False otherwise.
        Credentials should be obtained from environment variables.
        """
        pass

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        Test the connection to the external system.

        Returns a ConnectionTestResult with status and details.
        """
        pass

    @abstractmethod
    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Read data from the external system.

        Args:
            resource_type: Type of resource to read (e.g., 'issues', 'projects')
            filters: Optional filters to apply
            limit: Maximum number of records to return
            offset: Starting offset for pagination

        Returns:
            List of records from the external system
        """
        pass

    def write(
        self,
        resource_type: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Write data to the external system.

        Args:
            resource_type: Type of resource to write
            data: List of records to write

        Returns:
            List of created/updated records with IDs

        Raises:
            NotImplementedError if connector doesn't support write operations
        """
        if not self.SUPPORTS_WRITE:
            raise NotImplementedError(
                f"{self.CONNECTOR_NAME} does not support write operations"
            )
        return []

    def get_metadata(self) -> dict[str, Any]:
        """Get connector metadata."""
        return {
            "connector_id": self.CONNECTOR_ID,
            "name": self.CONNECTOR_NAME,
            "version": self.CONNECTOR_VERSION,
            "category": self.CONNECTOR_CATEGORY.value,
            "supports_write": self.SUPPORTS_WRITE,
            "authenticated": self._authenticated,
        }


class ConnectorConfigStore:
    """
    Secure storage for connector configurations.

    - Non-secret fields (URLs, project keys) are stored in JSON
    - Secret fields (API tokens, passwords) MUST be provided via environment variables
    - Optional encryption for the JSON config file using CONNECTOR_ENCRYPTION_KEY env var
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/connectors/config.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._encryption_key = os.getenv("CONNECTOR_ENCRYPTION_KEY")
        self._fernet: Any = None
        if self._encryption_key and Fernet is not None:
            self._fernet = Fernet(self._encryption_key.encode())

    def _encrypt(self, data: str) -> str:
        if self._fernet:
            return self._fernet.encrypt(data.encode()).decode()
        return data

    def _decrypt(self, data: str) -> str:
        if self._fernet:
            return self._fernet.decrypt(data.encode()).decode()
        return data

    def _load_all(self) -> dict[str, dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        content = self.storage_path.read_text()
        if self._fernet:
            content = self._decrypt(content)
        return json.loads(content)

    def _save_all(self, configs: dict[str, dict[str, Any]]) -> None:
        content = json.dumps(configs, indent=2, default=str)
        if self._fernet:
            content = self._encrypt(content)
        self.storage_path.write_text(content)

    def get(self, connector_id: str) -> ConnectorConfig | None:
        """Get a connector configuration by ID."""
        configs = self._load_all()
        if connector_id not in configs:
            return None
        return ConnectorConfig.from_dict(configs[connector_id])

    def list_all(self) -> list[ConnectorConfig]:
        """List all connector configurations."""
        configs = self._load_all()
        return [ConnectorConfig.from_dict(data) for data in configs.values()]

    def save(self, config: ConnectorConfig) -> None:
        """Save a connector configuration."""
        configs = self._load_all()
        config.updated_at = datetime.now(timezone.utc)
        configs[config.connector_id] = config.to_dict()
        self._save_all(configs)

    def delete(self, connector_id: str) -> bool:
        """Delete a connector configuration."""
        configs = self._load_all()
        if connector_id not in configs:
            return False
        del configs[connector_id]
        self._save_all(configs)
        return True

    def get_enabled_by_category(self, category: ConnectorCategory) -> ConnectorConfig | None:
        """
        Get the enabled connector for a category.

        Enforces mutual exclusivity - only one connector per category can be enabled.
        """
        for config in self.list_all():
            if config.category == category and config.enabled:
                return config
        return None

    def enable_connector(self, connector_id: str) -> bool:
        """
        Enable a connector, disabling any other connector in the same category.

        Returns True if successful, False if connector not found.
        """
        config = self.get(connector_id)
        if not config:
            return False

        # Disable other connectors in the same category
        for other_config in self.list_all():
            if (
                other_config.category == config.category
                and other_config.connector_id != connector_id
                and other_config.enabled
            ):
                other_config.enabled = False
                self.save(other_config)

        # Enable this connector
        config.enabled = True
        self.save(config)
        return True
