from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from cryptography.fernet import Fernet  # Optional dependency for encryption
except Exception:
    Fernet = None  # type: ignore

from .base_connector import ConnectorCategory, ConnectorConfig
from .connector_registry import get_connector_definition


@dataclass
class ProjectConnectorConfig(ConnectorConfig):
    """Configuration for a connector scoped to a PPM project."""

    ppm_project_id: str = ""
    mcp_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["ppm_project_id"] = self.ppm_project_id
        data["mcp_tools"] = self.mcp_tools
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConnectorConfig":
        base = ConnectorConfig.from_dict(data)
        mcp_tools = data.get("mcp_tools")
        if not mcp_tools:
            mcp_tools = list((data.get("tool_map") or data.get("mcp_tool_map") or {}).keys())
        return cls(
            connector_id=base.connector_id,
            name=base.name,
            category=base.category,
            enabled=base.enabled,
            sync_direction=base.sync_direction,
            sync_frequency=base.sync_frequency,
            instance_url=base.instance_url,
            project_key=base.project_key,
            custom_fields=base.custom_fields,
            mcp_server_url=base.mcp_server_url,
            mcp_server_id=base.mcp_server_id,
            protocol=base.protocol,
            protocol_version=base.protocol_version,
            mcp_client_id=base.mcp_client_id,
            mcp_client_secret=base.mcp_client_secret,
            mcp_scope=base.mcp_scope,
            mcp_scopes=base.mcp_scopes,
            mcp_api_key=base.mcp_api_key,
            mcp_api_key_header=base.mcp_api_key_header,
            mcp_oauth_token=base.mcp_oauth_token,
            client_id=base.client_id,
            client_secret=base.client_secret,
            scope=base.scope,
            mcp_tool_map=base.mcp_tool_map,
            resource_map=base.resource_map,
            prompt_map=base.prompt_map,
            prefer_mcp=base.prefer_mcp,
            mcp_enabled=base.mcp_enabled,
            mcp_enabled_operations=base.mcp_enabled_operations,
            mcp_disabled_operations=base.mcp_disabled_operations,
            api_endpoint=base.api_endpoint,
            api_version=base.api_version,
            resource=base.resource,
            created_at=base.created_at,
            updated_at=base.updated_at,
            last_sync_at=base.last_sync_at,
            health_status=base.health_status,
            ppm_project_id=data.get("ppm_project_id", ""),
            mcp_tools=mcp_tools or [],
        )


class ProjectConnectorConfigStore:
    """Store connector configs per project with optional encryption."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path: Path = storage_path or Path("data/connectors/project_config.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._encryption_key = os.getenv("CONNECTOR_ENCRYPTION_KEY")
        self._fernet = (
            Fernet(self._encryption_key.encode()) if self._encryption_key and Fernet else None
        )

    def _load_all(self) -> dict[str, dict[str, dict[str, Any]]]:
        if not self.storage_path.exists():
            return {}
        content = self.storage_path.read_text()
        if self._fernet:
            content = self._fernet.decrypt(content.encode()).decode()
        return json.loads(content or "{}")

    def _save_all(self, configs: dict[str, dict[str, dict[str, Any]]]) -> None:
        content = json.dumps(configs, indent=2, default=str)
        if self._fernet:
            content = self._fernet.encrypt(content.encode()).decode()
        self.storage_path.write_text(content)

    def get(self, project_id: str, connector_id: str) -> ProjectConnectorConfig | None:
        data = self._load_all().get(project_id, {}).get(connector_id)
        return ProjectConnectorConfig.from_dict(data) if data else None

    def list_project(self, project_id: str) -> list[ProjectConnectorConfig]:
        return [
            ProjectConnectorConfig.from_dict(config)
            for config in self._load_all().get(project_id, {}).values()
        ]

    def save(self, config: ProjectConnectorConfig) -> None:
        configs = self._load_all()
        project_configs = configs.setdefault(config.ppm_project_id, {})
        config.updated_at = datetime.now(timezone.utc)
        config_data = config.to_dict()
        if config_data.get("mcp_tools") and not config_data.get("mcp_tool_map"):
            config_data["mcp_tool_map"] = {tool: tool for tool in config_data["mcp_tools"]}
        if config_data.get("mcp_tool_map") and not config_data.get("mcp_tools"):
            config_data["mcp_tools"] = list(config_data["mcp_tool_map"].keys())
        if config_data.get("tool_map") and not config_data.get("mcp_tool_map"):
            config_data["mcp_tool_map"] = dict(config_data["tool_map"])
        if not self._fernet:
            for field in (
                "mcp_client_secret",
                "mcp_api_key",
                "mcp_oauth_token",
                "client_secret",
            ):
                if config_data.get(field):
                    config_data[field] = ""
        project_configs[config.connector_id] = config_data
        configs[config.ppm_project_id] = project_configs
        self._save_all(configs)

    def delete(self, project_id: str, connector_id: str) -> bool:
        configs = self._load_all()
        project_configs = configs.get(project_id)
        if not project_configs or connector_id not in project_configs:
            return False
        del project_configs[connector_id]
        configs[project_id] = project_configs
        self._save_all(configs)
        return True

    def get_enabled_by_project(
        self, project_id: str, category: ConnectorCategory
    ) -> ProjectConnectorConfig | None:
        for config in self.list_project(project_id):
            if config.category == category and config.enabled:
                return config
        return None

    def enable_connector(self, project_id: str, connector_id: str) -> bool:
        config = self.get(project_id, connector_id)
        if not config:
            return False
        definition = get_connector_definition(connector_id)
        system = definition.system if definition else None

        for other in self.list_project(project_id):
            if other.connector_id == connector_id or not other.enabled:
                continue
            other_definition = get_connector_definition(other.connector_id)
            if system and other_definition and other_definition.system == system:
                other.enabled = False
                self.save(other)
                continue
            if other.category == config.category:
                other.enabled = False
                self.save(other)

        config.enabled = True
        self.save(config)
        return True
