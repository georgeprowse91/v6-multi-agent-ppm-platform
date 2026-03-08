"""Global search route."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from routes._deps import (
    _approval_payload,
    _demo_mode_enabled,
    _get_search_service,
    _highlight_query,
    _load_demo_dashboard_payload,
    _load_demo_search_payload,
    _load_projects,
    _match_score,
    _require_session,
    workflow_definition_store,
)
from routes._models import SearchResponse, SearchResult

router = APIRouter()


@router.get("/api/search", response_model=SearchResponse)
async def search_global(
    request: Request,
    q: str | None = Query(default=None, alias="q"),
    query: str | None = None,
    types: str | None = None,
    project_ids: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> SearchResponse:
    session = _require_session(request)
    type_list = [e.strip() for e in types.split(",")] if types else []
    selected_types = type_list or ["document", "project", "knowledge", "approval", "workflow"]
    project_id_set = (
        {e.strip() for e in project_ids.split(",") if e.strip()} if project_ids else None
    )
    resolved_query = (q or query or "").strip()

    if _demo_mode_enabled():
        demo_payload = _load_demo_search_payload("global-search.json")
        if demo_payload:
            results_payload = demo_payload.get("results", [])
            return SearchResponse(
                query=resolved_query,
                offset=0,
                limit=min(max(limit, 1), 100),
                total=len(results_payload),
                results=[SearchResult.model_validate(i) for i in results_payload],
            )

    search_service = _get_search_service()
    search_results, _ = search_service.search(
        query=resolved_query,
        types=[e for e in selected_types if e in {"document", "knowledge", "lesson"}],
        project_ids=project_id_set,
        tenant_id=session.get("tenant_id"),
        offset=0,
        limit=200,
    )
    results: list[SearchResult] = [
        SearchResult(
            id=i.id,
            type=i.result_type,
            title=i.title,
            summary=i.summary,
            project_id=i.project_id,
            updated_at=i.updated_at.isoformat() if i.updated_at else None,
            highlights=i.highlights,
            payload=i.payload,
        )
        for i in search_results
    ]

    if "project" in selected_types:
        for project in _load_projects():
            if project_id_set and project.id not in project_id_set:
                continue
            text = f"{project.name} {project.template_id} {project.methodology.get('name', '')}"
            if _match_score(resolved_query, text) < 0.6:
                continue
            summary = f"Template {project.template_id}"
            methodology_name = project.methodology.get("name")
            if methodology_name:
                summary = f"{summary} \u00b7 Methodology {methodology_name}"
            results.append(
                SearchResult(
                    id=project.id,
                    type="project",
                    title=project.name,
                    summary=summary,
                    project_id=project.id,
                    updated_at=project.created_at,
                    highlights={
                        k: v
                        for k, v in {
                            "title": _highlight_query(resolved_query, project.name),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if v
                    }
                    or None,
                    payload={
                        "projectId": project.id,
                        "name": project.name,
                        "templateId": project.template_id,
                        "methodology": project.methodology,
                        "createdAt": project.created_at,
                    },
                )
            )

    if "approval" in selected_types:
        approvals_payload = (
            _load_demo_dashboard_payload("approvals.json")
            if _demo_mode_enabled()
            else _approval_payload()
        )
        approvals = approvals_payload.get("approvals") or approvals_payload.get("items") or []
        for idx, approval in enumerate(approvals):
            title = approval.get("title") or approval.get("name") or "Approval"
            meta = approval.get("meta") or []
            summary = " \u00b7 ".join(meta) if isinstance(meta, list) else str(meta)
            if not summary:
                summary = " \u00b7 ".join(
                    v
                    for v in [approval.get("project"), approval.get("risk"), approval.get("due_in")]
                    if v
                )
            if _match_score(resolved_query, f"{title} {summary}") < 0.6:
                continue
            results.append(
                SearchResult(
                    id=str(approval.get("id") or f"approval-{idx}"),
                    type="approval",
                    title=title,
                    summary=summary,
                    project_id=approval.get("project"),
                    highlights={
                        k: v
                        for k, v in {
                            "title": _highlight_query(resolved_query, title),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if v
                    }
                    or None,
                    payload=approval,
                )
            )

    if "workflow" in selected_types:
        if _demo_mode_enabled():
            wp = _load_demo_dashboard_payload("workflow-monitoring.json") or {}
            workflows = wp.get("runs", [])
        else:
            workflows = [w.model_dump() for w in workflow_definition_store.list_summaries()]
        for idx, wf in enumerate(workflows):
            title = wf.get("name") or wf.get("title") or "Workflow"
            summary = wf.get("description") or " \u00b7 ".join(
                v
                for v in [
                    wf.get("status"),
                    wf.get("run_id") or wf.get("id"),
                    wf.get("owner") or wf.get("agent"),
                ]
                if v
            )
            if _match_score(resolved_query, f"{title} {summary}") < 0.6:
                continue
            results.append(
                SearchResult(
                    id=str(
                        wf.get("workflow_id")
                        or wf.get("run_id")
                        or wf.get("id")
                        or f"workflow-{idx}"
                    ),
                    type="workflow",
                    title=title,
                    summary=summary,
                    updated_at=wf.get("updated_at"),
                    highlights={
                        k: v
                        for k, v in {
                            "title": _highlight_query(resolved_query, title),
                            "summary": _highlight_query(resolved_query, summary),
                        }.items()
                        if v
                    }
                    or None,
                    payload=wf,
                )
            )

    total = len(results)
    results.sort(key=lambda i: (i.updated_at or ""), reverse=True)
    trimmed = results[max(offset, 0) : max(offset, 0) + min(max(limit, 1), 100)]
    return SearchResponse(
        query=resolved_query,
        offset=max(offset, 0),
        limit=min(max(limit, 1), 100),
        total=total,
        results=trimmed,
    )
