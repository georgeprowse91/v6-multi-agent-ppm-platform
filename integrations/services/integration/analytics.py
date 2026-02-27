"""Analytics integration utilities."""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,127}$")


def _validate_table_name(name: str) -> str:
    """Validate and return a safely quoted SQL table name, raising on invalid input."""
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid SQL table name: {name!r}. "
            "Table names must be alphanumeric/underscore and <= 128 chars."
        )
    # Double-quote the identifier to prevent any SQL injection even if the
    # regex were somehow bypassed.  Any embedded double-quotes are escaped.
    return f'"{name.replace(chr(34), chr(34) + chr(34))}"'


class AnalyticsSettings(BaseSettings):
    """Configuration for analytics providers."""

    model_config = SettingsConfigDict(env_prefix="ANALYTICS_", env_file=".env")

    provider: str = "in_memory"
    azure_monitor_connection_string: Optional[str] = None
    synapse_connection_string: Optional[str] = None
    synapse_table: str = "analytics_events"


@dataclass
class AnalyticsRecord:
    timestamp: datetime
    category: str
    name: str
    value: float
    metadata: Dict[str, Any]


class AnalyticsProvider:
    def record(self, record: AnalyticsRecord) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def list_records(self) -> List[AnalyticsRecord]:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryAnalyticsProvider(AnalyticsProvider):
    def __init__(self) -> None:
        self.records: List[AnalyticsRecord] = []

    def record(self, record: AnalyticsRecord) -> None:
        self.records.append(record)

    def list_records(self) -> List[AnalyticsRecord]:
        return list(self.records)


class SynapseAnalyticsProvider(AnalyticsProvider):
    def __init__(self, connection_string: str, table: str) -> None:
        from sqlalchemy import create_engine, text

        self._engine = create_engine(connection_string)
        self._table = _validate_table_name(table)
        self._ensure_table()
        self._insert_stmt = text(
            f"INSERT INTO {self._table} (timestamp, category, name, value, metadata) "
            "VALUES (:timestamp, :category, :name, :value, :metadata)"
        )

    def _ensure_table(self) -> None:
        from sqlalchemy import text

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            "timestamp TEXT, category TEXT, name TEXT, value REAL, metadata TEXT)"
        )
        with self._engine.begin() as conn:
            conn.execute(text(ddl))

    def record(self, record: AnalyticsRecord) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                self._insert_stmt,
                {
                    "timestamp": record.timestamp.isoformat(),
                    "category": record.category,
                    "name": record.name,
                    "value": record.value,
                    "metadata": str(record.metadata),
                },
            )

    def list_records(self) -> List[AnalyticsRecord]:
        logger.warning("Synapse analytics provider does not support listing records")
        return []


class AzureMonitorAnalyticsProvider(AnalyticsProvider):
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    def record(self, record: AnalyticsRecord) -> None:
        logger.info(
            "Azure Monitor analytics record",
            extra={
                "connection_string": self._connection_string,
                "record": record,
            },
        )

    def list_records(self) -> List[AnalyticsRecord]:
        logger.warning("Azure Monitor analytics provider does not support listing records")
        return []


class AnalyticsClient:
    """Unified client to log analytics and metrics."""

    def __init__(
        self,
        settings: Optional[AnalyticsSettings] = None,
        provider: Optional[AnalyticsProvider] = None,
    ) -> None:
        self.settings = settings or AnalyticsSettings()
        self.provider = provider or self._build_provider()

    def _build_provider(self) -> AnalyticsProvider:
        match self.settings.provider:
            case "synapse":
                if not self.settings.synapse_connection_string:
                    raise ValueError("Synapse connection string required")
                return SynapseAnalyticsProvider(
                    self.settings.synapse_connection_string, self.settings.synapse_table
                )
            case "azure_monitor":
                if not self.settings.azure_monitor_connection_string:
                    raise ValueError("Azure Monitor connection string required")
                return AzureMonitorAnalyticsProvider(self.settings.azure_monitor_connection_string)
            case _:
                return InMemoryAnalyticsProvider()

    def record_event(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._record("event", name, 1.0, metadata)

    def record_kpi(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._record("kpi", name, value, metadata)

    def record_health_metric(
        self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("health", name, value, metadata)

    def record_metric(
        self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("metric", name, value, metadata)

    def record_error_rate(
        self, name: str, error_rate: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("error_rate", name, error_rate, metadata)

    def record_defect_rate(
        self, name: str, defect_rate: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("defect_rate", name, defect_rate, metadata)

    def record_deployment_metric(
        self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("deployment", name, value, metadata)

    def record_anomaly_signal(
        self, name: str, score: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._record("anomaly", name, score, metadata)

    def list_records(
        self,
        *,
        category: Optional[str] = None,
        name_prefix: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[AnalyticsRecord]:
        records = self.provider.list_records()
        filtered: List[AnalyticsRecord] = []
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        for record in records:
            if category and record.category != category:
                continue
            if name_prefix and not record.name.startswith(name_prefix):
                continue
            if since and record.timestamp < since:
                continue
            filtered.append(record)
        return filtered

    def detect_anomaly(self, series: Iterable[float], threshold: float = 2.5) -> bool:
        values = list(series)
        if len(values) < 2:
            return False
        mean = statistics.mean(values)
        std_dev = statistics.pstdev(values)
        if std_dev == 0:
            return False
        z_score = (values[-1] - mean) / std_dev
        return abs(z_score) >= threshold

    def _record(
        self, category: str, name: str, value: float, metadata: Optional[Dict[str, Any]]
    ) -> None:
        record = AnalyticsRecord(
            timestamp=datetime.now(timezone.utc),
            category=category,
            name=name,
            value=value,
            metadata=metadata or {},
        )
        self.provider.record(record)


__all__ = [
    "AnalyticsSettings",
    "AnalyticsClient",
    "AnalyticsProvider",
    "AnalyticsRecord",
    "InMemoryAnalyticsProvider",
]
