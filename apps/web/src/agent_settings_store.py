from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_settings_models import AgentRegistryEntry, AgentSettingsEntry, ProjectAgentSettings


class AgentSettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"tenants": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_project_settings(self, tenant_id: str, project_id: str) -> ProjectAgentSettings | None:
        data = self._read()
        tenant_payload = data.get("tenants", {}).get(tenant_id, {})
        project_payload = tenant_payload.get("projects", {}).get(project_id)
        if not project_payload:
            return None
        payload = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "defaults_version": project_payload.get("defaults_version", 1),
            "agents": project_payload.get("agents", {}),
        }
        return ProjectAgentSettings.model_validate(payload)

    def ensure_project_settings(
        self,
        tenant_id: str,
        project_id: str,
        registry: list[AgentRegistryEntry],
    ) -> ProjectAgentSettings:
        existing = self.get_project_settings(tenant_id, project_id)
        if not existing:
            return self.initialize_project_settings(tenant_id, project_id, registry)
        updated = False
        agents = dict(existing.agents)
        now = self._timestamp()
        for entry in registry:
            if entry.agent_id in agents:
                continue
            agents[entry.agent_id] = AgentSettingsEntry(
                agent_id=entry.agent_id,
                enabled=entry.default_enabled,
                config={},
                updated_at=now,
            )
            updated = True
        if updated:
            updated_settings = ProjectAgentSettings(
                tenant_id=tenant_id,
                project_id=project_id,
                defaults_version=existing.defaults_version,
                agents=agents,
            )
            self._persist_project(updated_settings)
            return updated_settings
        return existing

    def initialize_project_settings(
        self,
        tenant_id: str,
        project_id: str,
        registry: list[AgentRegistryEntry],
    ) -> ProjectAgentSettings:
        settings = ProjectAgentSettings(
            tenant_id=tenant_id,
            project_id=project_id,
            defaults_version=1,
            agents={
                entry.agent_id: AgentSettingsEntry(
                    agent_id=entry.agent_id,
                    enabled=entry.default_enabled,
                    config={},
                    updated_at=self._timestamp(),
                )
                for entry in registry
            },
        )
        self._persist_project(settings)
        return settings

    def update_agent_settings(
        self,
        tenant_id: str,
        project_id: str,
        agent_id: str,
        *,
        enabled: bool | None = None,
        config: dict[str, Any] | None = None,
    ) -> AgentSettingsEntry:
        settings = self.get_project_settings(tenant_id, project_id)
        if not settings:
            raise ValueError("Project settings not initialized")
        if agent_id not in settings.agents:
            raise KeyError("Agent not found")
        entry = settings.agents[agent_id]
        updated = AgentSettingsEntry(
            agent_id=entry.agent_id,
            enabled=entry.enabled if enabled is None else enabled,
            config=entry.config if config is None else config,
            updated_at=self._timestamp(),
        )
        settings.agents[agent_id] = updated
        self._persist_project(settings)
        return updated

    def reset_project_defaults(
        self,
        tenant_id: str,
        project_id: str,
        registry: list[AgentRegistryEntry],
    ) -> ProjectAgentSettings:
        settings = ProjectAgentSettings(
            tenant_id=tenant_id,
            project_id=project_id,
            defaults_version=1,
            agents={
                entry.agent_id: AgentSettingsEntry(
                    agent_id=entry.agent_id,
                    enabled=entry.default_enabled,
                    config={},
                    updated_at=self._timestamp(),
                )
                for entry in registry
            },
        )
        self._persist_project(settings)
        return settings

    def _persist_project(self, settings: ProjectAgentSettings) -> None:
        data = self._read()
        tenants = data.setdefault("tenants", {})
        tenant_payload = tenants.setdefault(settings.tenant_id, {})
        projects = tenant_payload.setdefault("projects", {})
        projects[settings.project_id] = {
            "defaults_version": settings.defaults_version,
            "agents": {
                agent_id: entry.model_dump()
                for agent_id, entry in settings.agents.items()
            },
        }
        self._write(data)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
