"""External tool synchronization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
import sys

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTORS_ROOT = REPO_ROOT / "connectors"
CONNECTOR_SDK_PATH = CONNECTORS_ROOT / "sdk" / "src"


def _ensure_connector_paths() -> None:
    if str(CONNECTOR_SDK_PATH) not in sys.path:
        sys.path.insert(0, str(CONNECTOR_SDK_PATH))
    for connector_dir in CONNECTORS_ROOT.iterdir():
        src_path = connector_dir / "src"
        if src_path.is_dir() and str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))


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

    def __init__(
        self,
        settings: Optional[ExternalSyncSettings] = None,
        *,
        connectors: Optional[dict[str, Any]] = None,
    ) -> None:
        self.settings = settings or ExternalSyncSettings()
        self._pushed: List[ExternalSyncRecord] = []
        self._pulled: List[ExternalSyncRecord] = []
        self._calendar_events: List[ExternalSyncRecord] = []
        self._connectors: dict[str, Any] = connectors or {}

        if self.settings.enable_smartsheet or self.settings.enable_outlook or self.settings.enable_google_calendar:
            _ensure_connector_paths()

    def _get_connector(self, connector_type: str) -> Any | None:
        if connector_type in self._connectors:
            return self._connectors[connector_type]

        try:
            from base_connector import ConnectorCategory, ConnectorConfig

            if connector_type == "smartsheet":
                from smartsheet_connector import SmartsheetConnector

                config = ConnectorConfig(
                    connector_id="smartsheet",
                    name="Smartsheet",
                    category=ConnectorCategory.PM,
                )
                self._connectors[connector_type] = SmartsheetConnector(config)
            elif connector_type == "outlook":
                from outlook_connector import OutlookConnector

                config = ConnectorConfig(
                    connector_id="outlook",
                    name="Outlook",
                    category=ConnectorCategory.COLLABORATION,
                )
                self._connectors[connector_type] = OutlookConnector(config)
            elif connector_type == "google_calendar":
                from google_calendar_connector import GoogleCalendarConnector

                config = ConnectorConfig(
                    connector_id="google_calendar",
                    name="Google Calendar",
                    category=ConnectorCategory.COLLABORATION,
                )
                self._connectors[connector_type] = GoogleCalendarConnector(config)
            else:
                return None
            return self._connectors[connector_type]
        except (ConnectionError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("Failed to initialize %s connector: %s", connector_type, exc)
            return None

    def push_schedule(self, schedule_id: str, payload: Dict[str, Any]) -> None:
        for system in self._enabled_systems():
            connector = self._get_connector(system)
            if connector and hasattr(connector, "write"):
                try:
                    connector.write("sheets", [payload])
                except (ConnectionError, RuntimeError, TimeoutError, ValueError) as exc:
                    logger.warning("Failed to push schedule to %s: %s", system, exc)
            self._pushed.append(ExternalSyncRecord(system=system, schedule_id=schedule_id, payload=payload))

    def pull_updates(self, schedule_id: str) -> List[ExternalSyncRecord]:
        updates = [record for record in self._pulled if record.schedule_id == schedule_id]
        return updates

    def record_pull(self, system: str, schedule_id: str, payload: Dict[str, Any]) -> None:
        self._pulled.append(ExternalSyncRecord(system=system, schedule_id=schedule_id, payload=payload))

    def sync_calendar(self, schedule_id: str, milestones: List[Dict[str, Any]]) -> None:
        for system in self._enabled_calendar_systems():
            connector = self._get_connector(system)
            if connector and hasattr(connector, "write"):
                for milestone in milestones:
                    event_payload = {
                        "subject": milestone.get("name") or milestone.get("title"),
                        "summary": milestone.get("name") or milestone.get("title"),
                        "start": milestone.get("date"),
                        "end": milestone.get("date"),
                        "description": milestone.get("description"),
                    }
                    try:
                        connector.write("events", [event_payload])
                    except (ConnectionError, RuntimeError, TimeoutError, ValueError) as exc:
                        logger.warning("Failed to sync calendar event to %s: %s", system, exc)
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
