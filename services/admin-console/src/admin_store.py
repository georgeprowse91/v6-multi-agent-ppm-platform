"""Admin Console storage layer.

Provides SQLite-backed persistence for tenant configuration, connector
instances, agent settings overrides, and system monitoring snapshots.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TenantConfig:
    tenant_id: str
    display_name: str
    environment: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class ConnectorInstance:
    instance_id: str
    tenant_id: str
    connector_type: str
    name: str
    enabled: bool
    config: dict[str, Any]
    health_status: str
    last_synced: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AgentSetting:
    setting_id: str
    tenant_id: str
    agent_id: str
    enabled: bool
    parameters: dict[str, Any]
    updated_at: datetime
    updated_by: str | None


@dataclass
class SystemEvent:
    event_id: str
    tenant_id: str
    event_type: str
    source: str
    severity: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime


# ---------------------------------------------------------------------------
# Store implementation
# ---------------------------------------------------------------------------


class AdminStore:
    """SQLite-backed storage for admin console entities."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def ping(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    environment TEXT NOT NULL DEFAULT 'development',
                    settings TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS connector_instances (
                    instance_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connector_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    config TEXT NOT NULL DEFAULT '{}',
                    health_status TEXT NOT NULL DEFAULT 'unknown',
                    last_synced TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_settings (
                    setting_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    parameters TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL,
                    updated_by TEXT,
                    UNIQUE(tenant_id, agent_id)
                );

                CREATE TABLE IF NOT EXISTS system_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'info',
                    message TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_connector_instances_tenant
                    ON connector_instances(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_agent_settings_tenant
                    ON agent_settings(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_system_events_tenant_type
                    ON system_events(tenant_id, event_type);
                CREATE INDEX IF NOT EXISTS idx_system_events_created
                    ON system_events(created_at);
                """)

    # -----------------------------------------------------------------------
    # Tenant configuration
    # -----------------------------------------------------------------------

    def create_tenant(
        self,
        tenant_id: str,
        display_name: str,
        environment: str = "development",
        settings: dict[str, Any] | None = None,
    ) -> TenantConfig:
        now = datetime.now(timezone.utc).isoformat()
        settings = settings or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tenants (tenant_id, display_name, environment, settings,
                                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, display_name, environment, json.dumps(settings), now, now),
            )
        return TenantConfig(
            tenant_id=tenant_id,
            display_name=display_name,
            environment=environment,
            settings=settings,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_tenant(self, tenant_id: str) -> TenantConfig | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
        return self._deserialize_tenant(row) if row else None

    def list_tenants(self) -> list[TenantConfig]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tenants ORDER BY display_name").fetchall()
        return [self._deserialize_tenant(row) for row in rows]

    def update_tenant(
        self,
        tenant_id: str,
        display_name: str | None = None,
        environment: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> TenantConfig | None:
        existing = self.get_tenant(tenant_id)
        if not existing:
            return None
        now = datetime.now(timezone.utc).isoformat()
        new_name = display_name if display_name is not None else existing.display_name
        new_env = environment if environment is not None else existing.environment
        new_settings = settings if settings is not None else existing.settings
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tenants
                SET display_name = ?, environment = ?, settings = ?, updated_at = ?
                WHERE tenant_id = ?
                """,
                (new_name, new_env, json.dumps(new_settings), now, tenant_id),
            )
        return self.get_tenant(tenant_id)

    def delete_tenant(self, tenant_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        return cursor.rowcount > 0

    def _deserialize_tenant(self, row: sqlite3.Row) -> TenantConfig:
        return TenantConfig(
            tenant_id=row["tenant_id"],
            display_name=row["display_name"],
            environment=row["environment"],
            settings=json.loads(row["settings"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # -----------------------------------------------------------------------
    # Connector instances
    # -----------------------------------------------------------------------

    def create_connector_instance(
        self,
        tenant_id: str,
        connector_type: str,
        name: str,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> ConnectorInstance:
        instance_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        config = config or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connector_instances
                    (instance_id, tenant_id, connector_type, name, enabled, config,
                     health_status, last_synced, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    tenant_id,
                    connector_type,
                    name,
                    1 if enabled else 0,
                    json.dumps(config),
                    "unknown",
                    None,
                    now,
                    now,
                ),
            )
        return ConnectorInstance(
            instance_id=instance_id,
            tenant_id=tenant_id,
            connector_type=connector_type,
            name=name,
            enabled=enabled,
            config=config,
            health_status="unknown",
            last_synced=None,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def list_connector_instances(self, tenant_id: str) -> list[ConnectorInstance]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM connector_instances WHERE tenant_id = ? ORDER BY name",
                (tenant_id,),
            ).fetchall()
        return [self._deserialize_connector(row) for row in rows]

    def get_connector_instance(self, tenant_id: str, instance_id: str) -> ConnectorInstance | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM connector_instances
                WHERE tenant_id = ? AND instance_id = ?
                """,
                (tenant_id, instance_id),
            ).fetchone()
        return self._deserialize_connector(row) if row else None

    def update_connector_instance(
        self,
        tenant_id: str,
        instance_id: str,
        name: str | None = None,
        enabled: bool | None = None,
        config: dict[str, Any] | None = None,
        health_status: str | None = None,
    ) -> ConnectorInstance | None:
        existing = self.get_connector_instance(tenant_id, instance_id)
        if not existing:
            return None
        now = datetime.now(timezone.utc).isoformat()
        new_name = name if name is not None else existing.name
        new_enabled = enabled if enabled is not None else existing.enabled
        new_config = config if config is not None else existing.config
        new_health = health_status if health_status is not None else existing.health_status
        last_synced = (
            now
            if health_status is not None
            else (existing.last_synced.isoformat() if existing.last_synced else None)
        )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE connector_instances
                SET name = ?, enabled = ?, config = ?, health_status = ?,
                    last_synced = ?, updated_at = ?
                WHERE instance_id = ? AND tenant_id = ?
                """,
                (
                    new_name,
                    1 if new_enabled else 0,
                    json.dumps(new_config),
                    new_health,
                    last_synced,
                    now,
                    instance_id,
                    tenant_id,
                ),
            )
        return self.get_connector_instance(tenant_id, instance_id)

    def delete_connector_instance(self, tenant_id: str, instance_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM connector_instances WHERE tenant_id = ? AND instance_id = ?",
                (tenant_id, instance_id),
            )
        return cursor.rowcount > 0

    def _deserialize_connector(self, row: sqlite3.Row) -> ConnectorInstance:
        return ConnectorInstance(
            instance_id=row["instance_id"],
            tenant_id=row["tenant_id"],
            connector_type=row["connector_type"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            config=json.loads(row["config"]),
            health_status=row["health_status"],
            last_synced=(
                datetime.fromisoformat(row["last_synced"]) if row["last_synced"] else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # -----------------------------------------------------------------------
    # Agent settings
    # -----------------------------------------------------------------------

    def upsert_agent_setting(
        self,
        tenant_id: str,
        agent_id: str,
        enabled: bool = True,
        parameters: dict[str, Any] | None = None,
        updated_by: str | None = None,
    ) -> AgentSetting:
        setting_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        parameters = parameters or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_settings
                    (setting_id, tenant_id, agent_id, enabled, parameters,
                     updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, agent_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    parameters = excluded.parameters,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (
                    setting_id,
                    tenant_id,
                    agent_id,
                    1 if enabled else 0,
                    json.dumps(parameters),
                    now,
                    updated_by,
                ),
            )
            row = conn.execute(
                "SELECT * FROM agent_settings WHERE tenant_id = ? AND agent_id = ?",
                (tenant_id, agent_id),
            ).fetchone()
        return self._deserialize_agent_setting(row)

    def list_agent_settings(self, tenant_id: str) -> list[AgentSetting]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_settings WHERE tenant_id = ? ORDER BY agent_id",
                (tenant_id,),
            ).fetchall()
        return [self._deserialize_agent_setting(row) for row in rows]

    def get_agent_setting(self, tenant_id: str, agent_id: str) -> AgentSetting | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_settings WHERE tenant_id = ? AND agent_id = ?",
                (tenant_id, agent_id),
            ).fetchone()
        return self._deserialize_agent_setting(row) if row else None

    def delete_agent_setting(self, tenant_id: str, agent_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM agent_settings WHERE tenant_id = ? AND agent_id = ?",
                (tenant_id, agent_id),
            )
        return cursor.rowcount > 0

    def _deserialize_agent_setting(self, row: sqlite3.Row) -> AgentSetting:
        return AgentSetting(
            setting_id=row["setting_id"],
            tenant_id=row["tenant_id"],
            agent_id=row["agent_id"],
            enabled=bool(row["enabled"]),
            parameters=json.loads(row["parameters"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            updated_by=row["updated_by"],
        )

    # -----------------------------------------------------------------------
    # System monitoring / events
    # -----------------------------------------------------------------------

    def record_event(
        self,
        tenant_id: str,
        event_type: str,
        source: str,
        message: str,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> SystemEvent:
        event_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO system_events
                    (event_id, tenant_id, event_type, source, severity,
                     message, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    tenant_id,
                    event_type,
                    source,
                    severity,
                    json.dumps(metadata),
                    now,
                ),
            )
        return SystemEvent(
            event_id=event_id,
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            severity=severity,
            message=message,
            metadata=metadata,
            created_at=datetime.fromisoformat(now),
        )

    def list_events(
        self,
        tenant_id: str,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SystemEvent]:
        query = "SELECT * FROM system_events WHERE tenant_id = ?"
        params: list[str | int] = [tenant_id]
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._deserialize_event(row) for row in rows]

    def count_events(
        self,
        tenant_id: str,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> int:
        query = "SELECT COUNT(*) as cnt FROM system_events WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return row["cnt"] if row else 0

    def _deserialize_event(self, row: sqlite3.Row) -> SystemEvent:
        return SystemEvent(
            event_id=row["event_id"],
            tenant_id=row["tenant_id"],
            event_type=row["event_type"],
            source=row["source"],
            severity=row["severity"],
            message=row["message"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
