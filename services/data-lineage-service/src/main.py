from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlite3 import Error as SqliteError

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
DATA_QUALITY_ROOT = REPO_ROOT / "packages" / "data-quality" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT, DATA_QUALITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from packages.version import API_VERSION  # noqa: E402
from data_quality.remediation import RemediationResult, remediate_payload  # noqa: E402
from data_quality.rules import evaluate_quality_rules  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from quality import QualityResult, compute_quality  # noqa: E402
from retention_scheduler import RetentionScheduler  # noqa: E402
from security.auth import AuthContext, AuthTenantMiddleware  # noqa: E402
from security.config import load_yaml  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402
from security.lineage import mask_lineage_payload  # noqa: E402
from storage import LineageRecord, LineageStore  # noqa: E402

logger = logging.getLogger("data-lineage-service")
logging.basicConfig(level=logging.INFO)

DEFAULT_STORE_PATH = "services/data-lineage-service/storage/lineage.db"
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
    dependencies: dict[str, str] = Field(default_factory=dict)


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


class QualityRemediationRequest(BaseModel):
    record_type: str
    record: dict[str, Any]
    apply_fixes: bool = True


class QualityRemediationResponse(BaseModel):
    record_type: str
    record_id: str | None
    remediated: bool
    actions: list[dict[str, Any]]
    original_payload: dict[str, Any]
    remediated_payload: dict[str, Any]
    quality: QualityPayload | None = None


class RetentionStatusResponse(BaseModel):
    interval_seconds: int
    last_pruned_at: str | None
    last_pruned_count: int


app = FastAPI(title="Data Lineage Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
app.add_middleware(SecurityHeadersMiddleware)
configure_tracing("data-lineage-service")
configure_metrics("data-lineage-service")
app.add_middleware(TraceMiddleware, service_name="data-lineage-service")
app.add_middleware(RequestMetricsMiddleware, service_name="data-lineage-service")
register_error_handlers(app)


@app.on_event("startup")
async def startup() -> None:
    store_path = Path(os.getenv("DATA_LINEAGE_STORE_PATH", DEFAULT_STORE_PATH))
    app.state.store = LineageStore(store_path)
    interval = int(os.getenv("DATA_LINEAGE_RETENTION_INTERVAL_SECONDS", "3600"))
    scheduler = RetentionScheduler(app.state.store, interval_seconds=interval)
    scheduler.start()
    app.state.retention_scheduler = scheduler


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler = getattr(app.state, "retention_scheduler", None)
    if scheduler:
        scheduler.stop()


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    store = get_store()
    scheduler = getattr(app.state, "retention_scheduler", None)
    dependencies = {"store": "unknown", "retention_scheduler": "unknown"}
    try:
        store.ping()
        dependencies["store"] = "ok"
    except SqliteError:
        dependencies["store"] = "down"
    dependencies["retention_scheduler"] = "ok" if scheduler else "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "data-lineage-service",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


def get_store() -> LineageStore:
    return app.state.store


def _get_retention_scheduler(request: Request) -> RetentionScheduler | None:
    return getattr(request.app.state, "retention_scheduler", None)


def _load_rules() -> dict[str, Any]:
    rules_path = Path(os.getenv("DATA_LINEAGE_RULES_PATH", DEFAULT_RULES_PATH))
    return load_yaml(rules_path)


def _load_classification_config() -> dict[str, Any]:
    path = Path(os.getenv("DATA_LINEAGE_CLASSIFICATION_LEVELS", DEFAULT_CLASSIFICATION_CONFIG))
    return load_yaml(path)


def _load_retention_config() -> dict[str, Any]:
    path = Path(os.getenv("DATA_LINEAGE_RETENTION_POLICIES", DEFAULT_RETENTION_CONFIG))
    return load_yaml(path)


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


def _remediation_response(
    result: RemediationResult, quality: QualityResult | None
) -> QualityRemediationResponse:
    return QualityRemediationResponse(
        record_type=result.record_type,
        record_id=result.record_id,
        remediated=bool(result.actions),
        actions=[action.__dict__ for action in result.actions],
        original_payload=result.original_payload,
        remediated_payload=result.remediated_payload,
        quality=QualityPayload(**quality.__dict__) if quality else None,
    )


def _paginate(items: list[Any], *, offset: int, limit: int) -> tuple[list[Any], int]:
    total = len(items)
    return items[offset : offset + limit], total


def _extract_work_item_id(target: dict[str, Any]) -> str | None:
    entity = (target.get("schema") or target.get("entity") or target.get("object") or "").lower()
    if entity in {"work-item", "work_item", "workitem", "work items"}:
        return target.get("record_id") or target.get("id")
    return None


def _mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not os.getenv("LINEAGE_MASK_SALT"):
        return payload
    return mask_lineage_payload(payload)


@api_router.post("/lineage/events", response_model=LineageEventOut)
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
    entity_type = (
        payload.entity_type or payload.target.get("schema") or payload.target.get("entity")
    )

    quality_result: QualityResult | None = None
    if payload.quality:
        quality_result = QualityResult(
            score=payload.quality.score,
            dimensions=payload.quality.dimensions or {},
            rules_checked=payload.quality.rules_checked or [],
            issues=payload.quality.issues or [],
            computed_at=payload.quality.computed_at or datetime.now(timezone.utc).isoformat(),
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
        "work_item_id": _extract_work_item_id(payload.target),
    }

    masked_payload = _mask_payload(record_payload)
    store.upsert(LineageRecord(**masked_payload))
    logger.info("lineage_event_ingested", extra={"lineage_id": lineage_id})
    return _record_to_response(store.get(payload.tenant_id, lineage_id))


@api_router.get("/lineage/events", response_model=list[LineageEventOut])
async def list_events(
    request: Request,
    connector_id: str | None = None,
    work_item_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    response: Response,
    store: LineageStore = Depends(get_store),
) -> list[LineageEventOut]:
    auth = request.state.auth
    records = store.list(auth.tenant_id, connector_id=connector_id, work_item_id=work_item_id)
    visible = []
    for record in records:
        try:
            _ensure_access(auth, record.classification)
        except HTTPException:
            continue
        visible.append(_record_to_response(record))
    sliced, total = _paginate(visible, offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.get("/lineage/events/{lineage_id}", response_model=LineageEventOut)
async def get_event(
    lineage_id: str, request: Request, store: LineageStore = Depends(get_store)
) -> LineageEventOut:
    auth = request.state.auth
    record = store.get(auth.tenant_id, lineage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lineage event not found")
    _ensure_access(auth, record.classification)
    return _record_to_response(record)


@api_router.get("/lineage/graph", response_model=LineageGraphResponse)
async def get_graph(
    request: Request, store: LineageStore = Depends(get_store)
) -> LineageGraphResponse:
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


@api_router.get("/quality/summary", response_model=QualitySummaryResponse)
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


@api_router.post("/quality/remediate", response_model=QualityRemediationResponse)
async def remediate_quality(
    payload: QualityRemediationRequest, request: Request
) -> QualityRemediationResponse:
    auth = request.state.auth
    if payload.record.get("tenant_id") and payload.record.get("tenant_id") != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    report = evaluate_quality_rules(payload.record_type, payload.record)
    result = remediate_payload(payload.record_type, payload.record, report)
    quality = None
    if payload.apply_fixes and result.remediated_payload:
        quality = compute_quality(
            entity_type=payload.record_type,
            entity_payload=result.remediated_payload,
            rules_config=_load_rules(),
        )
    return _remediation_response(result, quality)


@api_router.post("/quality/remediate/{lineage_id}", response_model=QualityRemediationResponse)
async def remediate_lineage_record(
    lineage_id: str,
    request: Request,
    store: LineageStore = Depends(get_store),
) -> QualityRemediationResponse:
    auth = request.state.auth
    record = store.get(auth.tenant_id, lineage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lineage event not found")
    _ensure_access(auth, record.classification)
    if not record.entity_type or not record.entity_payload:
        raise HTTPException(status_code=400, detail="No entity payload available")
    report = evaluate_quality_rules(record.entity_type, record.entity_payload)
    result = remediate_payload(record.entity_type, record.entity_payload, report)
    quality = compute_quality(
        entity_type=record.entity_type,
        entity_payload=result.remediated_payload,
        rules_config=_load_rules(),
    )
    if result.actions:
        metadata = dict(record.metadata or {})
        metadata["remediation"] = {
            "actions": [action.__dict__ for action in result.actions],
            "remediated_at": datetime.now(timezone.utc).isoformat(),
        }
        updated = LineageRecord(
            **{
                **record.__dict__,
                "entity_payload": result.remediated_payload,
                "quality": quality.__dict__ if quality else None,
                "metadata": metadata,
            }
        )
        store.upsert(updated)
    return _remediation_response(result, quality)


@api_router.get("/retention/status", response_model=RetentionStatusResponse)
async def retention_status(request: Request) -> RetentionStatusResponse:
    scheduler = _get_retention_scheduler(request)
    if not scheduler:
        raise HTTPException(status_code=404, detail="Retention scheduler not configured")
    snapshot = scheduler.snapshot()
    return RetentionStatusResponse(
        interval_seconds=int(snapshot["interval_seconds"]),
        last_pruned_at=snapshot["last_pruned_at"],
        last_pruned_count=int(snapshot["last_pruned_count"]),
    )


app.include_router(api_router)
