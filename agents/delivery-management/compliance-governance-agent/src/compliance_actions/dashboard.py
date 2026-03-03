"""Action handler: get_compliance_dashboard"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_utils import calculate_next_test_date, is_recently_tested

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_get_compliance_dashboard(
    agent: ComplianceRegulatoryAgent,
    project_id: str | None,
    portfolio_id: str | None,
    *,
    domain: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """
    Get compliance dashboard.

    Returns dashboard data.
    """
    agent.logger.info(
        "Getting compliance dashboard for project=%s, portfolio=%s", project_id, portfolio_id
    )

    external_monitoring = None
    if agent.enable_regulatory_monitoring and domain:
        try:
            from actions.monitor_regulatory import handle_monitor_regulations

            external_monitoring = await handle_monitor_regulations(agent, domain, region)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # pragma: no cover - defensive
            agent.logger.warning(
                "External compliance monitoring failed", extra={"error": str(exc)}
            )
            external_monitoring = {
                "summary": "",
                "updates": [],
                "gaps": [],
                "sources": [],
                "used_external_research": False,
            }

    # Get compliance assessment
    assessment = None
    if project_id:
        from actions.assess_compliance import handle_assess_compliance

        assessment = await handle_assess_compliance(agent, project_id, {})

    # Get control testing status
    control_status = await _get_control_testing_status(agent, project_id)

    # Get upcoming audits
    upcoming_audits = await _get_upcoming_audits(agent, project_id)

    # Get recent findings
    recent_findings = await _get_recent_audit_findings(agent, project_id)

    return {
        "project_id": project_id,
        "portfolio_id": portfolio_id,
        "compliance_assessment": assessment,
        "control_testing_status": control_status,
        "upcoming_audits": upcoming_audits,
        "recent_findings": recent_findings,
        "external_monitoring": external_monitoring,
        "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_control_testing_status(
    agent: ComplianceRegulatoryAgent, project_id: str | None
) -> dict[str, Any]:
    """Get control testing status."""
    overdue_tests = 0
    upcoming_tests = 0
    recently_tested_count = 0

    mappings = (
        {project_id: agent.compliance_mappings.get(project_id)}
        if project_id
        else agent.compliance_mappings
    )
    for mapping in mappings.values():
        if not mapping:
            continue
        for control_id, status in mapping.get("control_status", {}).items():
            control = agent.control_registry.get(control_id, {})
            last_test = status.get("last_tested")
            if not last_test:
                overdue_tests += 1
                continue
            if await is_recently_tested(control, status):
                recently_tested_count += 1
            else:
                overdue_tests += 1

            next_test_date = await calculate_next_test_date(control)
            if next_test_date:
                next_test = datetime.fromisoformat(next_test_date)
                if (next_test - datetime.now(timezone.utc)).days <= 14:
                    upcoming_tests += 1

    return {
        "overdue_tests": overdue_tests,
        "upcoming_tests": upcoming_tests,
        "recently_tested": recently_tested_count,
    }


async def _get_upcoming_audits(
    agent: ComplianceRegulatoryAgent, project_id: str | None
) -> list[dict[str, Any]]:
    """Get upcoming audits."""
    upcoming = []
    for audit_id, audit in agent.audits.items():
        if project_id and audit.get("project_id") != project_id:
            continue
        if audit.get("status") in ["Scheduled", "Prepared"]:
            upcoming.append(
                {
                    "audit_id": audit_id,
                    "title": audit.get("title"),
                    "scheduled_date": audit.get("scheduled_date"),
                }
            )
    return upcoming


async def _get_recent_audit_findings(
    agent: ComplianceRegulatoryAgent, project_id: str | None
) -> list[dict[str, Any]]:
    """Get recent audit findings."""
    findings = []
    for audit_id, audit in agent.audits.items():
        if project_id and audit.get("project_id") != project_id:
            continue
        if audit.get("status") == "Completed":
            findings.extend(audit.get("findings", []))
    return findings[:10]  # Most recent 10
