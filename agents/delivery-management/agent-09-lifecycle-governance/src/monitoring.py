"""Azure Monitor integration helpers for lifecycle workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MonitorRecord:
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AzureMonitorClient:
    def __init__(self, *, logger: Any | None = None, delay_threshold_s: float = 30.0) -> None:
        self.logger = logger
        self.delay_threshold_s = delay_threshold_s
        self.records: list[MonitorRecord] = []

    def workflow_started(self, context: Any, workflow_name: str) -> None:
        self.records.append(
            MonitorRecord(
                name=workflow_name,
                status="started",
                started_at=datetime.now(timezone.utc),
                metadata={"workflow_id": context.workflow_id, "project_id": context.project_id},
            )
        )
        if self.logger:
            self.logger.info(
                "Workflow started", extra={"workflow": workflow_name, "workflow_id": context.workflow_id}
            )

    def workflow_completed(
        self,
        context: Any,
        workflow_name: str,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        duration = (finished_at - started_at).total_seconds()
        record = MonitorRecord(
            name=workflow_name,
            status="completed",
            started_at=started_at,
            finished_at=finished_at,
            metadata={
                "workflow_id": context.workflow_id,
                "project_id": context.project_id,
                "duration_s": duration,
            },
        )
        self.records.append(record)
        if self.logger:
            self.logger.info(
                "Workflow completed",
                extra={"workflow": workflow_name, "workflow_id": context.workflow_id, "duration_s": duration},
            )
        if duration > self.delay_threshold_s:
            self.raise_alert(
                "workflow.delay",
                f"Workflow {workflow_name} exceeded {self.delay_threshold_s}s",
                metadata=record.metadata,
            )

    def workflow_failed(self, context: Any, workflow_name: str, exc: Exception) -> None:
        record = MonitorRecord(
            name=workflow_name,
            status="failed",
            metadata={
                "workflow_id": context.workflow_id,
                "project_id": context.project_id,
                "error": str(exc),
            },
        )
        self.records.append(record)
        if self.logger:
            self.logger.warning(
                "Workflow failed",
                extra={"workflow": workflow_name, "workflow_id": context.workflow_id, "error": str(exc)},
            )
        self.raise_alert("workflow.failure", f"Workflow {workflow_name} failed", metadata=record.metadata)

    def raise_alert(self, name: str, message: str, metadata: dict[str, Any]) -> None:
        record = MonitorRecord(name=name, status="alert", metadata={"message": message, **metadata})
        self.records.append(record)
        if self.logger:
            self.logger.error("Azure Monitor alert", extra={"alert": name, "message": message, **metadata})

    def record_metric(self, name: str, value: float, metadata: dict[str, Any]) -> None:
        record = MonitorRecord(name=name, status="metric", metadata={"value": value, **metadata})
        self.records.append(record)
        if self.logger:
            self.logger.info("Azure Monitor metric", extra={"metric": name, "value": value, **metadata})
