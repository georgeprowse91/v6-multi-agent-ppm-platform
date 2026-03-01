from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

from agents.runtime.src.state_store import TenantStateStore
from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class WorkflowStateStore(Protocol):
    async def initialize(self) -> None: ...

    async def get_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None: ...

    async def save_definition(
        self, tenant_id: str, workflow_id: str, definition: dict[str, Any]
    ) -> None: ...

    async def get_instance(self, tenant_id: str, instance_id: str) -> dict[str, Any] | None: ...

    async def save_instance(
        self, tenant_id: str, instance_id: str, instance: dict[str, Any]
    ) -> None: ...

    async def list_instances(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def get_task(self, tenant_id: str, task_id: str) -> dict[str, Any] | None: ...

    async def save_task(self, tenant_id: str, task_id: str, task: dict[str, Any]) -> None: ...

    async def list_tasks(
        self, tenant_id: str, *, assignee: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def save_subscription(
        self, tenant_id: str, subscription_id: str, subscription: dict[str, Any]
    ) -> None: ...

    async def list_subscriptions(
        self, tenant_id: str, event_type: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def save_event(self, tenant_id: str, event_id: str, event: dict[str, Any]) -> None: ...

    async def list_events(self, tenant_id: str) -> list[dict[str, Any]]: ...


class JsonWorkflowStateStore:
    def __init__(
        self,
        definition_path: Path,
        instance_path: Path,
        task_path: Path,
        event_path: Path,
        subscription_path: Path,
    ) -> None:
        self.definition_store = TenantStateStore(definition_path)
        self.instance_store = TenantStateStore(instance_path)
        self.task_store = TenantStateStore(task_path)
        self.event_store = TenantStateStore(event_path)
        self.subscription_store = TenantStateStore(subscription_path)

    async def initialize(self) -> None:
        return None

    async def get_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        return self.definition_store.get(tenant_id, workflow_id)

    async def save_definition(
        self, tenant_id: str, workflow_id: str, definition: dict[str, Any]
    ) -> None:
        self.definition_store.upsert(tenant_id, workflow_id, definition)

    async def get_instance(self, tenant_id: str, instance_id: str) -> dict[str, Any] | None:
        return self.instance_store.get(tenant_id, instance_id)

    async def save_instance(
        self, tenant_id: str, instance_id: str, instance: dict[str, Any]
    ) -> None:
        self.instance_store.upsert(tenant_id, instance_id, instance)

    async def list_instances(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.instance_store.list(tenant_id)

    async def get_task(self, tenant_id: str, task_id: str) -> dict[str, Any] | None:
        return self.task_store.get(tenant_id, task_id)

    async def save_task(self, tenant_id: str, task_id: str, task: dict[str, Any]) -> None:
        self.task_store.upsert(tenant_id, task_id, task)

    async def list_tasks(
        self, tenant_id: str, *, assignee: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        tasks = self.task_store.list(tenant_id)
        filtered = []
        for task in tasks:
            if assignee and task.get("assignee") != assignee:
                continue
            if status and task.get("status") != status:
                continue
            filtered.append(task)
        return filtered

    async def save_subscription(
        self, tenant_id: str, subscription_id: str, subscription: dict[str, Any]
    ) -> None:
        self.subscription_store.upsert(tenant_id, subscription_id, subscription)

    async def list_subscriptions(
        self, tenant_id: str, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        subscriptions = self.subscription_store.list(tenant_id)
        if not event_type:
            return subscriptions
        return [sub for sub in subscriptions if sub.get("event_type") == event_type]

    async def save_event(self, tenant_id: str, event_id: str, event: dict[str, Any]) -> None:
        self.event_store.upsert(tenant_id, event_id, event)

    async def list_events(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.event_store.list(tenant_id)


metadata = MetaData()

WORKFLOW_DEFINITION_TABLE = Table(
    "workflow_definitions",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("workflow_id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", String(512)),
    Column("version", String(32), nullable=False),
    Column("definition", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

WORKFLOW_INSTANCE_TABLE = Table(
    "workflow_runs",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("instance_id", String(64), primary_key=True),
    Column("workflow_id", String(64), nullable=False),
    Column("status", String(64), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

WORKFLOW_TASK_TABLE = Table(
    "workflow_tasks",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("task_id", String(64), primary_key=True),
    Column("instance_id", String(64), nullable=False),
    Column("status", String(64), nullable=False),
    Column("task_type", String(64)),
    Column("assignee", String(128)),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

WORKFLOW_EVENT_TABLE = Table(
    "workflow_events",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("event_id", String(64), primary_key=True),
    Column("event_type", String(128), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

WORKFLOW_SUBSCRIPTION_TABLE = Table(
    "workflow_event_subscriptions",
    metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("subscription_id", String(64), primary_key=True),
    Column("workflow_id", String(64), nullable=False),
    Column("event_type", String(128), nullable=False),
    Column("action", String(64), nullable=False),
    Column("task_id", String(64)),
    Column("criteria", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


class DatabaseWorkflowStateStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        # In-memory fallback for offline/stub environments where the DB is a no-op
        self._mem_definitions: dict[str, dict[str, Any]] = {}
        self._mem_instances: dict[str, dict[str, Any]] = {}
        self._mem_tasks: dict[str, dict[str, Any]] = {}
        self._mem_subscriptions: dict[str, dict[str, Any]] = {}
        self._mem_events: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def get_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WORKFLOW_DEFINITION_TABLE).where(
                    WORKFLOW_DEFINITION_TABLE.c.tenant_id == tenant_id,
                    WORKFLOW_DEFINITION_TABLE.c.workflow_id == workflow_id,
                )
            )
            row = result.fetchone()
        if not row:
            return self._mem_definitions.get(f"{tenant_id}:{workflow_id}")
        return dict(row.definition)

    async def save_definition(
        self, tenant_id: str, workflow_id: str, definition: dict[str, Any]
    ) -> None:
        self._mem_definitions[f"{tenant_id}:{workflow_id}"] = definition.copy()
        async with self.session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(WORKFLOW_DEFINITION_TABLE.c.workflow_id).where(
                        WORKFLOW_DEFINITION_TABLE.c.tenant_id == tenant_id,
                        WORKFLOW_DEFINITION_TABLE.c.workflow_id == workflow_id,
                    )
                )
                payload = definition.copy()
                name = payload.get("name") or ""
                description = payload.get("description")
                version = str(payload.get("version", "1"))
                if existing.first():
                    await session.execute(
                        WORKFLOW_DEFINITION_TABLE.update()
                        .where(
                            WORKFLOW_DEFINITION_TABLE.c.tenant_id == tenant_id,
                            WORKFLOW_DEFINITION_TABLE.c.workflow_id == workflow_id,
                        )
                        .values(
                            name=name,
                            description=description,
                            version=version,
                            definition=payload,
                            updated_at=func.now(),
                        )
                    )
                else:
                    await session.execute(
                        WORKFLOW_DEFINITION_TABLE.insert().values(
                            tenant_id=tenant_id,
                            workflow_id=workflow_id,
                            name=name,
                            description=description,
                            version=version,
                            definition=payload,
                        )
                    )

    async def get_instance(self, tenant_id: str, instance_id: str) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WORKFLOW_INSTANCE_TABLE).where(
                    WORKFLOW_INSTANCE_TABLE.c.tenant_id == tenant_id,
                    WORKFLOW_INSTANCE_TABLE.c.instance_id == instance_id,
                )
            )
            row = result.fetchone()
        if not row:
            return self._mem_instances.get(f"{tenant_id}:{instance_id}")
        return dict(row.payload)

    async def save_instance(
        self, tenant_id: str, instance_id: str, instance: dict[str, Any]
    ) -> None:
        self._mem_instances[f"{tenant_id}:{instance_id}"] = instance.copy()
        async with self.session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(WORKFLOW_INSTANCE_TABLE.c.instance_id).where(
                        WORKFLOW_INSTANCE_TABLE.c.tenant_id == tenant_id,
                        WORKFLOW_INSTANCE_TABLE.c.instance_id == instance_id,
                    )
                )
                payload = instance.copy()
                status = payload.get("status") or "unknown"
                workflow_id = payload.get("workflow_id") or "unknown"
                if existing.first():
                    await session.execute(
                        WORKFLOW_INSTANCE_TABLE.update()
                        .where(
                            WORKFLOW_INSTANCE_TABLE.c.tenant_id == tenant_id,
                            WORKFLOW_INSTANCE_TABLE.c.instance_id == instance_id,
                        )
                        .values(
                            workflow_id=workflow_id,
                            status=status,
                            payload=payload,
                            updated_at=func.now(),
                        )
                    )
                else:
                    await session.execute(
                        WORKFLOW_INSTANCE_TABLE.insert().values(
                            tenant_id=tenant_id,
                            instance_id=instance_id,
                            workflow_id=workflow_id,
                            status=status,
                            payload=payload,
                        )
                    )

    async def list_instances(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WORKFLOW_INSTANCE_TABLE).where(
                    WORKFLOW_INSTANCE_TABLE.c.tenant_id == tenant_id
                )
            )
            rows = result.fetchall()
        if rows:
            return [dict(row.payload) for row in rows]
        prefix = f"{tenant_id}:"
        return [v for k, v in self._mem_instances.items() if k.startswith(prefix)]

    async def get_task(self, tenant_id: str, task_id: str) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WORKFLOW_TASK_TABLE).where(
                    WORKFLOW_TASK_TABLE.c.tenant_id == tenant_id,
                    WORKFLOW_TASK_TABLE.c.task_id == task_id,
                )
            )
            row = result.fetchone()
        if not row:
            return self._mem_tasks.get(f"{tenant_id}:{task_id}")
        return dict(row.payload)

    async def save_task(self, tenant_id: str, task_id: str, task: dict[str, Any]) -> None:
        self._mem_tasks[f"{tenant_id}:{task_id}"] = task.copy()
        async with self.session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(WORKFLOW_TASK_TABLE.c.task_id).where(
                        WORKFLOW_TASK_TABLE.c.tenant_id == tenant_id,
                        WORKFLOW_TASK_TABLE.c.task_id == task_id,
                    )
                )
                payload = task.copy()
                status = payload.get("status") or "unknown"
                instance_id = payload.get("instance_id") or "unknown"
                if existing.first():
                    await session.execute(
                        WORKFLOW_TASK_TABLE.update()
                        .where(
                            WORKFLOW_TASK_TABLE.c.tenant_id == tenant_id,
                            WORKFLOW_TASK_TABLE.c.task_id == task_id,
                        )
                        .values(
                            instance_id=instance_id,
                            status=status,
                            task_type=payload.get("task_type"),
                            assignee=payload.get("assignee"),
                            payload=payload,
                            updated_at=func.now(),
                        )
                    )
                else:
                    await session.execute(
                        WORKFLOW_TASK_TABLE.insert().values(
                            tenant_id=tenant_id,
                            task_id=task_id,
                            instance_id=instance_id,
                            status=status,
                            task_type=payload.get("task_type"),
                            assignee=payload.get("assignee"),
                            payload=payload,
                        )
                    )

    async def list_tasks(
        self, tenant_id: str, *, assignee: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            statement = select(WORKFLOW_TASK_TABLE).where(
                WORKFLOW_TASK_TABLE.c.tenant_id == tenant_id
            )
            if assignee:
                statement = statement.where(WORKFLOW_TASK_TABLE.c.assignee == assignee)
            if status:
                statement = statement.where(WORKFLOW_TASK_TABLE.c.status == status)
            result = await session.execute(statement)
            rows = result.fetchall()
        if rows:
            return [dict(row.payload) for row in rows]
        prefix = f"{tenant_id}:"
        tasks = [v for k, v in self._mem_tasks.items() if k.startswith(prefix)]
        if assignee:
            tasks = [t for t in tasks if t.get("assignee") == assignee]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    async def save_subscription(
        self, tenant_id: str, subscription_id: str, subscription: dict[str, Any]
    ) -> None:
        self._mem_subscriptions[f"{tenant_id}:{subscription_id}"] = subscription.copy()
        async with self.session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(WORKFLOW_SUBSCRIPTION_TABLE.c.subscription_id).where(
                        WORKFLOW_SUBSCRIPTION_TABLE.c.tenant_id == tenant_id,
                        WORKFLOW_SUBSCRIPTION_TABLE.c.subscription_id == subscription_id,
                    )
                )
                payload = subscription.copy()
                if existing.first():
                    await session.execute(
                        WORKFLOW_SUBSCRIPTION_TABLE.update()
                        .where(
                            WORKFLOW_SUBSCRIPTION_TABLE.c.tenant_id == tenant_id,
                            WORKFLOW_SUBSCRIPTION_TABLE.c.subscription_id == subscription_id,
                        )
                        .values(
                            workflow_id=payload.get("workflow_id"),
                            event_type=payload.get("event_type"),
                            action=payload.get("action"),
                            task_id=payload.get("task_id"),
                            criteria=payload.get("criteria") or {},
                        )
                    )
                else:
                    await session.execute(
                        WORKFLOW_SUBSCRIPTION_TABLE.insert().values(
                            tenant_id=tenant_id,
                            subscription_id=subscription_id,
                            workflow_id=payload.get("workflow_id"),
                            event_type=payload.get("event_type"),
                            action=payload.get("action"),
                            task_id=payload.get("task_id"),
                            criteria=payload.get("criteria") or {},
                        )
                    )

    async def list_subscriptions(
        self, tenant_id: str, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            statement = select(WORKFLOW_SUBSCRIPTION_TABLE).where(
                WORKFLOW_SUBSCRIPTION_TABLE.c.tenant_id == tenant_id
            )
            if event_type:
                statement = statement.where(WORKFLOW_SUBSCRIPTION_TABLE.c.event_type == event_type)
            result = await session.execute(statement)
            rows = result.fetchall()
        if rows:
            subscriptions = []
            for row in rows:
                subscriptions.append(
                    {
                        "subscription_id": row.subscription_id,
                        "workflow_id": row.workflow_id,
                        "event_type": row.event_type,
                        "action": row.action,
                        "task_id": row.task_id,
                        "criteria": row.criteria or {},
                    }
                )
            return subscriptions
        prefix = f"{tenant_id}:"
        subs = [v for k, v in self._mem_subscriptions.items() if k.startswith(prefix)]
        if event_type:
            subs = [s for s in subs if s.get("event_type") == event_type]
        return subs

    async def save_event(self, tenant_id: str, event_id: str, event: dict[str, Any]) -> None:
        self._mem_events.append({"tenant_id": tenant_id, "event_id": event_id, **event.copy()})
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    WORKFLOW_EVENT_TABLE.insert().values(
                        tenant_id=tenant_id,
                        event_id=event_id,
                        event_type=event.get("event_type"),
                        payload=event,
                    )
                )

    async def list_events(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WORKFLOW_EVENT_TABLE).where(WORKFLOW_EVENT_TABLE.c.tenant_id == tenant_id)
            )
            rows = result.fetchall()
        if rows:
            return [dict(row.payload) for row in rows]
        return [e for e in self._mem_events if e.get("tenant_id") == tenant_id]


def build_workflow_state_store(config: dict[str, Any] | None = None) -> WorkflowStateStore:
    config = config or {}
    backend = (
        config.get("workflow_state_backend") or os.getenv("WORKFLOW_STATE_BACKEND", "") or ""
    ).lower()
    database_url = (
        config.get("workflow_database_url")
        or os.getenv("WORKFLOW_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if database_url and backend in {"", "db", "database", "postgres", "postgresql"}:
        return DatabaseWorkflowStateStore(_to_async_database_url(database_url))
    if backend in {"db", "database", "postgres", "postgresql"} and not database_url:
        raise ValueError("workflow_database_url is required for database backend")
    definition_path = Path(config.get("workflow_definition_store_path", "data/workflows.json"))
    instance_path = Path(config.get("workflow_instance_store_path", "data/workflow_instances.json"))
    task_path = Path(config.get("workflow_task_store_path", "data/workflow_tasks.json"))
    event_path = Path(config.get("workflow_event_store_path", "data/workflow_events.json"))
    subscription_path = Path(
        config.get("workflow_subscription_store_path", "data/workflow_subscriptions.json")
    )
    return JsonWorkflowStateStore(
        definition_path,
        instance_path,
        task_path,
        event_path,
        subscription_path,
    )


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
