"""Lifecycle governance persistence module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

class DocumentStore:
    def upsert(self, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def read(self, doc_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class InMemoryDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    def upsert(self, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {"id": doc_id, **data}
        self._docs[doc_id] = payload
        return payload

    def read(self, doc_id: str) -> dict[str, Any] | None:
        return self._docs.get(doc_id)


class CosmosDocumentStore(DocumentStore):
    def __init__(self, *, endpoint: str, key: str, database: str, container: str) -> None:
        if not endpoint or not key:
            raise ValueError("Cosmos DB endpoint and key required")
        from azure.cosmos import CosmosClient  # type: ignore

        self._client = CosmosClient(endpoint, credential=key)
        self._database = self._client.create_database_if_not_exists(database)
        self._container = self._database.create_container_if_not_exists(
            id=container,
            partition_key="/id",
        )

    def upsert(self, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {"id": doc_id, **data, "updated_at": datetime.now(timezone.utc).isoformat()}
        return self._container.upsert_item(payload)

    def read(self, doc_id: str) -> dict[str, Any] | None:
        try:
            return self._container.read_item(item=doc_id, partition_key=doc_id)
        except Exception:
            return None


@dataclass(slots=True)
class PersistenceConfig:
    cosmos_endpoint: str | None = None
    cosmos_key: str | None = None
    cosmos_database: str = "ppm"
    cosmos_container: str = "lifecycle_governance"


def _create_store(config: PersistenceConfig) -> DocumentStore:
    if config.cosmos_endpoint and config.cosmos_key:
        return CosmosDocumentStore(
            endpoint=config.cosmos_endpoint,
            key=config.cosmos_key,
            database=config.cosmos_database,
            container=config.cosmos_container,
        )
    return InMemoryDocumentStore()


@dataclass
class LifecyclePersistence:
    store: DocumentStore
    gate_history: list[dict[str, Any]] = field(default_factory=list)
    health_history: list[dict[str, Any]] = field(default_factory=list)
    methodology_history: list[dict[str, Any]] = field(default_factory=list)
    summaries: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "LifecyclePersistence":
        persistence_config = PersistenceConfig(
            cosmos_endpoint=(config or {}).get("cosmos_endpoint"),
            cosmos_key=(config or {}).get("cosmos_key"),
            cosmos_database=(config or {}).get("cosmos_database", "ppm"),
            cosmos_container=(config or {}).get("cosmos_container", "lifecycle_governance"),
        )
        return cls(store=_create_store(persistence_config))

    def store_gate_evaluation(
        self, tenant_id: str, project_id: str, evaluation: dict[str, Any]
    ) -> dict[str, Any]:
        record = self._build_record("gate_evaluation", tenant_id, project_id, evaluation)
        self.gate_history.append(record)
        self.store.upsert(record["id"], record)
        return record

    def store_health_metrics(
        self, tenant_id: str, project_id: str, health_data: dict[str, Any]
    ) -> dict[str, Any]:
        record = self._build_record("health_metric", tenant_id, project_id, health_data)
        self.health_history.append(record)
        self.store.upsert(record["id"], record)
        return record

    def store_methodology_decision(
        self, tenant_id: str, project_id: str, decision: dict[str, Any]
    ) -> dict[str, Any]:
        record = self._build_record("methodology_decision", tenant_id, project_id, decision)
        self.methodology_history.append(record)
        self.store.upsert(record["id"], record)
        return record

    def store_summary(
        self, tenant_id: str, project_id: str, summary: dict[str, Any]
    ) -> dict[str, Any]:
        record = self._build_record("gate_summary", tenant_id, project_id, summary)
        self.summaries.append(record)
        self.store.upsert(record["id"], record)
        return record

    def list_gate_outcomes(
        self, tenant_id: str, project_id: str, gate_name: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            record
            for record in self.gate_history
            if record["tenant_id"] == tenant_id
            and record["project_id"] == project_id
            and (gate_name is None or record["payload"].get("gate_name") == gate_name)
        ]

    def list_readiness_scores(self, tenant_id: str, project_id: str) -> list[dict[str, Any]]:
        return [
            {
                "gate_name": record["payload"].get("gate_name"),
                "readiness_score": record["payload"].get("readiness_score"),
                "evaluated_at": record["payload"].get("evaluated_at"),
            }
            for record in self.gate_history
            if record["tenant_id"] == tenant_id and record["project_id"] == project_id
        ]

    def list_health_metrics(self, tenant_id: str, project_id: str) -> list[dict[str, Any]]:
        return [
            record
            for record in self.health_history
            if record["tenant_id"] == tenant_id and record["project_id"] == project_id
        ]

    def _build_record(
        self, record_type: str, tenant_id: str, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        record_id = f"{record_type}:{project_id}:{timestamp}"
        return {
            "id": record_id,
            "record_type": record_type,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "payload": payload,
            "created_at": timestamp,
        }
