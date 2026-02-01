"""Persistence helpers for SQL and Cosmos DB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class SqlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SQL_", env_file=".env")

    connection_string: str = "sqlite+pysqlite:///:memory:"


class CosmosSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COSMOS_", env_file=".env")

    endpoint: Optional[str] = None
    key: Optional[str] = None
    database: str = "ppm"
    container: str = "ppm_documents"


class PersistenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PERSISTENCE_", env_file=".env")

    sql_connection_string: str = "sqlite+pysqlite:///:memory:"
    cosmos_endpoint: Optional[str] = None
    cosmos_key: Optional[str] = None
    cosmos_database: str = "ppm"
    cosmos_container: str = "ppm_documents"


class Base(DeclarativeBase):
    pass


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskRecord(Base):
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(50))
    mitigation_plan: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResourceRecord(Base):
    __tablename__ = "resource_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_name: Mapped[str] = mapped_column(String(255))
    allocation: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


@dataclass
class SqlRepository:
    session: Session

    def add_schedule(self, name: str, status: str = "draft") -> Schedule:
        schedule = Schedule(name=name, status=status)
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def add_risk(self, title: str, severity: str, mitigation_plan: str) -> RiskRecord:
        risk = RiskRecord(title=title, severity=severity, mitigation_plan=mitigation_plan)
        self.session.add(risk)
        self.session.commit()
        self.session.refresh(risk)
        return risk


class DocumentStore:
    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def read(self, doc_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class InMemoryDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": doc_id, **data}
        self._docs[doc_id] = payload
        return payload

    def read(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._docs.get(doc_id)


class CosmosDocumentStore(DocumentStore):
    def __init__(self, settings: CosmosSettings) -> None:
        if not settings.endpoint or not settings.key:
            raise ValueError("Cosmos DB endpoint and key required")
        try:
            from azure.cosmos import CosmosClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("azure-cosmos is required for CosmosDB provider") from exc

        self._client = CosmosClient(settings.endpoint, credential=settings.key)
        self._database = self._client.create_database_if_not_exists(settings.database)
        self._container = self._database.create_container_if_not_exists(
            id=settings.container,
            partition_key="/id",
        )

    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": doc_id, **data, "updated_at": datetime.now(timezone.utc).isoformat()}
        return self._container.upsert_item(payload)

    def read(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._container.read_item(item=doc_id, partition_key=doc_id)
        except Exception:
            return None


def create_sql_engine(connection_string: str) -> Any:
    return create_engine(connection_string)


__all__ = [
    "SqlSettings",
    "CosmosSettings",
    "PersistenceSettings",
    "Base",
    "Schedule",
    "RiskRecord",
    "QualityMetric",
    "ResourceRecord",
    "SqlRepository",
    "DocumentStore",
    "InMemoryDocumentStore",
    "CosmosDocumentStore",
    "create_sql_engine",
]
