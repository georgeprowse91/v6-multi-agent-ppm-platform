"""Action handlers for quality audit management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quality_models import build_audit
from quality_utils import (
    calculate_audit_score,
    extract_audit_findings,
    generate_audit_id,
    generate_audit_recommendations,
)

if TYPE_CHECKING:
    from quality_management_agent import QualityManagementAgent


async def conduct_audit(
    agent: QualityManagementAgent,
    audit_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Conduct quality audit.  Returns audit findings and scores."""
    agent.logger.info("Conducting audit: %s", audit_data.get("title"))

    audit_id = await generate_audit_id()

    audit_checks = await _perform_audit_checks(
        agent, audit_data.get("project_id"), audit_data.get("checklist", [])  # type: ignore
    )
    audit_score = await calculate_audit_score(audit_checks)
    findings = await extract_audit_findings(audit_checks)
    recommendations = await generate_audit_recommendations(audit_checks)

    audit = build_audit(audit_id, audit_data, audit_checks, audit_score, findings, recommendations)

    agent.audits[audit_id] = audit
    agent.audit_store.upsert(tenant_id, audit_id, audit)
    await agent._publish_quality_event(
        "quality.audit.completed",
        payload={
            "audit_id": audit_id,
            "project_id": audit.get("project_id"),
            "score": audit.get("audit_score"),
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    audit_document = await _publish_audit_document(agent, audit, audit_data)
    if audit_document:
        audit["document"] = audit_document
    await agent._store_record("quality_audits", audit_id, audit)

    return {
        "audit_id": audit_id,
        "project_id": audit["project_id"],
        "audit_score": audit_score,
        "total_checks": len(audit_checks),
        "passed_checks": sum(1 for c in audit_checks if c.get("result") == "pass"),
        "findings": audit["findings"],
        "recommendations": audit["recommendations"],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _perform_audit_checks(
    agent: QualityManagementAgent,
    project_id: str,
    checklist: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks = []
    static_analysis = agent.integration_config.get("qa_tools", {}).get("static_analysis", {})
    lint_issues = static_analysis.get("issues", [])
    lint_result = "fail" if lint_issues else "pass"
    checks.append(
        {
            "check": "static_analysis",
            "result": lint_result,
            "notes": "Issues detected" if lint_issues else "No issues detected",
            "issues": lint_issues,
        }
    )
    from quality_actions.metric_actions import _fetch_coverage_metrics

    coverage_snapshot = await _fetch_coverage_metrics(agent, project_id)
    coverage_pct = float(coverage_snapshot.get("coverage_pct", 0.0)) if coverage_snapshot else 0.0
    coverage_result = "pass" if coverage_pct >= agent.min_test_coverage * 100 else "fail"
    checks.append(
        {
            "check": "coverage_threshold",
            "result": coverage_result,
            "notes": f"Coverage {coverage_pct:.1f}%",
        }
    )
    for item in checklist:
        checks.append(
            {
                "check": item.get("check"),
                "result": item.get("result", "pass"),
                "notes": item.get("notes", ""),
            }
        )
    return checks


async def _publish_audit_document(
    agent: QualityManagementAgent,
    audit: dict[str, Any],
    audit_data: dict[str, Any],
) -> dict[str, Any] | None:
    from agents.common.connector_integration import DocumentManagementService, DocumentMetadata

    report_content = audit_data.get("report")
    if not report_content:
        return None
    if agent.document_service is None:
        agent.document_service = DocumentManagementService(agent.config.get("document_service"))
    metadata = DocumentMetadata(
        title=audit.get("title") or f"Quality Audit {audit.get('audit_id')}",
        description=f"Quality audit report for project {audit.get('project_id')}",
        classification=audit_data.get("classification", "internal"),
        tags=["quality", "audit", audit.get("type", "process_audit")],
        owner=audit_data.get("auditor", ""),
    )
    return await agent.document_service.publish_document(
        document_content=report_content,
        metadata=metadata,
        folder_path="Quality/Audits",
    )
