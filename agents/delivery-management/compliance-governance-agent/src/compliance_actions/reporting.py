"""Action handlers: generate_compliance_report, list_reports, get_report"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_generate_compliance_report(
    agent: ComplianceRegulatoryAgent,
    report_type: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate compliance report.

    Returns report data.
    """
    agent.logger.info("Generating %s compliance report", report_type)

    if report_type == "summary":
        return await _generate_summary_report(agent, filters)
    elif report_type == "detailed":
        return await _generate_detailed_report(agent, filters)
    elif report_type == "audit":
        return await _generate_audit_report(agent, filters)
    elif report_type in {"soc2", "soc-2", "iso27001", "iso-27001"}:
        return await _generate_certification_report(agent, report_type, filters)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


async def handle_list_reports(
    agent: ComplianceRegulatoryAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    records = await agent.db_service.query("compliance_reports", filters=filters, limit=200)
    return {"count": len(records), "reports": records}


async def handle_get_report(
    agent: ComplianceRegulatoryAgent, report_id: str | None
) -> dict[str, Any]:
    if not report_id:
        raise ValueError("report_id is required")
    record = await agent.db_service.retrieve("compliance_reports", report_id)
    return {"report": record}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _store_report(
    agent: ComplianceRegulatoryAgent, report_type: str, data: dict[str, Any]
) -> dict[str, Any]:
    report_id = (
        f"REP-{report_type.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )
    report = {
        "report_id": report_id,
        "report_type": report_type,
        "data": data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.compliance_reports[report_id] = report
    await agent.db_service.store("compliance_reports", report_id, report)
    return report


async def _generate_summary_report(
    agent: ComplianceRegulatoryAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Generate summary compliance report."""
    project_id = filters.get("project_id")
    assessment = None
    if project_id:
        from actions.assess_compliance import handle_assess_compliance

        assessment = await handle_assess_compliance(agent, project_id, {"mapping": filters})
    report_data = {
        "assessment": assessment,
        "alerts": [
            alert
            for alert in agent.compliance_alerts
            if not project_id or alert.get("project_id") == project_id
        ],
        "latest_audits": list(agent.audits.values())[:5],
    }
    return await _store_report(agent, "summary", report_data)


async def _generate_detailed_report(
    agent: ComplianceRegulatoryAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Generate detailed compliance report."""
    project_id = filters.get("project_id")
    mappings = (
        {project_id: agent.compliance_mappings.get(project_id)}
        if project_id
        else agent.compliance_mappings
    )
    report_data = {
        "mappings": mappings,
        "controls": agent.control_registry,
        "regulations": agent.regulation_library,
        "evidence": agent.evidence,
        "audits": agent.audits,
    }
    return await _store_report(agent, "detailed", report_data)


async def _generate_audit_report(
    agent: ComplianceRegulatoryAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Generate audit report."""
    from actions.audit import _generate_control_summary

    project_id = filters.get("project_id")
    audits = [
        audit
        for audit in agent.audits.values()
        if not project_id or audit.get("project_id") == project_id
    ]
    report_data = {
        "audits": audits,
        "control_summary": (
            await _generate_control_summary(agent, project_id) if project_id else []
        ),
        "findings": [finding for audit in audits for finding in audit.get("findings", [])],
    }
    return await _store_report(agent, "audit", report_data)


async def _generate_certification_report(
    agent: ComplianceRegulatoryAgent, report_type: str, filters: dict[str, Any]
) -> dict[str, Any]:
    from actions.assess_compliance import handle_assess_compliance

    normalized_type = report_type.replace("-", "").lower()
    project_id = filters.get("project_id")
    assessment = (
        await handle_assess_compliance(agent, project_id, {"mapping": filters})
        if project_id
        else None
    )
    statement = "Compliance statement"
    framework = "SOC 2" if "soc2" in normalized_type else "ISO 27001"
    if assessment:
        statement = (
            f"{framework} compliance assessment completed with score "
            f"{assessment.get('compliance_score', 0):.1f}."
        )

    report_data = {
        "framework": framework,
        "statement": statement,
        "assessment": assessment,
        "generated_for": project_id,
    }
    report = await _store_report(agent, report_type, report_data)
    report_content = (
        f"# {framework} Compliance Report\n\n"
        f"## Statement\n{statement}\n\n"
        f"## Assessment Summary\n{json.dumps(assessment or {}, indent=2)}\n"
    )
    doc_metadata = DocumentMetadata(
        title=f"{framework} Compliance Report",
        description=f"{framework} compliance report for {project_id or 'portfolio'}",
        classification="confidential",
        tags=["compliance_report", framework.replace(" ", "_").lower()],
        owner=agent.agent_id,
    )
    publish_result = await agent.document_service.publish_document(
        document_content=report_content,
        metadata=doc_metadata,
        folder_path="Compliance Reports",
    )
    report["report_url"] = publish_result.get("url")
    return report
