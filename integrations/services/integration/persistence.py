"""Persistence helpers for SQL and Cosmos DB."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, Float, Integer, String, create_engine, select
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
    schedule_key: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    project_id: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, index=True)
    task_key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    duration_days: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskDependencyRecord(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, index=True)
    predecessor_task_key: Mapped[str] = mapped_column(String(100))
    successor_task_key: Mapped[str] = mapped_column(String(100))
    dependency_type: Mapped[str] = mapped_column(String(10), default="FS")
    lag_days: Mapped[float] = mapped_column(Float, default=0.0)
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


class ResourceAllocationRecord(Base):
    __tablename__ = "resource_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, index=True)
    task_key: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(120))
    skill: Mapped[str] = mapped_column(String(120), default="")
    units: Mapped[float] = mapped_column(Float, default=1.0)
    performance_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScheduleSimulationRecord(Base):
    __tablename__ = "schedule_simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, index=True)
    iterations: Mapped[int] = mapped_column(Integer)
    p50_duration: Mapped[float] = mapped_column(Float)
    p80_duration: Mapped[float] = mapped_column(Float)
    p90_duration: Mapped[float] = mapped_column(Float)
    p95_duration: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    distribution_json: Mapped[str] = mapped_column(String(2000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EarnedValueRecord(Base):
    __tablename__ = "earned_value_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, index=True)
    planned_value: Mapped[float] = mapped_column(Float)
    earned_value: Mapped[float] = mapped_column(Float)
    actual_cost: Mapped[float] = mapped_column(Float)
    spi: Mapped[float] = mapped_column(Float)
    cpi: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_type: Mapped[str] = mapped_column(String(120))
    reference: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="collected")
    details: Mapped[str] = mapped_column(String(1000), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessLog(Base):
    __tablename__ = "process_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(1000))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


@dataclass
class SqlRepository:
    session: Session
    _memory_schedules: ClassVar[dict[str, Schedule]] = {}
    _memory_tasks: ClassVar[list[TaskRecord]] = []
    _memory_dependencies: ClassVar[list[TaskDependencyRecord]] = []
    _memory_allocations: ClassVar[list[ResourceAllocationRecord]] = []
    _memory_simulations: ClassVar[list[ScheduleSimulationRecord]] = []
    _memory_earned_values: ClassVar[list[EarnedValueRecord]] = []

    def _build(self, model_cls: type[Base], **fields: Any) -> Base:
        record = model_cls()
        for key, value in fields.items():
            setattr(record, key, value)
        return record

    def _use_memory_store(self) -> bool:
        return not hasattr(self.session, "execute")

    def _ensure_memory_store(self) -> None:
        return None

    def upsert_schedule(
        self,
        schedule_key: str,
        name: str,
        status: str = "draft",
        project_id: str = "",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Schedule:
        if self._use_memory_store():
            self._ensure_memory_store()
            existing = self._memory_schedules.get(schedule_key)
        else:
            existing = self.session.execute(
                select(Schedule).where(Schedule.schedule_key == schedule_key)
            ).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.status = status
            existing.project_id = project_id
            existing.start_date = start_date
            existing.end_date = end_date
            schedule = existing
        else:
            schedule = self._build(
                Schedule,
                schedule_key=schedule_key,
                name=name,
                status=status,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
            )
            if self._use_memory_store():
                self._memory_schedules[schedule_key] = schedule  # type: ignore[index]
            else:
                self.session.add(schedule)
        if not self._use_memory_store():
            self.session.commit()
            self.session.refresh(schedule)
        return schedule

    def add_task(
        self,
        schedule_id: int,
        task_key: str,
        name: str,
        duration_days: float,
        status: str = "planned",
    ) -> TaskRecord:
        task = self._build(
            TaskRecord,
            schedule_id=schedule_id,
            task_key=task_key,
            name=name,
            duration_days=duration_days,
            status=status,
        )
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_tasks.append(task)  # type: ignore[union-attr]
        else:
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        return task

    def add_dependency(
        self,
        schedule_id: int,
        predecessor_task_key: str,
        successor_task_key: str,
        dependency_type: str = "FS",
        lag_days: float = 0.0,
    ) -> TaskDependencyRecord:
        dependency = self._build(
            TaskDependencyRecord,
            schedule_id=schedule_id,
            predecessor_task_key=predecessor_task_key,
            successor_task_key=successor_task_key,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_dependencies.append(dependency)  # type: ignore[union-attr]
        else:
            self.session.add(dependency)
            self.session.commit()
            self.session.refresh(dependency)
        return dependency

    def add_risk(self, title: str, severity: str, mitigation_plan: str) -> RiskRecord:
        risk = self._build(RiskRecord, title=title, severity=severity, mitigation_plan=mitigation_plan)
        self.session.add(risk)
        self.session.commit()
        self.session.refresh(risk)
        return risk

    def add_quality_metric(self, name: str, value: float) -> QualityMetric:
        metric = self._build(QualityMetric, name=name, value=value)
        self.session.add(metric)
        self.session.commit()
        self.session.refresh(metric)
        return metric

    def add_resource_record(self, resource_name: str, allocation: float) -> ResourceRecord:
        resource = self._build(ResourceRecord, resource_name=resource_name, allocation=allocation)
        if not self._use_memory_store():
            self.session.add(resource)
            self.session.commit()
            self.session.refresh(resource)
        return resource

    def add_resource_allocation(
        self,
        schedule_id: int,
        task_key: str,
        resource_id: str,
        skill: str,
        units: float,
        performance_score: float,
    ) -> ResourceAllocationRecord:
        allocation = self._build(
            ResourceAllocationRecord,
            schedule_id=schedule_id,
            task_key=task_key,
            resource_id=resource_id,
            skill=skill,
            units=units,
            performance_score=performance_score,
        )
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_allocations.append(allocation)  # type: ignore[union-attr]
        else:
            self.session.add(allocation)
            self.session.commit()
            self.session.refresh(allocation)
        return allocation

    def add_simulation_record(
        self,
        schedule_id: int,
        iterations: int,
        p50: float,
        p80: float,
        p90: float,
        p95: float,
        risk_score: float,
        distribution: Dict[str, Any],
    ) -> ScheduleSimulationRecord:
        record = self._build(
            ScheduleSimulationRecord,
            schedule_id=schedule_id,
            iterations=iterations,
            p50_duration=p50,
            p80_duration=p80,
            p90_duration=p90,
            p95_duration=p95,
            risk_score=risk_score,
            distribution_json=json.dumps(distribution),
        )
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_simulations.append(record)  # type: ignore[union-attr]
        else:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
        return record

    def add_earned_value_record(
        self,
        schedule_id: int,
        planned_value: float,
        earned_value: float,
        actual_cost: float,
        spi: float,
        cpi: float,
    ) -> EarnedValueRecord:
        record = self._build(
            EarnedValueRecord,
            schedule_id=schedule_id,
            planned_value=planned_value,
            earned_value=earned_value,
            actual_cost=actual_cost,
            spi=spi,
            cpi=cpi,
        )
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_earned_values.append(record)  # type: ignore[union-attr]
        else:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
        return record

    def get_schedule_by_key(self, schedule_key: str) -> Optional[Schedule]:
        if self._use_memory_store():
            self._ensure_memory_store()
            return self._memory_schedules.get(schedule_key)  # type: ignore[return-value]
        return self.session.execute(
            select(Schedule).where(Schedule.schedule_key == schedule_key)
        ).scalar_one_or_none()

    def get_tasks(self, schedule_id: int) -> list[TaskRecord]:
        if self._use_memory_store():
            self._ensure_memory_store()
            return [
                task for task in self._memory_tasks if task.schedule_id == schedule_id  # type: ignore[union-attr]
            ]
        return list(
            self.session.execute(
                select(TaskRecord).where(TaskRecord.schedule_id == schedule_id)
            ).scalars()
        )

    def get_dependencies(self, schedule_id: int) -> list[TaskDependencyRecord]:
        if self._use_memory_store():
            self._ensure_memory_store()
            return [
                dep
                for dep in self._memory_dependencies  # type: ignore[union-attr]
                if dep.schedule_id == schedule_id
            ]
        return list(
            self.session.execute(
                select(TaskDependencyRecord).where(
                    TaskDependencyRecord.schedule_id == schedule_id
                )
            ).scalars()
        )

    def get_resource_allocations(self, schedule_id: int) -> list[ResourceAllocationRecord]:
        if self._use_memory_store():
            self._ensure_memory_store()
            return [
                allocation
                for allocation in self._memory_allocations  # type: ignore[union-attr]
                if allocation.schedule_id == schedule_id
            ]
        return list(
            self.session.execute(
                select(ResourceAllocationRecord).where(
                    ResourceAllocationRecord.schedule_id == schedule_id
                )
            ).scalars()
        )

    def clear_schedule_children(self, schedule_id: int) -> None:
        if self._use_memory_store():
            self._ensure_memory_store()
            self._memory_tasks = [  # type: ignore[assignment]
                task for task in self._memory_tasks if task.schedule_id != schedule_id  # type: ignore[union-attr]
            ]
            self._memory_dependencies = [  # type: ignore[assignment]
                dep for dep in self._memory_dependencies if dep.schedule_id != schedule_id  # type: ignore[union-attr]
            ]
            self._memory_allocations = [  # type: ignore[assignment]
                allocation
                for allocation in self._memory_allocations  # type: ignore[union-attr]
                if allocation.schedule_id != schedule_id
            ]
            return
        self.session.query(TaskDependencyRecord).filter(TaskDependencyRecord.schedule_id == schedule_id).delete()
        self.session.query(TaskRecord).filter(TaskRecord.schedule_id == schedule_id).delete()
        self.session.query(ResourceAllocationRecord).filter(ResourceAllocationRecord.schedule_id == schedule_id).delete()
        self.session.commit()

    def add_compliance_evidence(
        self, evidence_type: str, reference: str, status: str, details: str
    ) -> ComplianceEvidence:
        evidence = self._build(
            ComplianceEvidence,
            evidence_type=evidence_type,
            reference=reference,
            status=status,
            details=details,
        )
        self.session.add(evidence)
        self.session.commit()
        self.session.refresh(evidence)
        return evidence

    def add_process_log(self, process_name: str, status: str, message: str) -> ProcessLog:
        log = self._build(ProcessLog, process_name=process_name, status=status, message=message)
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log


class DocumentStore(ABC):
    @abstractmethod
    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def read(self, doc_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CACHE_", env_file=".env")

    provider: str = "in_memory"
    redis_url: Optional[str] = None
    default_ttl_seconds: int = 600


class CacheProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:  # pragma: no cover
        raise NotImplementedError


class InMemoryCacheProvider(CacheProvider):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        self._store[key] = value


class RedisCacheProvider(CacheProvider):
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raw = self._client.get(key)
        if not raw:
            return None
        return json.loads(raw)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, json.dumps(value))


class CacheClient:
    def __init__(self, settings: Optional[CacheSettings] = None) -> None:
        self.settings = settings or CacheSettings()
        self.provider = self._build_provider()

    def _build_provider(self) -> CacheProvider:
        if self.settings.provider == "redis":
            if not self.settings.redis_url:
                raise ValueError("Redis URL required for redis cache provider")
            return RedisCacheProvider(self.settings.redis_url)
        return InMemoryCacheProvider()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.provider.get(key)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds or self.settings.default_ttl_seconds
        self.provider.set(key, value, ttl)


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
            from azure.cosmos.exceptions import CosmosHttpResponseError  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            CosmosHttpResponseError = RuntimeError
        try:
            return self._container.read_item(item=doc_id, partition_key=doc_id)
        except (CosmosHttpResponseError, KeyError, ValueError):
            return None


def create_sql_engine(connection_string: str) -> Any:
    return create_engine(connection_string)


def run_migrations(engine: Any) -> None:
    Base.metadata.create_all(engine)


__all__ = [
    "SqlSettings",
    "CosmosSettings",
    "PersistenceSettings",
    "Base",
    "Schedule",
    "TaskRecord",
    "TaskDependencyRecord",
    "RiskRecord",
    "QualityMetric",
    "ResourceRecord",
    "ResourceAllocationRecord",
    "ScheduleSimulationRecord",
    "EarnedValueRecord",
    "ComplianceEvidence",
    "ProcessLog",
    "SqlRepository",
    "DocumentStore",
    "InMemoryDocumentStore",
    "CosmosDocumentStore",
    "create_sql_engine",
    "run_migrations",
    "CacheSettings",
    "CacheClient",
    "CacheProvider",
    "InMemoryCacheProvider",
    "RedisCacheProvider",
]
