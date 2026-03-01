"""External tool synchronization helpers for lifecycle governance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SyncOutcome:
    system: str
    status: str
    details: dict[str, Any]


class ExternalSyncService:
    def __init__(
        self,
        *,
        planview: Any | None = None,
        clarity: Any | None = None,
        jira: Any | None = None,
        azure_devops: Any | None = None,
        logger: Any | None = None,
    ) -> None:
        self.planview = planview
        self.clarity = clarity
        self.jira = jira
        self.azure_devops = azure_devops
        self.logger = logger

    async def sync_project_state(self, project_id: str, state: dict[str, Any]) -> list[SyncOutcome]:
        payload = {"project_id": project_id, "state": state}
        return [
            self._sync_connector("planview", self.planview, payload),
            self._sync_connector("clarity", self.clarity, payload),
        ]

    async def sync_gate_decision(
        self, project_id: str, gate_name: str, decision: dict[str, Any]
    ) -> list[SyncOutcome]:
        payload = {"project_id": project_id, "gate_name": gate_name, "decision": decision}
        results = [
            self._sync_connector("planview", self.planview, payload),
            self._sync_connector("clarity", self.clarity, payload),
        ]
        results.extend(await self.update_work_items(project_id, gate_name, decision))
        return results

    async def update_work_items(
        self, project_id: str, gate_name: str, decision: dict[str, Any]
    ) -> list[SyncOutcome]:
        payload = {
            "project_id": project_id,
            "gate_name": gate_name,
            "status": decision.get("recommendation"),
            "readiness_score": decision.get("readiness_score"),
        }
        return [
            self._sync_connector("jira", self.jira, payload),
            self._sync_connector("azure_devops", self.azure_devops, payload),
        ]

    def _sync_connector(
        self, name: str, connector: Any | None, payload: dict[str, Any]
    ) -> SyncOutcome:
        if connector is None:
            return SyncOutcome(system=name, status="skipped", details={"reason": "not_configured"})
        write = getattr(connector, "write", None)
        if not callable(write):
            return SyncOutcome(
                system=name, status="skipped", details={"reason": "write_not_supported"}
            )
        try:
            response = write("lifecycle_gate", payload)
            return SyncOutcome(system=name, status="synced", details={"response": response})
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            if self.logger:
                self.logger.warning(
                    "External sync failed", extra={"system": name, "error": str(exc)}
                )
            return SyncOutcome(system=name, status="failed", details={"error": str(exc)})

    def close(self) -> None:
        for connector in (self.planview, self.clarity, self.jira, self.azure_devops):
            close = getattr(connector, "close", None)
            if callable(close):
                close()
