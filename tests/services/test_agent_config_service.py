from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

if not hasattr(sqlalchemy, 'ForeignKey'):
    pytest.skip('agent-config RBAC tests require full SQLAlchemy ForeignKey support', allow_module_level=True)

from agent_config_service import AgentConfigRBACStore


@pytest.fixture
def rbac_store(tmp_path: Path) -> AgentConfigRBACStore:
    store = AgentConfigRBACStore(f"sqlite:///{tmp_path / 'rbac.db'}")
    store.initialize()
    return store


def test_rbac_user_role_crud_and_authorization_checks(rbac_store: AgentConfigRBACStore) -> None:
    rbac_store.sync_user_roles(
        user_id="u-1",
        tenant_id="t-1",
        roles=["PM"],
        display_name="First User",
        email="first@example.com",
    )

    assert rbac_store.get_user_roles("u-1", "t-1") == ["PM"]
    assert rbac_store.can_user_configure_agents("u-1", "t-1") is True

    rbac_store.sync_user_roles(
        user_id="u-1",
        tenant_id="t-1",
        roles=["TEAM_MEMBER"],
        display_name="Renamed",
        email="rename@example.com",
    )

    assert rbac_store.get_user_roles("u-1", "t-1") == ["TEAM_MEMBER"]
    assert rbac_store.can_user_configure_agents("u-1", "t-1") is False

    rbac_store.sync_user_roles(user_id="u-1", tenant_id="t-1", roles=[])

    assert rbac_store.get_user_roles("u-1", "t-1") == []
    assert rbac_store.can_user_configure_agents("u-1", "t-1") is False


def test_rbac_persistence_conflict_and_delete_behavior(rbac_store: AgentConfigRBACStore, tmp_path: Path) -> None:
    rbac_store.sync_user_roles(
        user_id="u-2",
        tenant_id="t-2",
        roles=["PM", "PM", "AUDITOR"],
        display_name="Duplicate Roles",
    )
    rbac_store.sync_user_roles(user_id="u-3", tenant_id="t-2", roles=["PM"])

    db_path = tmp_path / "rbac.db"
    with sqlite3.connect(db_path) as conn:
        role_rows = conn.execute("SELECT role_id FROM rbac_roles ORDER BY role_id").fetchall()
        assert role_rows == [("AUDITOR",), ("PM",)]

        user_role_rows = conn.execute(
            "SELECT user_id, role_id FROM rbac_user_roles WHERE user_id = 'u-2' ORDER BY role_id"
        ).fetchall()
        assert user_role_rows == [("u-2", "AUDITOR"), ("u-2", "PM")]

    rbac_store.sync_user_roles(user_id="u-2", tenant_id="t-2", roles=[])
    with sqlite3.connect(db_path) as conn:
        user_role_rows_after_delete = conn.execute(
            "SELECT user_id, role_id FROM rbac_user_roles WHERE user_id = 'u-2'"
        ).fetchall()
        assert user_role_rows_after_delete == []


def test_rbac_database_failure_can_be_retried(monkeypatch, rbac_store: AgentConfigRBACStore) -> None:
    original_begin = rbac_store.engine.begin
    attempts = {"count": 0}

    def flaky_begin():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise SQLAlchemyError("transient db outage")
        return original_begin()

    monkeypatch.setattr(rbac_store.engine, "begin", flaky_begin)

    with pytest.raises(RuntimeError, match="Failed to sync RBAC roles"):
        rbac_store.sync_user_roles(user_id="retry-user", tenant_id="tenant", roles=["PM"])

    rbac_store.sync_user_roles(user_id="retry-user", tenant_id="tenant", roles=["PMO_ADMIN"])
    assert rbac_store.get_user_roles("retry-user", "tenant") == ["PMO_ADMIN"]
