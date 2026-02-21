from __future__ import annotations

from workspace_state_store import WorkspaceStateStore


class WorkspaceService:
    def __init__(self, workspace_store: WorkspaceStateStore) -> None:
        self._workspace_store = workspace_store

    def get_state(self, project_id: str):
        return self._workspace_store.get_or_create("demo-tenant", project_id).model_dump()
