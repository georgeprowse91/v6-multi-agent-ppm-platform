from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from workspace_state import WorkspaceState, build_default_state, refresh_timestamp


class WorkspaceStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock_path = path.with_suffix(".lock")

    def get_or_create(self, tenant_id: str, project_id: str) -> WorkspaceState:
        payload = self._load()
        tenant_bucket = payload.setdefault(tenant_id, {})
        state_raw = tenant_bucket.get(project_id)
        if state_raw:
            return WorkspaceState.model_validate(state_raw)
        state = build_default_state(tenant_id, project_id)
        tenant_bucket[project_id] = state.model_dump()
        self._write(payload)
        return state

    def update_selection(
        self,
        tenant_id: str,
        project_id: str,
        updates: dict[str, Any],
    ) -> WorkspaceState:
        payload = self._load()
        tenant_bucket = payload.setdefault(tenant_id, {})
        current = tenant_bucket.get(project_id)
        state = (
            WorkspaceState.model_validate(current)
            if current
            else build_default_state(tenant_id, project_id)
        )
        state = state.model_copy(update=updates)
        state = refresh_timestamp(state)
        tenant_bucket[project_id] = state.model_dump()
        self._write(payload)
        return state

    def update_activity_completion(
        self,
        tenant_id: str,
        project_id: str,
        activity_id: str,
        completed: bool,
    ) -> WorkspaceState:
        payload = self._load()
        tenant_bucket = payload.setdefault(tenant_id, {})
        current = tenant_bucket.get(project_id)
        state = (
            WorkspaceState.model_validate(current)
            if current
            else build_default_state(tenant_id, project_id)
        )
        activity_completion = dict(state.activity_completion)
        activity_completion[activity_id] = completed
        state = state.model_copy(update={"activity_completion": activity_completion})
        state = refresh_timestamp(state)
        tenant_bucket[project_id] = state.model_dump()
        self._write(payload)
        return state

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
