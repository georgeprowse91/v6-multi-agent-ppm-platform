from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from timeline_models import Milestone, MilestoneCreate, MilestoneUpdate, utc_now


class TimelineStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock_path = path.with_suffix(".lock")

    def list_milestones(self, tenant_id: str, project_id: str) -> list[Milestone]:
        payload = self._load()
        milestones_raw = payload.get(tenant_id, {}).get(project_id, [])
        milestones = [Milestone.model_validate(item) for item in milestones_raw]
        return sorted(milestones, key=lambda item: (item.date, item.created_at))

    def get_milestone(
        self, tenant_id: str, project_id: str, milestone_id: str
    ) -> Milestone | None:
        payload = self._load()
        milestones_raw = payload.get(tenant_id, {}).get(project_id, [])
        for item in milestones_raw:
            if item.get("milestone_id") == milestone_id:
                return Milestone.model_validate(item)
        return None

    def create_milestone(
        self, tenant_id: str, project_id: str, payload: MilestoneCreate
    ) -> Milestone:
        milestone = Milestone.build(tenant_id, project_id, payload)
        payload_data = self._load()
        tenant_bucket = payload_data.setdefault(tenant_id, {})
        project_bucket = tenant_bucket.setdefault(project_id, [])
        project_bucket.append(milestone.model_dump(mode="json"))
        self._write(payload_data)
        return milestone

    def update_milestone(
        self,
        tenant_id: str,
        project_id: str,
        milestone_id: str,
        updates: MilestoneUpdate,
    ) -> Milestone | None:
        payload = self._load()
        tenant_bucket = payload.setdefault(tenant_id, {})
        project_bucket = tenant_bucket.setdefault(project_id, [])
        for index, item in enumerate(project_bucket):
            if item.get("milestone_id") != milestone_id:
                continue
            milestone = Milestone.model_validate(item)
            update_data = updates.model_dump(exclude_unset=True)
            if update_data:
                update_data["updated_at"] = utc_now()
                milestone = milestone.model_copy(update=update_data)
                project_bucket[index] = milestone.model_dump(mode="json")
                self._write(payload)
            return milestone
        return None

    def delete_milestone(self, tenant_id: str, project_id: str, milestone_id: str) -> bool:
        payload = self._load()
        tenant_bucket = payload.get(tenant_id, {})
        project_bucket = tenant_bucket.get(project_id, [])
        for index, item in enumerate(project_bucket):
            if item.get("milestone_id") == milestone_id:
                project_bucket.pop(index)
                self._write(payload)
                return True
        return False

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_lock():
            temp_path = self._path.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            temp_path.replace(self._path)

    def _file_lock(self) -> "FileLock":
        return FileLock(self._lock_path)


class FileLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: Any = None

    def __enter__(self) -> "FileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w", encoding="utf-8")
        self._lock()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._unlock()
        if self._handle:
            self._handle.close()
            self._handle = None

    def _lock(self) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)

    def _unlock(self) -> None:
        if not self._handle:
            return
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
