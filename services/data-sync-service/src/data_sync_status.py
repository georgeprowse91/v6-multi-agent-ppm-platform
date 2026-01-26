from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


@dataclass
class SyncJobStatus:
    job_id: str
    status: str
    created_at: str
    updated_at: str
    connector: str | None
    details: dict[str, Any]


class StatusStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _load(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.path.read_text()))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def create(self, job_id: str, connector: str | None, status: str) -> SyncJobStatus:
        now = datetime.now(timezone.utc).isoformat()
        data = self._load()
        data[job_id] = {
            "job_id": job_id,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "connector": connector,
            "details": {},
        }
        self._save(data)
        return SyncJobStatus(**data[job_id])

    def update(
        self, job_id: str, status: str, details: dict[str, Any] | None = None
    ) -> SyncJobStatus:
        data = self._load()
        job = data.get(job_id)
        if not job:
            raise KeyError("Job not found")
        job["status"] = status
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        if details:
            job["details"].update(details)
        data[job_id] = job
        self._save(data)
        return SyncJobStatus(**job)

    def get(self, job_id: str) -> SyncJobStatus | None:
        data = self._load()
        job = data.get(job_id)
        if not job:
            return None
        return SyncJobStatus(**job)


def get_status_store() -> StatusStore:
    path = Path(
        os.getenv("DATA_SYNC_STATUS_PATH", "services/data-sync-service/storage/status.json")
    )
    return StatusStore(path)
