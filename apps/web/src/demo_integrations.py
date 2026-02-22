from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("demo_integrations")


def _json_response(payload: Any, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=payload)


class DemoOutbox:
    """File-backed outbox that captures demo write operations instead of calling
    external systems.  All demo publish / write paths must go through this
    outbox so that side effects are observable but never leave the demo
    sandbox."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, bucket: str, payload: dict[str, Any]) -> None:
        data = self._load()
        data.setdefault(bucket, []).append(payload)
        self._write(data)

    def read(self, bucket: str) -> list[dict[str, Any]]:
        return self._load().get(bucket, [])

    def write_bucket(self, bucket: str, values: list[dict[str, Any]]) -> None:
        data = self._load()
        data[bucket] = values
        self._write(data)

    def record_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit an audit event to the demo outbox so that demo publish/write
        operations are auditable without touching external audit stores."""
        event: dict[str, Any] = {
            "event_id": f"demo-audit-{uuid4().hex[:12]}",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "mode": "demo",
        }
        if metadata:
            event["metadata"] = metadata
        self.append("audit_events", event)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("demo_outbox_load_failed", extra={"path": str(self._path)})
            return {}

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class DemoDocumentServiceClient:
    def __init__(self, outbox: DemoOutbox) -> None:
        self._outbox = outbox

    async def create_document(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        doc_id = payload.get("document_id") or f"demo-doc-{uuid4()}"
        item = {
            "document_id": doc_id,
            "name": payload.get("name", "Untitled"),
            "content": payload.get("content", ""),
            "metadata": payload.get("metadata", {}),
            "tenant_id": headers.get("X-Tenant-ID", "demo-tenant"),
        }
        self._outbox.append("documents", item)
        self._outbox.record_audit_event(
            action="demo.document.created",
            resource_type="document",
            resource_id=doc_id,
            metadata={"name": item["name"]},
        )
        return _json_response(item, status_code=201)

    async def list_documents(self, headers: dict[str, str]) -> httpx.Response:
        tenant_id = headers.get("X-Tenant-ID", "demo-tenant")
        docs = [
            item for item in self._outbox.read("documents") if item.get("tenant_id") == tenant_id
        ]
        return _json_response(docs)

    async def get_document(self, document_id: str, headers: dict[str, str]) -> httpx.Response:
        tenant_id = headers.get("X-Tenant-ID", "demo-tenant")
        for item in self._outbox.read("documents"):
            if item.get("document_id") == document_id and item.get("tenant_id") == tenant_id:
                return _json_response(item)
        return _json_response({"detail": "Not found"}, status_code=404)


class DemoDataServiceClient:
    def __init__(self, outbox: DemoOutbox) -> None:
        self._outbox = outbox

    async def store_entity(
        self, schema_name: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        entity_id = f"demo-{schema_name}-{uuid4().hex[:8]}"
        entity = {
            "id": entity_id,
            "schema_name": schema_name,
            "tenant_id": payload.get("tenant_id") or headers.get("X-Tenant-ID", "demo-tenant"),
            "data": payload.get("data", {}),
        }
        self._outbox.append("entities", entity)
        self._outbox.record_audit_event(
            action="demo.entity.stored",
            resource_type=schema_name,
            resource_id=entity_id,
        )
        return _json_response(entity, status_code=201)


class DemoAnalyticsServiceClient:
    async def get_project_health(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return _json_response(
            {"project_id": project_id, "status": "green", "spi": 0.96, "cpi": 1.01}
        )

    async def get_project_trends(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return _json_response(
            {"project_id": project_id, "trend": [{"period": "2026-W05", "health": "green"}]}
        )

    async def request_what_if(
        self, project_id: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        return _json_response(
            {"project_id": project_id, "scenario": payload, "outcome": "demo-simulated"}
        )

    async def get_project_kpis(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return _json_response(
            {"project_id": project_id, "kpis": [{"label": "Burn", "value": "72%"}]}
        )

    async def get_project_narrative(
        self, project_id: str, headers: dict[str, str]
    ) -> httpx.Response:
        return _json_response({"project_id": project_id, "narrative": "Demo narrative."})

    async def get_project_aggregations(
        self, project_id: str, headers: dict[str, str]
    ) -> httpx.Response:
        return _json_response({"project_id": project_id, "aggregations": []})

    async def get_powerbi_report(self, report_type: str, headers: dict[str, str]) -> httpx.Response:
        return _json_response({"report_type": report_type, "url": "https://demo.local/report"})


class DemoConnectorHubClient:
    def __init__(self, outbox: DemoOutbox) -> None:
        self._outbox = outbox

    async def list_connectors(self, headers: dict[str, str]) -> httpx.Response:
        tenant_id = headers.get("X-Tenant-ID", "demo-tenant")
        items = [
            item for item in self._outbox.read("connectors") if item.get("tenant_id") == tenant_id
        ]
        return _json_response(items)

    async def create_connector(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        tenant_id = headers.get("X-Tenant-ID", "demo-tenant")
        connector_id = f"demo-connector-{uuid4().hex[:8]}"
        connector = {
            "connector_id": connector_id,
            "tenant_id": tenant_id,
            **payload,
            "status": "configured",
        }
        self._outbox.append("connectors", connector)
        self._outbox.record_audit_event(
            action="demo.connector.created",
            resource_type="connector",
            resource_id=connector_id,
        )
        return _json_response(connector, status_code=201)

    async def update_connector(
        self, connector_id: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        tenant_id = headers.get("X-Tenant-ID", "demo-tenant")
        connectors = self._outbox.read("connectors")
        for index, item in enumerate(connectors):
            if item.get("connector_id") == connector_id and item.get("tenant_id") == tenant_id:
                connectors[index] = {**item, **payload}
                self._outbox.write_bucket("connectors", connectors)
                self._outbox.append(
                    "connector_updates", {"connector_id": connector_id, "payload": payload}
                )
                return _json_response(connectors[index])
        return _json_response({"detail": "Not found"}, status_code=404)

    async def get_connector_health(
        self, connector_id: str, headers: dict[str, str]
    ) -> httpx.Response:
        return _json_response({"connector_id": connector_id, "healthy": True, "mode": "demo"})
