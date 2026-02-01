"""External tool synchronization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ExternalSyncSettings:
    enable_ms_project: bool = False
    enable_jira: bool = False
    enable_azure_devops: bool = False
    enable_smartsheet: bool = False
    enable_outlook: bool = False
    enable_google_calendar: bool = False


@dataclass
class ExternalSyncRecord:
    system: str
    schedule_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExternalSyncClient:
    """In-memory external sync client for schedules and calendars."""

    def __init__(self, settings: Optional[ExternalSyncSettings] = None) -> None:
        self.settings = settings or ExternalSyncSettings()
        self._pushed: List[ExternalSyncRecord] = []
        self._pulled: List[ExternalSyncRecord] = []
        self._calendar_events: List[ExternalSyncRecord] = []

    def push_schedule(self, schedule_id: str, payload: Dict[str, Any]) -> None:
        for system in self._enabled_systems():
            self._pushed.append(ExternalSyncRecord(system=system, schedule_id=schedule_id, payload=payload))

    def pull_updates(self, schedule_id: str) -> List[ExternalSyncRecord]:
        updates = [record for record in self._pulled if record.schedule_id == schedule_id]
        return updates

    def record_pull(self, system: str, schedule_id: str, payload: Dict[str, Any]) -> None:
        self._pulled.append(ExternalSyncRecord(system=system, schedule_id=schedule_id, payload=payload))

    def sync_calendar(self, schedule_id: str, milestones: List[Dict[str, Any]]) -> None:
        for system in self._enabled_calendar_systems():
            self._calendar_events.append(
                ExternalSyncRecord(system=system, schedule_id=schedule_id, payload={"milestones": milestones})
            )

    def _enabled_systems(self) -> List[str]:
        systems = []
        if self.settings.enable_ms_project:
            systems.append("ms_project")
        if self.settings.enable_jira:
            systems.append("jira")
        if self.settings.enable_azure_devops:
            systems.append("azure_devops")
        if self.settings.enable_smartsheet:
            systems.append("smartsheet")
        return systems

    def _enabled_calendar_systems(self) -> List[str]:
        systems = []
        if self.settings.enable_outlook:
            systems.append("outlook")
        if self.settings.enable_google_calendar:
            systems.append("google_calendar")
        return systems

    @property
    def pushed(self) -> List[ExternalSyncRecord]:
        return self._pushed

    @property
    def calendar_events(self) -> List[ExternalSyncRecord]:
        return self._calendar_events


__all__ = ["ExternalSyncClient", "ExternalSyncSettings", "ExternalSyncRecord"]
