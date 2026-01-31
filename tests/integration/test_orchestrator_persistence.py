from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("alembic")

from alembic import command
from alembic.config import Config


def _database_urls(tmp_path: Path) -> tuple[str, str]:
    db_path = tmp_path / "orchestration.db"
    return (f"sqlite:///{db_path}", f"sqlite+aiosqlite:///{db_path}")


def _run_migrations(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.mark.asyncio
async def test_orchestrator_state_persists_across_restart(monkeypatch, tmp_path) -> None:
    sync_url, async_url = _database_urls(tmp_path)
    _run_migrations(sync_url)
    monkeypatch.setenv("ORCHESTRATION_STATE_BACKEND", "db")
    monkeypatch.setenv("ORCHESTRATION_DATABASE_URL", async_url)

    from orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    await orchestrator.persist_workflow_state(
        "tenant-a", "run-1", "running", "step-1", {"tenant_id": "tenant-a"}
    )

    orchestrator_restarted = AgentOrchestrator()
    await orchestrator_restarted.initialize()

    assert "run-1" in orchestrator_restarted.resume_workflows("tenant-a")


@pytest.mark.asyncio
async def test_orchestrator_state_optimistic_lock(monkeypatch, tmp_path) -> None:
    sync_url, async_url = _database_urls(tmp_path)
    _run_migrations(sync_url)
    monkeypatch.setenv("ORCHESTRATION_DATABASE_URL", async_url)

    from persistence import DatabaseOrchestrationStateStore, OptimisticLockError, WorkflowState

    store_a = DatabaseOrchestrationStateStore(async_url)
    store_b = DatabaseOrchestrationStateStore(async_url)

    initial = WorkflowState(
        tenant_id="tenant-a",
        run_id="run-1",
        status="running",
        last_checkpoint="step-1",
        payload={"tenant_id": "tenant-a"},
        version=0,
    )
    saved = await store_a.save(initial)
    update_a = WorkflowState(
        tenant_id=saved.tenant_id,
        run_id=saved.run_id,
        status="paused",
        last_checkpoint="step-2",
        payload=saved.payload,
        version=saved.version,
    )
    update_b = WorkflowState(
        tenant_id=saved.tenant_id,
        run_id=saved.run_id,
        status="completed",
        last_checkpoint="step-3",
        payload=saved.payload,
        version=saved.version,
    )

    await store_a.save(update_a)
    with pytest.raises(OptimisticLockError):
        await store_b.save(update_b)
