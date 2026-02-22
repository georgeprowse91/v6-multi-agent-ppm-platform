from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    delete,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

logger = logging.getLogger("data-service")

metadata = MetaData()

SCHEMA_REGISTRY_TABLE = Table(
    "schema_registry",
    metadata,
    Column("name", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("schema", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

CANONICAL_ENTITIES_TABLE = Table(
    "canonical_entities",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("tenant_id", String(64), nullable=False, index=True),
    Column("schema_name", String(128), nullable=False, index=True),
    Column("schema_version", Integer, nullable=False),
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

SCHEMA_PROMOTIONS_TABLE = Table(
    "schema_promotions",
    metadata,
    Column("name", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("environment", String(32), primary_key=True),
    Column("promoted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


@dataclass
class SchemaRecord:
    name: str
    version: int
    schema: dict[str, Any]
    created_at: datetime


@dataclass
class SchemaSummary:
    name: str
    latest_version: int
    versions: int


@dataclass
class SchemaPromotion:
    name: str
    version: int
    environment: str
    promoted_at: datetime


@dataclass
class EntityRecord:
    id: str
    tenant_id: str
    schema_name: str
    schema_version: int
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SchemaExistsError(RuntimeError):
    pass


class DataServiceStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url, pool_pre_ping=True)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def readiness_probe_transaction(self) -> None:
        probe_id = "healthcheck-probe"
        payload = {"probe": "ok"}
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    CANONICAL_ENTITIES_TABLE.insert().values(
                        id=probe_id,
                        tenant_id="system",
                        schema_name="healthcheck",
                        schema_version=1,
                        payload=payload,
                    )
                )
                result = await session.execute(
                    select(CANONICAL_ENTITIES_TABLE.c.payload).where(
                        CANONICAL_ENTITIES_TABLE.c.id == probe_id
                    )
                )
                stored_payload = result.scalar_one()
                if stored_payload != payload:
                    raise RuntimeError("readiness probe payload mismatch")
                await session.execute(
                    delete(CANONICAL_ENTITIES_TABLE).where(
                        CANONICAL_ENTITIES_TABLE.c.id == probe_id
                    )
                )

    async def register_schema(
        self, name: str, schema: dict[str, Any], version: int | None = None
    ) -> SchemaRecord:
        async with self.session_factory() as session:
            async with session.begin():
                if version is None:
                    result = await session.execute(
                        select(func.max(SCHEMA_REGISTRY_TABLE.c.version)).where(
                            SCHEMA_REGISTRY_TABLE.c.name == name
                        )
                    )
                    current = result.scalar_one_or_none()
                    version = 1 if current is None else int(current) + 1
                existing = await session.execute(
                    select(SCHEMA_REGISTRY_TABLE.c.name).where(
                        SCHEMA_REGISTRY_TABLE.c.name == name,
                        SCHEMA_REGISTRY_TABLE.c.version == version,
                    )
                )
                if existing.first():
                    raise SchemaExistsError(f"Schema {name} version {version} already registered")
                try:
                    await session.execute(
                        SCHEMA_REGISTRY_TABLE.insert().values(
                            name=name,
                            version=version,
                            schema=schema,
                        )
                    )
                except IntegrityError as exc:
                    raise SchemaExistsError(
                        f"Schema {name} version {version} already registered"
                    ) from exc

            created_at = datetime.now(timezone.utc)
            return SchemaRecord(name=name, version=version, schema=schema, created_at=created_at)

    async def list_schema_summaries(self) -> list[SchemaSummary]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    SCHEMA_REGISTRY_TABLE.c.name,
                    func.max(SCHEMA_REGISTRY_TABLE.c.version).label("latest"),
                    func.count(SCHEMA_REGISTRY_TABLE.c.version).label("versions"),
                ).group_by(SCHEMA_REGISTRY_TABLE.c.name)
            )
            rows = result.fetchall()
        return [
            SchemaSummary(name=row.name, latest_version=row.latest, versions=row.versions)
            for row in rows
        ]

    async def list_schema_versions(self, name: str) -> list[SchemaRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SCHEMA_REGISTRY_TABLE)
                .where(SCHEMA_REGISTRY_TABLE.c.name == name)
                .order_by(SCHEMA_REGISTRY_TABLE.c.version.asc())
            )
            rows = result.fetchall()
        return [self._schema_from_row(row) for row in rows]

    async def list_schema_promotions(self, name: str) -> list[SchemaPromotion]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SCHEMA_PROMOTIONS_TABLE)
                .where(SCHEMA_PROMOTIONS_TABLE.c.name == name)
                .order_by(SCHEMA_PROMOTIONS_TABLE.c.promoted_at.desc())
            )
            rows = result.fetchall()
        return [self._promotion_from_row(row) for row in rows]

    async def promote_schema(self, name: str, version: int, environment: str) -> SchemaPromotion:
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    SCHEMA_PROMOTIONS_TABLE.insert().values(
                        name=name,
                        version=version,
                        environment=environment,
                    )
                )
        return SchemaPromotion(
            name=name,
            version=version,
            environment=environment,
            promoted_at=datetime.now(timezone.utc),
        )

    async def is_schema_promoted(self, name: str, version: int, environment: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SCHEMA_PROMOTIONS_TABLE.c.name).where(
                    SCHEMA_PROMOTIONS_TABLE.c.name == name,
                    SCHEMA_PROMOTIONS_TABLE.c.version == version,
                    SCHEMA_PROMOTIONS_TABLE.c.environment == environment,
                )
            )
        return result.first() is not None

    async def get_schema(self, name: str, version: int) -> SchemaRecord | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SCHEMA_REGISTRY_TABLE).where(
                    SCHEMA_REGISTRY_TABLE.c.name == name,
                    SCHEMA_REGISTRY_TABLE.c.version == version,
                )
            )
            row = result.first()
        return self._schema_from_row(row) if row else None

    async def get_latest_schema(self, name: str) -> SchemaRecord | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SCHEMA_REGISTRY_TABLE)
                .where(SCHEMA_REGISTRY_TABLE.c.name == name)
                .order_by(SCHEMA_REGISTRY_TABLE.c.version.desc())
                .limit(1)
            )
            row = result.first()
        return self._schema_from_row(row) if row else None

    async def store_entity(
        self,
        entity_id: str,
        tenant_id: str,
        schema_name: str,
        schema_version: int,
        payload: dict[str, Any],
    ) -> EntityRecord:
        async with self.session_factory() as session:
            async with session.begin():
                existing = await session.execute(
                    select(CANONICAL_ENTITIES_TABLE).where(
                        CANONICAL_ENTITIES_TABLE.c.id == entity_id
                    )
                )
                row = existing.first()
                timestamp = datetime.now(timezone.utc)
                if row:
                    await session.execute(
                        CANONICAL_ENTITIES_TABLE.update()
                        .where(CANONICAL_ENTITIES_TABLE.c.id == entity_id)
                        .values(
                            tenant_id=tenant_id,
                            schema_name=schema_name,
                            schema_version=schema_version,
                            payload=payload,
                            updated_at=timestamp,
                        )
                    )
                    created_at = row.created_at or timestamp
                else:
                    await session.execute(
                        CANONICAL_ENTITIES_TABLE.insert().values(
                            id=entity_id,
                            tenant_id=tenant_id,
                            schema_name=schema_name,
                            schema_version=schema_version,
                            payload=payload,
                        )
                    )
                    created_at = timestamp

        return EntityRecord(
            id=entity_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
            schema_version=schema_version,
            payload=payload,
            created_at=created_at,
            updated_at=timestamp,
        )

    async def get_entity(self, schema_name: str, entity_id: str) -> EntityRecord | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CANONICAL_ENTITIES_TABLE).where(
                    CANONICAL_ENTITIES_TABLE.c.schema_name == schema_name,
                    CANONICAL_ENTITIES_TABLE.c.id == entity_id,
                )
            )
            row = result.first()
        return self._entity_from_row(row) if row else None

    async def list_entities(
        self,
        schema_name: str,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EntityRecord]:
        async with self.session_factory() as session:
            statement = select(CANONICAL_ENTITIES_TABLE).where(
                CANONICAL_ENTITIES_TABLE.c.schema_name == schema_name
            )
            if tenant_id:
                statement = statement.where(CANONICAL_ENTITIES_TABLE.c.tenant_id == tenant_id)
            statement = (
                statement.order_by(CANONICAL_ENTITIES_TABLE.c.updated_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(statement)
            rows = result.fetchall()
        return [self._entity_from_row(row) for row in rows]

    async def count_entities(self, schema_name: str, tenant_id: str | None = None) -> int:
        async with self.session_factory() as session:
            statement = select(func.count(CANONICAL_ENTITIES_TABLE.c.id)).where(
                CANONICAL_ENTITIES_TABLE.c.schema_name == schema_name
            )
            if tenant_id:
                statement = statement.where(CANONICAL_ENTITIES_TABLE.c.tenant_id == tenant_id)
            result = await session.execute(statement)
        return int(result.scalar_one())

    async def prune_entities(self, older_than: datetime) -> int:
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(CANONICAL_ENTITIES_TABLE).where(
                        CANONICAL_ENTITIES_TABLE.c.updated_at < older_than
                    )
                )
        return int(result.rowcount or 0)

    async def seed_schemas(self, schema_dir: Path) -> int:
        if not schema_dir.exists():
            logger.warning("schema_directory_missing", extra={"path": str(schema_dir)})
            return 0
        count = 0
        for schema_path in sorted(schema_dir.glob("*.schema.json")):
            name = schema_path.name.replace(".schema.json", "")
            if await self.get_latest_schema(name):
                continue
            payload = __import__("json").loads(schema_path.read_text())
            await self.register_schema(name, payload, version=1)
            count += 1
        return count

    def _schema_from_row(self, row: Any) -> SchemaRecord:
        record = row[0] if isinstance(row, tuple) else row
        created_at = record.created_at
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        return SchemaRecord(
            name=record.name,
            version=record.version,
            schema=record.schema,
            created_at=created_at,
        )

    def _entity_from_row(self, row: Any) -> EntityRecord:
        record = row[0] if isinstance(row, tuple) else row
        created_at = record.created_at or datetime.now(timezone.utc)
        updated_at = record.updated_at or created_at
        return EntityRecord(
            id=record.id,
            tenant_id=record.tenant_id,
            schema_name=record.schema_name,
            schema_version=record.schema_version,
            payload=record.payload,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _promotion_from_row(self, row: Any) -> SchemaPromotion:
        record = row[0] if isinstance(row, tuple) else row
        promoted_at = record.promoted_at or datetime.now(timezone.utc)
        return SchemaPromotion(
            name=record.name,
            version=record.version,
            environment=record.environment,
            promoted_at=promoted_at,
        )


def to_async_database_url(database_url: str) -> str:
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
