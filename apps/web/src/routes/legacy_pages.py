"""Legacy SPA redirect pages and static feed endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from routes._deps import _approval_payload, _demo_mode_enabled, _spa_route, demo_outbox

router = APIRouter()


@router.get("/approvals", response_model=None)
async def approvals_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/approvals"), status_code=307)


@router.get("/workflow-monitoring", response_model=None)
async def workflow_monitoring_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/workflows/monitoring"), status_code=307)


@router.get("/document-search", response_model=None)
async def document_search_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/knowledge/documents"), status_code=307)


@router.get("/lessons-learned", response_model=None)
async def lessons_learned_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/knowledge/lessons"), status_code=307)


@router.get("/audit-log", response_model=None)
async def audit_log_page() -> RedirectResponse:
    return RedirectResponse(url=_spa_route("/admin/audit"), status_code=307)


@router.get("/api/approvals")
async def approvals_feed() -> dict[str, Any]:
    return _approval_payload()


@router.get("/api/workflow-monitoring")
async def workflow_monitoring_feed() -> dict[str, Any]:
    return {
        "status_board": {"healthy": 18, "warning": 4, "failed": 2},
        "runs": [
            {"id": "WF-2041", "name": "Intake Routing", "status": "Success", "duration": "2m 12s", "agent": "Intake"},
            {"id": "WF-2042", "name": "Approval Escalation", "status": "Failed", "duration": "4m 50s", "agent": "Governance"},
            {"id": "WF-2043", "name": "Document Sync", "status": "Warning", "duration": "9m 03s", "agent": "SharePoint"},
        ],
        "bottlenecks": [
            {"issue": "Approval Escalation backlog", "recommendation": "Reroute to alternate approver", "severity": "High"},
            {"issue": "Document Sync latency", "recommendation": "Increase connector concurrency", "severity": "Medium"},
        ],
    }


@router.get("/api/document-search")
async def document_search_feed() -> dict[str, Any]:
    return {
        "query": "business case",
        "filters": {"project": "Phoenix", "confidentiality": "Confidential", "stage": "Initiation"},
        "results": [
            {"id": "doc-771", "title": "Business Case v5", "project": "Phoenix", "tags": ["ROI", "Approval", "Confidential"], "summary": "Latest funding request with revised ROI assumptions."},
            {"id": "doc-772", "title": "Lessons Learned > Sprint 8", "project": "Phoenix", "tags": ["Retrospective", "Risk"], "summary": "Highlights schedule recovery tactics."},
        ],
        "saved_searches": ["Critical approvals", "Evidence packs"],
    }


@router.get("/api/lessons-learned")
async def lessons_learned_feed() -> dict[str, Any]:
    return {
        "categories": ["Schedule", "Scope", "Risk", "Vendor"],
        "entries": [
            {"id": "lesson-201", "title": "Sprint 8 Retrospective", "status": "Applied 3x", "theme": "Schedule", "severity": "Medium"},
            {"id": "lesson-202", "title": "Vendor Delay Mitigation", "status": "Applied 1x", "theme": "Vendor", "severity": "High"},
        ],
        "recommendations": [{"title": "Contractual lead times", "tags": ["Procurement", "SLA", "Risk"], "adoption": "Reviewed"}],
    }


@router.get("/api/audit-log")
async def audit_log_feed() -> dict[str, Any]:
    return {
        "filters": ["Actor", "Action", "Object", "Framework", "Date"],
        "entries": [
            {"timestamp": "09:32", "action": "Approval", "object": "Gate Exit", "actor": "A. Lee", "source": "Approval Workflow", "hash": "a13f9c2"},
            {"timestamp": "09:14", "action": "Workflow Retry", "object": "WF-2041", "actor": "Orchestrator", "source": "Automation", "hash": "b82c4d1"},
        ],
        "evidence_packs": [{"id": "pack-7", "label": "Q1 Compliance Review", "integrity": "SHA256"}],
    }


@router.get("/ui/migration-map")
async def ui_migration_map() -> dict[str, Any]:
    return {
        "migration_status": {"legacy_ui_retired": True, "notes": "Legacy UI has been fully retired; compatibility is redirect-only."},
        "routes": [
            {"legacy": "/v1/approvals", "spa": "/app/approvals", "notes": "Approval inbox moved into SPA workflow area."},
            {"legacy": "/v1/workflow-monitoring", "spa": "/app/workflows/monitoring", "notes": "Monitoring now relies on SPA route with live updates."},
            {"legacy": "/v1/document-search", "spa": "/app/knowledge/documents", "notes": "Knowledge document search consolidated in SPA."},
            {"legacy": "/v1/lessons-learned", "spa": "/app/knowledge/lessons", "notes": "Lessons page moved to knowledge section."},
            {"legacy": "/v1/audit-log", "spa": "/app/admin/audit", "notes": "Admin audit access requires admin role in SPA."},
        ],
        "compatibility": {
            "api_endpoints": "Preserved under /v1/api/* and /v1/workflows/*.",
            "legacy_html": "Legacy HTML compatibility removed; routes redirect to SPA.",
        },
    }
