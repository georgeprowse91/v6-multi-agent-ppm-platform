from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_real_sqlalchemy():
    """Ensure real sqlalchemy (not vendor stub) is loaded. Returns True or False."""
    vendor_dir = str(_REPO_ROOT / "vendor")
    # Clear cached modules that may hold references to the vendor stub
    for key in list(sys.modules):
        if key == "sqlalchemy" or key.startswith("sqlalchemy."):
            del sys.modules[key]
        if key == "alembic" or key.startswith("alembic."):
            del sys.modules[key]
    # Also clear persistence so it re-imports with real sqlalchemy
    for key in list(sys.modules):
        if key == "persistence" or key.startswith("persistence."):
            del sys.modules[key]

    removed = vendor_dir in sys.path
    if removed:
        sys.path.remove(vendor_dir)
    try:
        import sqlalchemy  # noqa: F401
        import alembic  # noqa: F401
        return True
    except ImportError:
        return False
    finally:
        if removed:
            sys.path.append(vendor_dir)


def _database_urls(tmp_path: Path) -> tuple[str, str]:
    db_path = tmp_path / "orchestration.db"
    return (f"sqlite:///{db_path}", f"sqlite+aiosqlite:///{db_path}")


def _run_migrations(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        config = Config(str(_REPO_ROOT / "ops" / "config" / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", database_url)
        config.set_main_option("script_location", str(_REPO_ROOT / "data" / "migrations"))
        command.upgrade(config, "head")
    finally:
        if old_db_url is not None:
            os.environ["DATABASE_URL"] = old_db_url


@pytest.mark.asyncio
async def test_orchestrator_state_persists_across_restart(monkeypatch, tmp_path) -> None:
    if not _ensure_real_sqlalchemy():
        pytest.skip("real sqlalchemy/alembic not installed")

    sync_url, async_url = _database_urls(tmp_path)
    _run_migrations(sync_url)
    monkeypatch.setenv("ORCHESTRATION_STATE_BACKEND", "db")
    monkeypatch.setenv("ORCHESTRATION_DATABASE_URL", async_url)

    _orch_path = _REPO_ROOT / "apps" / "orchestration-service" / "src" / "orchestrator.py"
    _spec = importlib.util.spec_from_file_location("_orch_persistence_mod", _orch_path)
    _orch_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_orch_mod)
    AgentOrchestrator = _orch_mod.AgentOrchestrator

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
    if not _ensure_real_sqlalchemy():
        pytest.skip("real sqlalchemy/alembic not installed")

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
