from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from conflict_store import get_conflict_store
from jira_client import JiraIssue, get_jira_client
from lineage_client import get_lineage_client
from sync_log_store import get_sync_log_store
from task_store import TaskRecord, get_task_store


@dataclass
class SyncResult:
    status: str
    latency_ms: int
    errors: list[str]
    last_sync_at: str
    details: dict[str, Any]


class JiraTasksSyncJob:
    def __init__(self, strategy: str = "source_of_truth") -> None:
        self.strategy = strategy
        self.task_store = get_task_store()
        self.conflict_store = get_conflict_store()
        self.log_store = get_sync_log_store()
        self.jira_client = get_jira_client()

    def _parse_ts(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)

    def _map_issue(self, issue: JiraIssue) -> dict[str, Any]:
        return {
            "title": issue.summary,
            "status": issue.status,
            "external_id": issue.issue_id,
            "updated_at": issue.updated_at,
            "source": "jira",
            "details": {"jira_key": issue.key},
        }

    def _resolve_conflict(
        self,
        *,
        strategy: str,
        internal: TaskRecord,
        external: JiraIssue,
    ) -> tuple[str, dict[str, Any] | None]:
        internal_updated = self._parse_ts(internal.updated_at)
        external_updated = self._parse_ts(external.updated_at)
        if strategy == "manual_required":
            self.conflict_store.record(
                connector="jira",
                entity="tasks",
                task_id=internal.task_id,
                external_id=external.issue_id,
                strategy=strategy,
                reason="manual_resolution_required",
                internal_updated_at=internal.updated_at,
                external_updated_at=external.updated_at,
                details={"jira_key": external.key},
            )
            return "conflict", None
        if strategy == "last_write_wins":
            if external_updated >= internal_updated:
                return "external", self._map_issue(external)
            return "internal", None
        if strategy == "source_of_truth":
            return "external", self._map_issue(external)
        return "external", self._map_issue(external)

    def run(self, dry_run: bool = False) -> SyncResult:
        start = datetime.now(timezone.utc)
        errors: list[str] = []
        created = 0
        updated = 0
        conflicts = 0
        skipped = 0
        write_back: list[dict[str, Any]] = []
        lineage_client = get_lineage_client()
        project_key = None
        try:
            issues = self.jira_client.fetch_issues(project_key=project_key)
            for issue in issues:
                task_id = f"jira-{issue.issue_id}"
                internal = self.task_store.get(task_id)
                if internal:
                    resolution, payload = self._resolve_conflict(
                        strategy=self.strategy,
                        internal=internal,
                        external=issue,
                    )
                    if resolution == "conflict":
                        conflicts += 1
                        continue
                    if resolution == "internal":
                        write_back.append(
                            {
                                "task_id": internal.task_id,
                                "external_id": issue.issue_id,
                                "status": internal.status,
                                "title": internal.title,
                                "updated_at": internal.updated_at,
                            }
                        )
                        skipped += 1
                        continue
                    if payload and not dry_run:
                        self.task_store.upsert(task_id, payload)
                        updated += 1
                        self._emit_lineage_event(lineage_client, issue, task_id, payload)
                    else:
                        skipped += 1
                else:
                    payload = self._map_issue(issue)
                    if not dry_run:
                        self.task_store.upsert(task_id, payload)
                        created += 1
                        self._emit_lineage_event(lineage_client, issue, task_id, payload)
                    else:
                        skipped += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        end = datetime.now(timezone.utc)
        latency_ms = int((end - start).total_seconds() * 1000)
        status = "success" if not errors else "error"
        last_sync_at = end.isoformat()
        details = {
            "created": created,
            "updated": updated,
            "conflicts": conflicts,
            "skipped": skipped,
            "write_back_candidates": write_back,
            "dry_run": dry_run,
            "strategy": self.strategy,
        }
        self.log_store.create(
            connector="jira",
            entity="tasks",
            status=status,
            latency_ms=latency_ms,
            errors=errors,
            last_sync_at=last_sync_at,
            details=details,
        )
        return SyncResult(
            status=status,
            latency_ms=latency_ms,
            errors=errors,
            last_sync_at=last_sync_at,
            details=details,
        )

    def write_back(self, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        return {"status": "not_implemented", "count": len(payloads)}

    def _emit_lineage_event(
        self,
        lineage_client,
        issue: JiraIssue,
        task_id: str,
        payload: dict[str, Any],
    ) -> None:
        if not lineage_client:
            return
        lineage_payload = {
            "tenant_id": lineage_client.tenant_id,
            "connector": "jira",
            "source": {
                "system": "jira",
                "object": "issue",
                "record_id": issue.issue_id,
                "key": issue.key,
            },
            "target": {
                "schema": "task",
                "record_id": task_id,
            },
            "transformations": [
                "jira.summary -> task.title",
                "jira.status -> task.status",
                "jira.issue_id -> task.external_id",
            ],
            "entity_type": "task",
            "entity_payload": payload,
            "metadata": {"updated_at": issue.updated_at},
        }
        try:
            lineage_client.emit_event(lineage_payload)
        except Exception:  # noqa: BLE001
            return
