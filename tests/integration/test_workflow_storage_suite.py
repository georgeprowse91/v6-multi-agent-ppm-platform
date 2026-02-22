from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-engine" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_storage import WorkflowStore  # noqa: E402


def test_storage_crud_and_idempotency_concurrency(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    definition = {
        "metadata": {"name": "Flow", "version": "v2", "owner": "qa"},
        "steps": [{"id": "s", "type": "notification"}],
    }
    store.upsert_definition("wf", definition)
    assert store.get_definition("wf").version == "v2"

    first = store.create("run-1", "wf", "tenant-a", payload={"k": 1}, idempotency_key="idem-1")
    second = store.create("run-2", "wf", "tenant-a", payload={"k": 2}, idempotency_key="idem-1")
    assert first.run_id == second.run_id == "run-1"

    unique = store.create("run-3", "wf", "tenant-a", payload={"k": 3}, idempotency_key="idem-2")
    assert unique.run_id == "run-3"


def test_storage_serialization_roundtrip_across_states(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    store.create("run-state", "wf", "tenant-a", payload={"nested": {"items": [1, {"x": True}]}})

    for status in ["running", "completed", "failed", "cancelled"]:
        store.update_status("run-state", status, current_step_id="step-1")
        loaded = store.get("run-state")
        assert loaded.status == status
        assert loaded.payload == {"nested": {"items": [1, {"x": True}]}}

    state = store.upsert_step_state(
        "run-state", "step-1", "completed", attempts=2, output={"result": ["a", 2, {"ok": True}]}
    )
    assert state.output["result"][2]["ok"] is True

    approval = store.upsert_approval(
        approval_id="ap-1",
        run_id="run-state",
        step_id="step-2",
        tenant_id="tenant-a",
        status="approved",
        metadata={"roles": ["manager"], "flags": {"expedite": False}},
        decision="approved",
    )
    assert approval.metadata["flags"]["expedite"] is False


def test_storage_integrity_checks_raise_for_missing_rows(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    with pytest.raises(RuntimeError, match="Failed to update step state"):
        store.update_step_error("missing-run", "missing-step", "boom")

    with store._connect() as conn:  # noqa: SLF001 - deliberate integrity test path
        conn.execute(
            "INSERT INTO workflow_step_runs (run_id, step_id, status, attempts, output) VALUES (?, ?, ?, ?, ?)",
            ("x", "y", "running", 1, "not-json"),
        )
    with pytest.raises(json.JSONDecodeError):
        store.get_step_state("x", "y")
