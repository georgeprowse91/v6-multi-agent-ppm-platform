from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_real_sqlalchemy():
    """Import the real sqlalchemy, bypassing the vendor stub."""
    vendor_dir = str(_REPO_ROOT / "vendor")
    saved_modules = {}
    for key in list(sys.modules):
        if key == "sqlalchemy" or key.startswith("sqlalchemy."):
            saved_modules[key] = sys.modules.pop(key)

    removed = vendor_dir in sys.path
    if removed:
        sys.path.remove(vendor_dir)
    try:
        import sqlalchemy

        return sqlalchemy
    except ImportError:
        # Restore stub modules
        sys.modules.update(saved_modules)
        return None
    finally:
        if removed:
            sys.path.append(vendor_dir)


def _database_url(tmp_path: Path) -> str:
    db_path = tmp_path / "migrations.db"
    return f"sqlite:///{db_path}"


def _run_migrations(database_url: str) -> None:
    pytest.importorskip("alembic")
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


def test_missing_tables_created(tmp_path) -> None:
    sa = _load_real_sqlalchemy()
    if sa is None:
        pytest.skip("real sqlalchemy is not installed")

    database_url = _database_url(tmp_path)
    _run_migrations(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    assert "demands" in inspector.get_table_names()
    assert "resources" in inspector.get_table_names()
    assert "rois" in inspector.get_table_names()
    assert "agent_configs" in inspector.get_table_names()

    demand_columns = {column["name"] for column in inspector.get_columns("demands")}
    assert demand_columns == {
        "id",
        "tenant_id",
        "title",
        "description",
        "business_objective",
        "requester",
        "business_unit",
        "urgency",
        "source",
        "created_at",
        "updated_at",
    }

    resource_columns = {column["name"] for column in inspector.get_columns("resources")}
    assert resource_columns == {
        "id",
        "tenant_id",
        "name",
        "role",
        "location",
        "status",
        "created_at",
        "metadata",
    }

    roi_columns = {column["name"] for column in inspector.get_columns("rois")}
    assert roi_columns == {
        "id",
        "tenant_id",
        "roi",
        "created_at",
        "updated_at",
    }

    agent_config_columns = {column["name"] for column in inspector.get_columns("agent_configs")}
    assert agent_config_columns == {
        "tenant_id",
        "agents",
        "project_configs",
        "dev_users",
        "created_at",
        "updated_at",
    }
