from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthContext, AuthTenantMiddleware  # noqa: E402
from security.lineage import mask_lineage_payload  # noqa: E402
from quality import QualityResult, compute_quality  # noqa: E402
from storage import LineageRecord, LineageStore  # noqa: E402

logger = logging.getLogger("data-lineage-service")
logging.basicConfig(level=logging.INFO)

DEFAULT_STORE_PATH = "services/data-lineage-service/storage/lineage.json"
DEFAULT_RETENTION_CONFIG = "config/retention/policies.yaml"
DEFAULT_CLASSIFICATION_CONFIG = "config/data-classification/levels.yaml"
DEFAULT_RULES_PATH = "data/quality/rules.yaml"


@dataclass
class RetentionPolicy:
    policy_id: str
    duration_days: int


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "data-lineage-service"


class QualityPayload(BaseModel):
    score: float
    dimensions: dict[str, float] | None = None
    rules_checked: list[str] | None = None
    issues: list[dict[str, Any]] | None = None
    computed_at: str | None = None


class LineageEventIn(BaseModel):
    tenant_id: str
    connector: str
    source: dict[str, Any]
    target: dict[str, Any]
    transformations: list[str] = Field(default_factory=list)
    entity_type: str | None = None
    entity_payload: dict[str, Any] | None = None
    quality: QualityPayload | None = None
    classification: str = "internal"
    metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None


class LineageEventOut(BaseModel):
    lineage_id: str
    tenant_id: str
    connector: str
    source: dict[str, Any]
    target: dict[str, Any]
    transformations: list[str]
    entity_type: str | None = None
    entity_payload: dict[str, Any] | None = None
    quality: QualityPayload | None = None
    classification: str
    metadata: dict[str, Any] | None = None
    timestamp: datetime


class LineageGraphNode(BaseModel):
    id: str
    label: str
    node_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageGraphEdge(BaseModel):
    source: str
    target: str
    lineage_id: str
    timestamp: datetime
    quality_score: float | None = None


class LineageGraphResponse(BaseModel):
    nodes: list[LineageGraphNode]
    edges: list[LineageGraphEdge]


class QualitySummaryResponse(BaseModel):
    average_score: float
    total_events: int
    by_entity: dict[str, float]


app = FastAPI(title="Data Lineage Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("data-lineage-service")
configure_metrics("data-lineage-service")
app.add_middleware(TraceMiddleware, service_name="data-lineage-service")
app.add_middleware(RequestMetricsMiddleware, service_name="data-lineage-service")


@app.on_event("startup")
async def startup() -> None:
    store_path = Path(os.getenv("DATA_LINEAGE_STORE_PATH", DEFAULT_STORE_PATH))
    app.state.store = LineageStore(store_path)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def get_store() -> LineageStore:
    return app.state.store


def _load_rules() -> dict[str, Any]:
    rules_path = Path(os.getenv("DATA_LINEAGE_RULES_PATH", DEFAULT_RULES_PATH))
    return yaml.safe_load(rules_path.read_text())


def _load_classification_config() -> dict[str, Any]:
    path = Path(os.getenv("DATA_LINEAGE_CLASSIFICATION_LEVELS", DEFAULT_CLASSIFICATION_CONFIG))
    return yaml.safe_load(path.read_text())


def _load_retention_config() -> dict[str, Any]:
    path = Path(os.getenv("DATA_LINEAGE_RETENTION_POLICIES", DEFAULT_RETENTION_CONFIG))
    return yaml.safe_load(path.read_text())


def _retention_policy(classification: str) -> RetentionPolicy:
    retention_cfg = _load_retention_config()
    classification_cfg = _load_classification_config()
    policy_id = next(
        (
            level.get("retention_policy")
            for level in classification_cfg.get("levels", [])
            if level["id"] == classification
        ),
        None,
    )
    if not policy_id:
        raise HTTPException(status_code=400, detail="Retention policy not configured")
    policy = next((p for p in retention_cfg.get("policies", []) if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=400, detail="Retention policy not found")
    return RetentionPolicy(policy_id=policy["id"], duration_days=policy["duration_days"])


def _allowed_roles(classification: str) -> list[str]:
    classification_cfg = _load_classification_config()
    level = next(
        (level for level in classification_cfg.get("levels", []) if level["id"] == classification),
        None,
    )
    if not level:
        raise HTTPException(status_code=400, detail="Classification level not configured")
    return list(level.get("allowed_roles", []))


def _ensure_access(auth: AuthContext, classification: str) -> None:
    allowed = set(_allowed_roles(classification))
    if allowed and not (allowed.intersection(set(auth.roles))):
        raise HTTPException(status_code=403, detail="Access denied for classification")


def _record_to_response(record: LineageRecord) -> LineageEventOut:
    return LineageEventOut(
        lineage_id=record.lineage_id,
        tenant_id=record.tenant_id,
        connector=record.connector,
        source=record.source,
        target=record.target,
        transformations=record.transformations,
        entity_type=record.entity_type,
        entity_payload=record.entity_payload,
        quality=QualityPayload(**record.quality) if record.quality else None,
        classification=record.classification,
        metadata=record.metadata,
        timestamp=datetime.fromisoformat(record.timestamp),
    )


def _mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not os.getenv("LINEAGE_MASK_SALT"):
        return payload
    return mask_lineage_payload(payload)


@app.post("/lineage/events", response_model=LineageEventOut)
async def ingest_event(
    payload: LineageEventIn,
    request: Request,
    store: LineageStore = Depends(get_store),
) -> LineageEventOut:
    auth = request.state.auth
    if payload.tenant_id != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    _ensure_access(auth, payload.classification)

    timestamp = payload.timestamp or datetime.now(timezone.utc)
    lineage_id = f"lin-{uuid4().hex}"
    entity_type = payload.entity_type or payload.target.get("schema") or payload.target.get("entity")

    quality_result: QualityResult | None = None
    if payload.quality:
        quality_result = QualityResult(
            score=payload.quality.score,
            dimensions=payload.quality.dimensions or {},
            rules_checked=payload.quality.rules_checked or [],
            issues=payload.quality.issues or [],
            computed_at=payload.quality.computed_at or datetime.utcnow().isoformat(),
        )
    elif entity_type and payload.entity_payload:
        quality_result = compute_quality(
            entity_type=entity_type,
            entity_payload=payload.entity_payload,
            rules_config=_load_rules(),
        )

    retention = _retention_policy(payload.classification)
    retention_until = (timestamp + timedelta(days=retention.duration_days)).isoformat()

    record_payload = {
        "lineage_id": lineage_id,
        "tenant_id": payload.tenant_id,
        "connector": payload.connector,
        "source": payload.source,
        "target": payload.target,
        "transformations": payload.transformations,
        "entity_type": entity_type,
        "entity_payload": payload.entity_payload,
        "quality": quality_result.__dict__ if quality_result else None,
        "classification": payload.classification,
        "metadata": payload.metadata,
        "timestamp": timestamp.isoformat(),
        "retention_until": retention_until,
    }

    masked_payload = _mask_payload(record_payload)
    store.upsert(LineageRecord(**masked_payload))
    logger.info("lineage_event_ingested", extra={"lineage_id": lineage_id})
    return _record_to_response(store.get(payload.tenant_id, lineage_id))


@app.get("/lineage/events", response_model=list[LineageEventOut])
async def list_events(request: Request, store: LineageStore = Depends(get_store)) -> list[LineageEventOut]:
    auth = request.state.auth
    records = store.list(auth.tenant_id)
    visible = []
    for record in records:
        try:
            _ensure_access(auth, record.classification)
        except HTTPException:
            continue
        visible.append(_record_to_response(record))
    return visible


@app.get("/lineage/events/{lineage_id}", response_model=LineageEventOut)
async def get_event(
    lineage_id: str, request: Request, store: LineageStore = Depends(get_store)
) -> LineageEventOut:
    auth = request.state.auth
    record = store.get(auth.tenant_id, lineage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lineage event not found")
    _ensure_access(auth, record.classification)
    return _record_to_response(record)


@app.get("/lineage/graph", response_model=LineageGraphResponse)
async def get_graph(request: Request, store: LineageStore = Depends(get_store)) -> LineageGraphResponse:
    auth = request.state.auth
    records = store.list(auth.tenant_id)
    nodes: dict[str, LineageGraphNode] = {}
    edges: list[LineageGraphEdge] = []

    for record in records:
        try:
            _ensure_access(auth, record.classification)
        except HTTPException:
            continue
        source_id = f"source:{record.source.get('system')}:{record.source.get('object')}:{record.source.get('record_id')}"
        target_id = f"target:{record.target.get('schema')}:{record.target.get('record_id')}"
        if source_id not in nodes:
            nodes[source_id] = LineageGraphNode(
                id=source_id,
                label=str(record.source.get("object") or "source"),
                node_type="source",
                metadata=record.source,
            )
        if target_id not in nodes:
            nodes[target_id] = LineageGraphNode(
                id=target_id,
                label=str(record.target.get("schema") or "target"),
                node_type="target",
                metadata=record.target,
            )
        edges.append(
            LineageGraphEdge(
                source=source_id,
                target=target_id,
                lineage_id=record.lineage_id,
                timestamp=datetime.fromisoformat(record.timestamp),
                quality_score=record.quality.get("score") if record.quality else None,
            )
        )

    return LineageGraphResponse(nodes=list(nodes.values()), edges=edges)


@app.get("/quality/summary", response_model=QualitySummaryResponse)
async def get_quality_summary(
    request: Request, store: LineageStore = Depends(get_store)
) -> QualitySummaryResponse:
    auth = request.state.auth
    records = [record for record in store.list(auth.tenant_id) if record.quality]
    filtered: list[LineageRecord] = []
    for record in records:
        try:
            _ensure_access(auth, record.classification)
        except HTTPException:
            continue
        filtered.append(record)

    total_events = len(filtered)
    if total_events == 0:
        return QualitySummaryResponse(average_score=0.0, total_events=0, by_entity={})

    total_score = 0.0
    by_entity_totals: dict[str, list[float]] = {}
    for record in filtered:
        score = float(record.quality.get("score", 0.0)) if record.quality else 0.0
        total_score += score
        entity_type = record.entity_type or "unknown"
        by_entity_totals.setdefault(entity_type, []).append(score)

    by_entity = {
        entity: round(sum(scores) / len(scores), 4) for entity, scores in by_entity_totals.items()
    }
    average_score = round(total_score / total_events, 4)
    return QualitySummaryResponse(
        average_score=average_score,
        total_events=total_events,
        by_entity=by_entity,
    )
