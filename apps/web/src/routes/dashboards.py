"""Dashboard routes: health, trends, quality, KPIs, narrative, risks, issues, aggregations, export, power BI."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from routes._deps import (
    DEMO_DOWNLOADS_DIR,
    _analytics_client,
    _dashboard_demo_payload_or_default,
    _demo_mode_enabled,
    _lineage_client,
    _passthrough_response,
    _require_session,
    _slugify_filename,
    _unified_dashboards_enabled,
    build_forward_headers,
    logger,
    permission_required,
)
from routes._models import DashboardExportResponse, DashboardWhatIfRequest

router = APIRouter()


# Portfolio-level analytics
@router.get("/api/portfolio-health")
@permission_required("analytics.view")
async def get_portfolio_health(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _dashboard_demo_payload_or_default("portfolio-health.json", {})
        if payload:
            return JSONResponse(content=payload)
    # Mock when live analytics not available
    return JSONResponse(content={"portfolio_id": portfolio_id, "status": "green"})


@router.get("/api/lifecycle-metrics")
@permission_required("analytics.view")
async def get_lifecycle_metrics(
    request: Request, portfolio_id: str | None = None, project_id: str | None = None
) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        payload = _dashboard_demo_payload_or_default("lifecycle-metrics.json", {})
        if payload:
            return JSONResponse(content=payload)
    return JSONResponse(content={"portfolio_id": portfolio_id, "metrics": []})


# Project dashboards
@router.get("/api/dashboard/{project_id}/health")
@permission_required("analytics.view")
async def get_dashboard_health(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-health.json",
                {"project_id": project_id, "status": "green", "composite_score": 0.91},
            )
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_project_health(project_id, headers=headers)
    logger.info(
        "dashboard.health.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/api/dashboard/{project_id}/trends")
@permission_required("analytics.view")
async def get_dashboard_trends(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-trends.json", {"project_id": project_id, "points": []}
            )
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_project_trends(project_id, headers=headers)
    logger.info(
        "dashboard.trends.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/api/dashboard/{project_id}/quality")
@permission_required("analytics.view")
async def get_dashboard_quality(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-quality.json",
                {"total_rules": 0, "pass_rate": 1.0, "violations": []},
            )
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _lineage_client().get_quality_summary(headers=headers)
    logger.info(
        "dashboard.quality.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.post("/api/dashboard/{project_id}/what-if")
@permission_required("analytics.view")
async def create_dashboard_what_if(
    project_id: str, payload: DashboardWhatIfRequest, request: Request
) -> Response:
    if _demo_mode_enabled():
        scenario_hash = hashlib.sha1(
            f"{project_id}:{payload.scenario}:{json.dumps(payload.adjustments, sort_keys=True)}".encode()
        ).hexdigest()[:10]
        baseline = _dashboard_demo_payload_or_default(
            "project-dashboard-kpis.json",
            {
                "project_id": project_id,
                "metrics": [],
                "computed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        adjusted_metrics: list[dict[str, Any]] = []
        for metric in baseline.get("metrics", []):
            name = str(metric.get("name", ""))
            normalized = float(metric.get("normalized", 0.0))
            boost = (
                float(payload.adjustments.get(name, 0.0))
                if isinstance(payload.adjustments, dict)
                else 0.0
            )
            adjusted_metrics.append(
                {**metric, "normalized": max(0.0, min(1.0, round(normalized + boost, 3)))}
            )
        return JSONResponse(
            content={
                "project_id": project_id,
                "scenario_id": f"demo-{scenario_hash}",
                "status": "completed",
                "baseline": baseline,
                "adjusted": {
                    **baseline,
                    "metrics": adjusted_metrics or baseline.get("metrics", []),
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
                "narrative": _dashboard_demo_payload_or_default(
                    "project-dashboard-narrative.json",
                    {
                        "project_id": project_id,
                        "summary": "Demo what-if narrative.",
                        "highlights": [],
                        "risks": [],
                        "opportunities": [],
                        "data_quality_notes": [],
                        "computed_at": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            }
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().request_what_if(
        project_id, payload.model_dump(), headers=headers
    )
    logger.info(
        "dashboard.whatif.request",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/api/dashboard/{project_id}/kpis")
@permission_required("analytics.view")
async def get_dashboard_kpis(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-kpis.json",
                {
                    "project_id": project_id,
                    "metrics": [],
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_project_kpis(project_id, headers=headers)
    logger.info(
        "dashboard.kpis.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/api/dashboard/{project_id}/narrative")
@permission_required("analytics.view")
async def get_dashboard_narrative(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-narrative.json",
                {
                    "project_id": project_id,
                    "summary": "Demo narrative.",
                    "highlights": [],
                    "risks": [],
                    "opportunities": [],
                    "data_quality_notes": [],
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_project_narrative(project_id, headers=headers)
    logger.info(
        "dashboard.narrative.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/api/dashboard/{project_id}/risks")
@permission_required("analytics.view")
async def get_dashboard_risks(project_id: str, request: Request) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-risks.json", {"project_id": project_id, "items": []}
            )
        )
    return JSONResponse(
        content={
            "project_id": project_id,
            "items": [
                {"id": "risk-1", "title": "Scope volatility", "severity": "High", "owner": "PMO"},
                {
                    "id": "risk-2",
                    "title": "Vendor lead-time",
                    "severity": "Medium",
                    "owner": "Procurement",
                },
            ],
        }
    )


@router.get("/api/dashboard/{project_id}/issues")
@permission_required("analytics.view")
async def get_dashboard_issues(project_id: str, request: Request) -> Response:
    _require_session(request)
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-issues.json", {"project_id": project_id, "items": []}
            )
        )
    return JSONResponse(
        content={
            "project_id": project_id,
            "items": [
                {
                    "id": "issue-1",
                    "title": "Approval queue delay",
                    "status": "Open",
                    "owner": "Governance",
                },
                {
                    "id": "issue-2",
                    "title": "Test environment outage",
                    "status": "Mitigating",
                    "owner": "Platform",
                },
            ],
        }
    )


@router.get("/api/dashboard/{project_id}/aggregations")
@permission_required("analytics.view")
async def get_dashboard_aggregations(project_id: str, request: Request) -> Response:
    if _demo_mode_enabled():
        return JSONResponse(
            content=_dashboard_demo_payload_or_default(
                "project-dashboard-aggregations.json",
                {
                    "project_id": project_id,
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                    "artifacts": [],
                    "warnings": [],
                },
            )
        )
    if not _unified_dashboards_enabled():
        raise HTTPException(status_code=404, detail="Unified dashboards are not enabled")
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_project_aggregations(project_id, headers=headers)
    logger.info(
        "dashboard.aggregations.fetch",
        extra={"tenant_id": session.get("tenant_id"), "project_id": project_id},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.post("/api/dashboard/{project_id}/export-pack", response_model=DashboardExportResponse)
@permission_required("analytics.view")
async def export_dashboard_pack(project_id: str, request: Request) -> DashboardExportResponse:
    _require_session(request)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "project_id": project_id,
        "generated_at": generated_at,
        "health": _dashboard_demo_payload_or_default("project-dashboard-health.json", {}),
        "trends": _dashboard_demo_payload_or_default("project-dashboard-trends.json", {}),
        "quality": _dashboard_demo_payload_or_default("project-dashboard-quality.json", {}),
        "kpis": _dashboard_demo_payload_or_default("project-dashboard-kpis.json", {}),
        "narrative": _dashboard_demo_payload_or_default("project-dashboard-narrative.json", {}),
    }
    file_name = f"dashboard-pack-{_slugify_filename(project_id)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    output_path = DEMO_DOWNLOADS_DIR / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return DashboardExportResponse(
        project_id=project_id,
        file_name=file_name,
        download_path=f"/storage/downloads/{file_name}",
        generated_at=generated_at,
    )


@router.get("/api/analytics/powerbi/{report_type}")
@permission_required("analytics.view")
async def get_powerbi_embed(report_type: str, request: Request) -> Response:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    response = await _analytics_client().get_powerbi_report(report_type, headers=headers)
    logger.info(
        "dashboard.powerbi.embed.fetch",
        extra={"tenant_id": session.get("tenant_id"), "report_type": report_type},
    )
    if response.status_code >= 400:
        return _passthrough_response(response)
    return JSONResponse(status_code=response.status_code, content=response.json())
