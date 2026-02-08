from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.exc import IntegrityError

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class OptimisticLockError(RuntimeError):
    pass


@dataclass
class WorkflowState:
    run_id: str
    tenant_id: str
    status: str
    last_checkpoint: str
    payload: dict[str, Any]
    version: int = 0


def make_state_key(tenant_id: str, run_id: str) -> str:
    return f"{tenant_id}:{run_id}"


class OrchestrationStateStore(Protocol):
    async def load(self, tenant_id: str | None = None) -> dict[str, WorkflowState]: ...

    async def save(self, state: WorkflowState) -> WorkflowState: ...


class JsonOrchestrationStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))
        self.logger = logging.getLogger("orchestration-service.persistence")

    async def load(self, tenant_id: str | None = None) -> dict[str, WorkflowState]:
        raw = self._read_state()
        states: dict[str, WorkflowState] = {}
        for key, data in raw.items():
            payload = data.get("payload", {})
            resolved_tenant = (
                data.get("tenant_id")
                or payload.get("tenant_id")
                or os.getenv("AUTH_DEV_TENANT_ID", "default-tenant")
            )
            resolved_key = make_state_key(resolved_tenant, data.get("run_id", key))
            state = WorkflowState(
                run_id=data.get("run_id", key),
                tenant_id=resolved_tenant,
                status=data["status"],
                last_checkpoint=data["last_checkpoint"],
                payload=payload,
                version=int(data.get("version", 0)),
            )
            if tenant_id is None or state.tenant_id == tenant_id:
                states[resolved_key] = state
        return states

    async def save(self, state: WorkflowState) -> WorkflowState:
        raw = self._read_state()
        key = make_state_key(state.tenant_id, state.run_id)
        next_version = state.version + 1 if state.version else 1
        raw[key] = {
            "run_id": state.run_id,
            "tenant_id": state.tenant_id,
            "status": state.status,
            "last_checkpoint": state.last_checkpoint,
            "payload": state.payload,
            "version": next_version,
        }
        self.path.write_text(json.dumps(raw, indent=2))
        return WorkflowState(
            run_id=state.run_id,
            tenant_id=state.tenant_id,
            status=state.status,
            last_checkpoint=state.last_checkpoint,
            payload=state.payload,
            version=next_version,
        )

    def _read_state(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError:
            self.logger.warning("State file missing, recreating %s", self.path)
            self.path.write_text(json.dumps({}))
            return {}
        except json.JSONDecodeError:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            backup_path = self.path.with_suffix(f"{self.path.suffix}.corrupt.{timestamp}")
            self.logger.error(
                "State file corrupt, backing up to %s and resetting",
                backup_path,
            )
            self.path.rename(backup_path)
            self.path.write_text(json.dumps({}))
            return {}


class DatabaseOrchestrationStateStore:
    """Postgres-backed store.

    Assumes database-level encryption at rest. Optionally provide envelope encryption
    hooks to encrypt/decrypt the payload before persistence.
    """

    def __init__(
        self,
        database_url: str,
        *,
        encrypt_payload: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        decrypt_payload: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.engine = create_async_engine(database_url, pool_pre_ping=True)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        self.encrypt_payload = encrypt_payload
        self.decrypt_payload = decrypt_payload

    async def load(self, tenant_id: str | None = None) -> dict[str, WorkflowState]:
        async with self.session_factory() as session:
            statement = select(ORCHESTRATION_STATE_TABLE)
            if tenant_id:
                statement = statement.where(ORCHESTRATION_STATE_TABLE.c.tenant_id == tenant_id)
            result = await session.execute(statement)
            rows = result.fetchall()
        states: dict[str, WorkflowState] = {}
        for row in rows:
            payload = row.payload or {}
            if self.decrypt_payload:
                payload = self.decrypt_payload(payload)
            state = WorkflowState(
                run_id=row.run_id,
                tenant_id=row.tenant_id,
                status=row.status,
                last_checkpoint=row.last_checkpoint,
                payload=payload,
                version=row.version,
            )
            states[make_state_key(state.tenant_id, state.run_id)] = state
        return states

    async def save(self, state: WorkflowState) -> WorkflowState:
        payload = state.payload
        if self.encrypt_payload:
            payload = self.encrypt_payload(payload)
        async with self.session_factory() as session:
            async with session.begin():
                if state.version == 0:
                    try:
                        await session.execute(
                            ORCHESTRATION_STATE_TABLE.insert().values(
                                tenant_id=state.tenant_id,
                                run_id=state.run_id,
                                status=state.status,
                                last_checkpoint=state.last_checkpoint,
                                payload=payload,
                                version=1,
                            )
                        )
                        next_version = 1
                    except IntegrityError as exc:
                        raise OptimisticLockError(
                            "Orchestration state already exists for this tenant/run."
                        ) from exc
                else:
                    update_stmt = (
                        ORCHESTRATION_STATE_TABLE.update()
                        .where(
                            ORCHESTRATION_STATE_TABLE.c.tenant_id == state.tenant_id,
                            ORCHESTRATION_STATE_TABLE.c.run_id == state.run_id,
                            ORCHESTRATION_STATE_TABLE.c.version == state.version,
                        )
                        .values(
                            status=state.status,
                            last_checkpoint=state.last_checkpoint,
                            payload=payload,
                            version=state.version + 1,
                            updated_at=func.now(),
                        )
                    )
                    result = await session.execute(update_stmt)
                    if result.rowcount == 0:
                        raise OptimisticLockError("Orchestration state update conflict detected.")
                    next_version = state.version + 1
        return WorkflowState(
            run_id=state.run_id,
            tenant_id=state.tenant_id,
            status=state.status,
            last_checkpoint=state.last_checkpoint,
            payload=state.payload,
            version=next_version,
        )


def build_state_store(state_path: Path) -> OrchestrationStateStore:
    backend = os.getenv("ORCHESTRATION_STATE_BACKEND", "").lower()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    database_url = os.getenv("ORCHESTRATION_DATABASE_URL") or os.getenv("DATABASE_URL")

    if backend in {"file", "json"}:
        return JsonOrchestrationStateStore(state_path)

    if database_url and (backend in {"db", "database", "postgres"} or environment != "development"):
        return DatabaseOrchestrationStateStore(_to_async_database_url(database_url))

    if database_url and backend == "":
        return DatabaseOrchestrationStateStore(_to_async_database_url(database_url))

    return JsonOrchestrationStateStore(state_path)


def _to_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


metadata = MetaData()

ORCHESTRATION_STATE_TABLE = Table(
    "orchestration_states",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("run_id", String(64), primary_key=True),
    Column("status", String(64), nullable=False),
    Column("last_checkpoint", String(255), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("version", Integer, nullable=False, default=1),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)
