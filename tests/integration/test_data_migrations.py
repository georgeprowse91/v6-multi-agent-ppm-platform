from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _database_url(tmp_path: Path) -> str:
    db_path = tmp_path / "migrations.db"
    return f"sqlite:///{db_path}"


def _run_migrations(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def test_missing_tables_created(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _run_migrations(database_url)

    engine = create_engine(database_url)
    inspector = inspect(engine)

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

    agent_config_columns = {
        column["name"] for column in inspector.get_columns("agent_configs")
    }
    assert agent_config_columns == {
        "tenant_id",
        "agents",
        "project_configs",
        "dev_users",
        "created_at",
        "updated_at",
    }
