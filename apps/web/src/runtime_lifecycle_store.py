from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class RuntimeLifecycleStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"artifacts": {}, "approvals": {}}
        with self._path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload.setdefault("artifacts", {})
        payload.setdefault("approvals", {})
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def upsert_artifact(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        artifact_id: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._load()
        tenant_bucket = payload["artifacts"].setdefault(tenant_id, {})
        workspace_bucket = tenant_bucket.setdefault(workspace_id, {})
        existing = workspace_bucket.get(artifact_id, {})
        merged = {
            **existing,
            **artifact,
            "artifact_id": artifact_id,
            "updated_at": _now(),
            "version": int(existing.get("version", 0)) + 1,
        }
        workspace_bucket[artifact_id] = merged
        self._write(payload)
        return merged

    def list_approvals(self, *, tenant_id: str, workspace_id: str, status: str = "pending") -> list[dict[str, Any]]:
        payload = self._load()
        tenant_bucket = payload["approvals"].get(tenant_id, {})
        items = list(tenant_bucket.get(workspace_id, {}).values())
        if status:
            items = [item for item in items if item.get("status") == status]
        return sorted(items, key=lambda item: item.get("requested_at", ""), reverse=True)

    def create_approval(self, *, tenant_id: str, workspace_id: str, approval: dict[str, Any]) -> dict[str, Any]:
        payload = self._load()
        tenant_bucket = payload["approvals"].setdefault(tenant_id, {})
        workspace_bucket = tenant_bucket.setdefault(workspace_id, {})
        workspace_bucket[approval["approval_id"]] = approval
        self._write(payload)
        return approval

    def get_approval(self, *, tenant_id: str, workspace_id: str, approval_id: str) -> dict[str, Any] | None:
        payload = self._load()
        return payload["approvals"].get(tenant_id, {}).get(workspace_id, {}).get(approval_id)

    def decide_approval(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        approval_id: str,
        decision: str,
        actor: str,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        payload = self._load()
        workspace_bucket = payload["approvals"].get(tenant_id, {}).get(workspace_id, {})
        approval = workspace_bucket.get(approval_id)
        if not approval:
            return None
        approval["status"] = "approved" if decision == "approve" else "rejected" if decision == "reject" else "needs_changes"
        approval["decision"] = decision
        approval["decision_notes"] = notes
        approval["decided_by"] = actor
        approval["decided_at"] = _now()
        approval.setdefault("history", []).append(
            {"action": decision, "actor": actor, "notes": notes, "timestamp": approval["decided_at"]}
        )
        self._write(payload)
        return approval
