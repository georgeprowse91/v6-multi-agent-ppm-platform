from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RBAC_ROLES_PATH = REPO_ROOT / "config" / "rbac" / "roles.yaml"


def _load_role_ids() -> set[str]:
    with RBAC_ROLES_PATH.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return {role.get("id") for role in payload.get("roles", []) if role.get("id")}


ROLE_IDS = _load_role_ids()


@dataclass(frozen=True)
class ScimUserRecord:
    id: str
    user_name: str
    display_name: str | None
    active: bool
    emails: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    roles: list[str]


@dataclass(frozen=True)
class ScimGroupRecord:
    id: str
    display_name: str
    members: list[dict[str, Any]]


class ScimStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    display_name TEXT,
                    active INTEGER NOT NULL,
                    emails TEXT,
                    roles TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, user_name)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, display_name)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS group_members (
                    tenant_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, group_id, user_id),
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

    def create_user(
        self,
        tenant_id: str,
        *,
        user_id: str,
        user_name: str,
        display_name: str | None,
        active: bool,
        emails: list[dict[str, Any]] | None,
        group_ids: list[str],
    ) -> ScimUserRecord:
        now = datetime.now(timezone.utc).isoformat()
        emails_json = json.dumps(emails or [])
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, tenant_id, user_name, display_name, active, emails, roles, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    tenant_id,
                    user_name,
                    display_name,
                    1 if active else 0,
                    emails_json,
                    json.dumps([]),
                    now,
                    now,
                ),
            )
            for group_id in group_ids:
                conn.execute(
                    """
                    INSERT INTO group_members (tenant_id, group_id, user_id)
                    VALUES (?, ?, ?)
                    """,
                    (tenant_id, group_id, user_id),
                )
        self.update_user_roles(tenant_id, user_id)
        return self.get_user(tenant_id, user_id)

    def update_user(
        self,
        tenant_id: str,
        user_id: str,
        *,
        display_name: str | None = None,
        active: bool | None = None,
        emails: list[dict[str, Any]] | None = None,
        group_ids: list[str] | None = None,
    ) -> ScimUserRecord:
        updates = []
        params: list[Any] = []
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        if active is not None:
            updates.append("active = ?")
            params.append(1 if active else 0)
        if emails is not None:
            updates.append("emails = ?")
            params.append(json.dumps(emails))
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.extend([tenant_id, user_id])
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE tenant_id = ? AND id = ?",
                    params,
                )
        if group_ids is not None:
            self.set_user_groups(tenant_id, user_id, group_ids)
        self.update_user_roles(tenant_id, user_id)
        return self.get_user(tenant_id, user_id)

    def get_user(self, tenant_id: str, user_id: str) -> ScimUserRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? AND id = ?",
                (tenant_id, user_id),
            ).fetchone()
            if not row:
                raise KeyError("user not found")
            groups = conn.execute(
                """
                SELECT g.id, g.display_name
                FROM group_members gm
                JOIN groups g ON g.id = gm.group_id
                WHERE gm.tenant_id = ? AND gm.user_id = ?
                ORDER BY g.display_name
                """,
                (tenant_id, user_id),
            ).fetchall()
            roles = json.loads(row["roles"] or "[]")
        return ScimUserRecord(
            id=row["id"],
            user_name=row["user_name"],
            display_name=row["display_name"],
            active=bool(row["active"]),
            emails=json.loads(row["emails"] or "[]"),
            groups=[{"value": g["id"], "display": g["display_name"]} for g in groups],
            roles=roles,
        )

    def list_users(self, tenant_id: str, user_name: str | None = None) -> list[ScimUserRecord]:
        with self._connect() as conn:
            if user_name:
                rows = conn.execute(
                    "SELECT id FROM users WHERE tenant_id = ? AND user_name = ?",
                    (tenant_id, user_name),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM users WHERE tenant_id = ? ORDER BY user_name",
                    (tenant_id,),
                ).fetchall()
        return [self.get_user(tenant_id, row["id"]) for row in rows]

    def create_group(
        self,
        tenant_id: str,
        *,
        group_id: str,
        display_name: str,
        members: list[str],
    ) -> ScimGroupRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO groups (id, tenant_id, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (group_id, tenant_id, display_name, now, now),
            )
            for user_id in members:
                conn.execute(
                    """
                    INSERT INTO group_members (tenant_id, group_id, user_id)
                    VALUES (?, ?, ?)
                    """,
                    (tenant_id, group_id, user_id),
                )
        for user_id in members:
            self.update_user_roles(tenant_id, user_id)
        return self.get_group(tenant_id, group_id)

    def get_group(self, tenant_id: str, group_id: str) -> ScimGroupRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM groups WHERE tenant_id = ? AND id = ?",
                (tenant_id, group_id),
            ).fetchone()
            if not row:
                raise KeyError("group not found")
            members = conn.execute(
                """
                SELECT u.id, u.user_name
                FROM group_members gm
                JOIN users u ON u.id = gm.user_id
                WHERE gm.tenant_id = ? AND gm.group_id = ?
                ORDER BY u.user_name
                """,
                (tenant_id, group_id),
            ).fetchall()
        return ScimGroupRecord(
            id=row["id"],
            display_name=row["display_name"],
            members=[{"value": member["id"], "display": member["user_name"]} for member in members],
        )

    def list_groups(self, tenant_id: str) -> list[ScimGroupRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM groups WHERE tenant_id = ? ORDER BY display_name",
                (tenant_id,),
            ).fetchall()
        return [self.get_group(tenant_id, row["id"]) for row in rows]

    def set_user_groups(self, tenant_id: str, user_id: str, group_ids: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM group_members WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id),
            )
            for group_id in group_ids:
                conn.execute(
                    """
                    INSERT INTO group_members (tenant_id, group_id, user_id)
                    VALUES (?, ?, ?)
                    """,
                    (tenant_id, group_id, user_id),
                )

    def update_group_members(
        self,
        tenant_id: str,
        group_id: str,
        *,
        add_members: list[str] | None = None,
        remove_members: list[str] | None = None,
    ) -> ScimGroupRecord:
        add_members = add_members or []
        remove_members = remove_members or []
        with self._connect() as conn:
            for user_id in add_members:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO group_members (tenant_id, group_id, user_id)
                    VALUES (?, ?, ?)
                    """,
                    (tenant_id, group_id, user_id),
                )
            for user_id in remove_members:
                conn.execute(
                    """
                    DELETE FROM group_members
                    WHERE tenant_id = ? AND group_id = ? AND user_id = ?
                    """,
                    (tenant_id, group_id, user_id),
                )
        for user_id in add_members + remove_members:
            self.update_user_roles(tenant_id, user_id)
        return self.get_group(tenant_id, group_id)

    def update_user_roles(self, tenant_id: str, user_id: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT g.display_name
                FROM group_members gm
                JOIN groups g ON g.id = gm.group_id
                WHERE gm.tenant_id = ? AND gm.user_id = ?
                """,
                (tenant_id, user_id),
            ).fetchall()
            roles = sorted({row["display_name"] for row in rows if row["display_name"] in ROLE_IDS})
            conn.execute(
                "UPDATE users SET roles = ?, updated_at = ? WHERE tenant_id = ? AND id = ?",
                (
                    json.dumps(roles),
                    datetime.now(timezone.utc).isoformat(),
                    tenant_id,
                    user_id,
                ),
            )
