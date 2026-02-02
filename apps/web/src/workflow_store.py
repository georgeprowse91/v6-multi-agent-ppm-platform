from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_models import (
    WorkflowDefinitionPayload,
    WorkflowDefinitionRecord,
    WorkflowDefinitionSummary,
)


class WorkflowDefinitionStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def list_definitions(self) -> list[WorkflowDefinitionRecord]:
        payload = self._load()
        workflows = payload.get("workflows", {})
        records = [
            WorkflowDefinitionRecord.model_validate(record)
            for record in workflows.values()
        ]
        return sorted(records, key=lambda record: record.name.lower())

    def list_summaries(self) -> list[WorkflowDefinitionSummary]:
        records = self.list_definitions()
        return [
            WorkflowDefinitionSummary(
                workflow_id=record.workflow_id,
                name=record.name,
                description=record.description,
                updated_at=record.updated_at,
            )
            for record in records
        ]

    def get(self, workflow_id: str) -> WorkflowDefinitionRecord | None:
        payload = self._load()
        record = payload.get("workflows", {}).get(workflow_id)
        if not record:
            return None
        return WorkflowDefinitionRecord.model_validate(record)

    def upsert(self, payload: WorkflowDefinitionPayload) -> WorkflowDefinitionRecord:
        store = self._load()
        workflows = store.setdefault("workflows", {})
        now = datetime.now(timezone.utc).isoformat()
        existing = workflows.get(payload.workflow_id, {})
        record = WorkflowDefinitionRecord(
            **payload.model_dump(mode="json"),
            created_at=existing.get("created_at", now),
            updated_at=now,
        )
        workflows[payload.workflow_id] = record.model_dump(mode="json")
        self._write(store)
        return record

    def delete(self, workflow_id: str) -> None:
        store = self._load()
        workflows = store.setdefault("workflows", {})
        workflows.pop(workflow_id, None)
        self._write(store)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"workflows": {}}
        return json.loads(self._path.read_text())

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))
