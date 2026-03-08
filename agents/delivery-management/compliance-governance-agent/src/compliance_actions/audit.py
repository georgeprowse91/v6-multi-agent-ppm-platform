"""Action handlers: prepare_audit, conduct_audit"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_utils import generate_audit_id

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_prepare_audit(
    agent: ComplianceRegulatoryAgent, audit_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Prepare audit package.

    Returns audit package and documentation.
    """
    agent.logger.info("Preparing audit: %s", audit_data.get("title"))

    # Generate audit ID
    audit_id = await generate_audit_id()

    project_id = audit_data.get("project_id")
    scope = audit_data.get("scope", [])

    # Compile required documentation
    documentation = await _compile_audit_documentation(agent, project_id, scope)  # type: ignore

    # Collect evidence
    evidence_package = await _compile_evidence(agent, project_id, scope)  # type: ignore

    # Generate control status summary
    control_summary = await _generate_control_summary(agent, project_id)  # type: ignore

    # Create audit record
    audit = {
        "audit_id": audit_id,
        "project_id": project_id,
        "title": audit_data.get("title"),
        "audit_type": audit_data.get("audit_type", "internal"),
        "scope": scope,
        "auditor": audit_data.get("auditor"),
        "scheduled_date": audit_data.get("scheduled_date"),
        "documentation": documentation,
        "evidence_package": evidence_package,
        "control_summary": control_summary,
        "status": "Prepared",
        "findings": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store audit
    agent.audits[audit_id] = audit

    # Persist to database
    await agent.db_service.store("audits", audit_id, audit)
    audit["auditor_access"] = {"auditor": audit.get("auditor"), "access": "read_only"}

    return {
        "audit_id": audit_id,
        "title": audit["title"],
        "scheduled_date": audit["scheduled_date"],
        "documentation_items": len(documentation),
        "evidence_items": len(evidence_package),
        "controls_in_scope": len(control_summary),
        "audit_package_url": f"/audits/{audit_id}/package",
    }


async def handle_conduct_audit(agent: ComplianceRegulatoryAgent, audit_id: str) -> dict[str, Any]:
    """
    Conduct audit and record findings.

    Returns audit findings and scores.
    """
    agent.logger.info("Conducting audit: %s", audit_id)

    audit = agent.audits.get(audit_id)
    if not audit:
        raise ValueError(f"Audit not found: {audit_id}")

    # Review controls and evidence
    findings = []
    controls_reviewed = 0
    controls_passed = 0

    for control_id in audit.get("control_summary", []):
        control = agent.control_registry.get(control_id)
        if not control:
            continue

        controls_reviewed += 1

        # Check control effectiveness
        control_effective = await _verify_control_effectiveness(control)

        if control_effective:
            controls_passed += 1
        else:
            findings.append(
                {
                    "control_id": control_id,
                    "description": control.get("description"),
                    "finding_type": "deficiency",
                    "severity": "high",
                    "recommendation": "Strengthen control implementation and testing",
                }
            )

    # Calculate audit score
    audit_score = (controls_passed / controls_reviewed * 100) if controls_reviewed > 0 else 0

    # Update audit
    audit["findings"] = findings
    audit["audit_score"] = audit_score
    audit["controls_reviewed"] = controls_reviewed
    audit["controls_passed"] = controls_passed
    audit["status"] = "Completed"
    audit["completion_date"] = datetime.now(timezone.utc).isoformat()

    # Persist audit results
    await agent.db_service.store("audits", audit_id, audit)

    await agent._publish_event(
        "compliance.audit.completed",
        {
            "audit_id": audit_id,
            "project_id": audit.get("project_id"),
            "audit_score": audit_score,
            "controls_reviewed": controls_reviewed,
            "controls_passed": controls_passed,
            "findings_count": len(findings),
            "completion_date": audit["completion_date"],
        },
    )
    await agent._notify_stakeholders(
        subject=f"Audit completed: {audit.get('title', audit_id)}",
        message=(
            f"Audit {audit_id} completed with score {audit_score:.1f}. "
            f"Findings: {len(findings)}."
        ),
    )

    return {
        "audit_id": audit_id,
        "audit_score": audit_score,
        "controls_reviewed": controls_reviewed,
        "controls_passed": controls_passed,
        "findings_count": len(findings),
        "findings": findings,
        "completion_date": audit["completion_date"],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _compile_audit_documentation(
    agent: ComplianceRegulatoryAgent, project_id: str, scope: list[str]
) -> list[dict[str, Any]]:
    """Compile documentation for audit from SharePoint and database."""
    documentation = []

    # Gather policies from document management system
    policies = await agent.document_service.list_documents(
        folder_path="Policies",
        limit=50,
    )
    for policy in policies:
        documentation.append(
            {
                "type": "policy",
                "title": policy.get("title", policy.get("Title", "")),
                "url": policy.get("url", policy.get("ServerRelativeUrl", "")),
                "document_id": policy.get("document_id", policy.get("Id", "")),
            }
        )

    # Gather evidence documents for controls in scope
    for control_id in scope:
        evidence_docs = await agent.document_service.list_documents(
            folder_path=f"Compliance Evidence/{control_id}",
            limit=20,
        )
        for doc in evidence_docs:
            documentation.append(
                {
                    "type": "evidence",
                    "control_id": control_id,
                    "title": doc.get("title", doc.get("Title", "")),
                    "url": doc.get("url", doc.get("ServerRelativeUrl", "")),
                    "document_id": doc.get("document_id", doc.get("Id", "")),
                }
            )

    return documentation


async def _compile_evidence(
    agent: ComplianceRegulatoryAgent, project_id: str, scope: list[str]
) -> list[dict[str, Any]]:
    """Compile evidence for audit."""
    evidence_package = []
    for control_id, evidence_list in agent.evidence.items():
        evidence_package.extend(evidence_list)
    return evidence_package


async def _generate_control_summary(agent: ComplianceRegulatoryAgent, project_id: str) -> list[str]:
    """Generate control summary for audit."""
    mapping = agent.compliance_mappings.get(project_id)
    if not mapping:
        return []
    return mapping.get("applicable_controls", [])  # type: ignore


async def _verify_control_effectiveness(control: dict[str, Any]) -> bool:
    """Verify control effectiveness."""
    last_result = control.get("last_test_result")
    return last_result == "pass"
