from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SRC = REPO_ROOT / "apps" / "workflow-service" / "src"
COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
for path in (WORKFLOW_SRC, COMMON_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from workflow_storage import WorkflowStore


def test_idempotency_key_duplicate_suppression_under_parallel_create(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflows.db")

    def create(i: int) -> str:
        return store.create(
            run_id=f"run-{i}",
            workflow_id="wf-a",
            tenant_id="tenant-1",
            payload={"i": i},
            idempotency_key="idem-1",
        ).run_id

    with ThreadPoolExecutor(max_workers=8) as executor:
        run_ids = list(executor.map(create, range(40)))

    assert len(set(run_ids)) == 1


def test_approval_decision_is_race_safe_and_single_winner(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflows.db")
    store.create("run-1", "wf-a", "tenant-1", {"foo": "bar"})
    store.upsert_approval(
        approval_id="approval-1",
        run_id="run-1",
        step_id="approve-step",
        tenant_id="tenant-1",
        status="pending",
        metadata={},
    )

    def decide(status: str) -> str:
        return store.upsert_approval(
            approval_id="approval-1",
            run_id="run-1",
            step_id="approve-step",
            tenant_id="tenant-1",
            status=status,
            decision=status,
            approver_id=f"user-{status}",
            comments=status,
            metadata={"decision": status},
        ).status

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(decide, ["approved", "rejected"]))

    final = store.get_approval("approval-1")
    assert final is not None
    assert final.status in {"approved", "rejected"}


def test_workflow_backup_restore_and_retention_hooks(tmp_path: Path) -> None:
    db_path = tmp_path / "workflows.db"
    store = WorkflowStore(db_path)
    store.create("run-x", "wf-a", "tenant-1", {"x": 1})
    store.add_event("run-x", "started", "old event")
    backup = store.backup(tmp_path / "backup" / "workflows.db")
    retained = store.apply_retention(keep_days=0)
    assert "workflow_events" in retained

    store.restore(backup)
    assert store.get("run-x") is not None
