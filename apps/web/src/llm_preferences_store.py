from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LLMPreferencesStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"tenant": {}, "project": {}, "user": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def get_preferences(
        self, *, tenant_id: str, project_id: str | None, user_id: str | None
    ) -> dict[str, Any]:
        payload = self._load()
        resolved: dict[str, Any] = {}
        tenant_pref = payload.get("tenant", {}).get(tenant_id)
        if isinstance(tenant_pref, dict):
            resolved.update(tenant_pref)
        if project_id:
            project_pref = payload.get("project", {}).get(f"{tenant_id}:{project_id}")
            if isinstance(project_pref, dict):
                resolved.update(project_pref)
        if user_id:
            user_pref = payload.get("user", {}).get(f"{tenant_id}:{user_id}")
            if isinstance(user_pref, dict):
                resolved.update(user_pref)
        return resolved

    def set_preference(
        self,
        *,
        scope: str,
        tenant_id: str,
        project_id: str | None,
        user_id: str | None,
        provider: str,
        model_id: str,
    ) -> dict[str, Any]:
        if scope not in {"tenant", "project", "user"}:
            raise ValueError("Invalid scope")
        payload = self._load()
        section = payload.setdefault(scope, {})
        if scope == "tenant":
            key = tenant_id
        elif scope == "project":
            if not project_id:
                raise ValueError("project_id is required for project scope")
            key = f"{tenant_id}:{project_id}"
        else:
            if not user_id:
                raise ValueError("user_id is required for user scope")
            key = f"{tenant_id}:{user_id}"
        section[key] = {"provider": provider, "model_id": model_id}
        self._write(payload)
        return section[key]
