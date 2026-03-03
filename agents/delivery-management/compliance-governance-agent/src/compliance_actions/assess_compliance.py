"""Action handler: assess_compliance"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_models import EvidenceSnapshot
from compliance_utils import (
    calculate_compliance_scores,
    identify_gap_type,
    is_recently_tested,
    recommend_remediation,
)

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_assess_compliance(
    agent: ComplianceRegulatoryAgent,
    project_id: str,
    assessment_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Assess compliance readiness.

    Returns assessment results and gap analysis.
    """
    agent.logger.info("Assessing compliance for project: %s", project_id)

    tenant_id = assessment_data.get("tenant_id", "unknown")
    correlation_id = assessment_data.get("correlation_id", str(uuid.uuid4()))
    mapping = agent.compliance_mappings.get(project_id)
    if not mapping:
        # Create mapping first
        await agent._map_controls_to_project(
            project_id,
            assessment_data.get("mapping", {}),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        mapping = agent.compliance_mappings.get(project_id)

    # Assess each control
    control_assessments = []
    gaps = []

    evidence_bundle = await gather_evidence_from_agents(agent, project_id)
    await store_evidence_snapshot(agent, project_id, evidence_bundle)
    for control_id, status in mapping["control_status"].items():  # type: ignore
        control = agent.control_registry.get(control_id)
        if not control:
            continue

        # Check implementation status
        implemented = status.get("implementation_status") == "Implemented"
        evidence_provided = status.get("evidence_uploaded", False)
        recently_tested = await is_recently_tested(control, status)

        control_evidence = {
            "implementation_status": status.get("implementation_status"),
            "evidence_uploaded": status.get("evidence_uploaded", False),
            "recently_tested": recently_tested,
            "audit_logs": evidence_bundle.get("audit_logs", []),
            "risk_mitigations": evidence_bundle.get("risk_mitigations", []),
            "quality_results": evidence_bundle.get("quality_results", []),
            "deployment_evidence": evidence_bundle.get("deployment_evidence", []),
            "privacy_impact_assessed": evidence_bundle.get("privacy_impact_assessed", False),
        }
        evaluation = agent.rule_engine.evaluate(control, control_evidence)

        assessment = {
            "control_id": control_id,
            "description": control.get("description"),
            "implemented": implemented,
            "evidence_provided": evidence_provided,
            "recently_tested": recently_tested,
            "compliant": evaluation["met"],
            "evaluation_score": evaluation["score"],
            "evaluation_gaps": evaluation["gaps"],
        }

        control_assessments.append(assessment)

        if not assessment["compliant"]:
            gaps.append(
                {
                    "control_id": control_id,
                    "description": control.get("description"),
                    "gap_type": await identify_gap_type(assessment),
                    "remediation": await recommend_remediation(assessment),
                    "evaluation_gaps": evaluation["gaps"],
                }
            )

    score_summary = calculate_compliance_scores(
        mapping, control_assessments, agent.control_registry, agent.regulation_library
    )

    assessment_result = {
        "project_id": project_id,
        "compliance_score": score_summary["overall_score"],
        "total_controls": score_summary["total_controls"],
        "compliant_controls": score_summary["compliant_controls"],
        "gaps_identified": len(gaps),
        "gaps": gaps,
        "control_assessments": control_assessments,
        "regulation_scores": score_summary["regulation_scores"],
        "evidence_summary": evidence_bundle,
        "assessment_date": datetime.now(timezone.utc).isoformat(),
    }

    assessment_id = f"ASM-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    await agent.db_service.store("compliance_assessments", assessment_id, assessment_result)

    return assessment_result


async def gather_evidence_from_agents(
    agent: ComplianceRegulatoryAgent, project_id: str
) -> dict[str, Any]:
    evidence_summary = {
        "risk_mitigations": [],
        "quality_results": [],
        "audit_logs": [],
        "deployment_evidence": [],
        "privacy_impact_assessed": False,
        "security_scans": [],
    }

    risk_agent = agent.agent_clients.get("risk")
    quality_agent = agent.agent_clients.get("quality")
    release_agent = agent.agent_clients.get("release")
    security_agent = agent.agent_clients.get("security")

    if risk_agent:
        response = await _call_agent(
            agent,
            risk_agent,
            {"action": "get_risk_summary", "project_id": project_id},
        )
        evidence_summary["risk_mitigations"] = response.get("mitigations", []) or response.get(
            "risk_mitigations", []
        )

    if quality_agent:
        response = await _call_agent(
            agent,
            quality_agent,
            {"action": "get_quality_summary", "project_id": project_id},
        )
        evidence_summary["quality_results"] = response.get("test_results", []) or response.get(
            "quality_results", []
        )

    if release_agent:
        response = await _call_agent(
            agent,
            release_agent,
            {"action": "get_release_audit_logs", "project_id": project_id},
        )
        evidence_summary["audit_logs"] = response.get("audit_logs", [])
        evidence_summary["deployment_evidence"] = response.get(
            "deployment_evidence", []
        ) or response.get("deployment_logs", [])

    if security_agent:
        response = await _call_agent(
            agent,
            security_agent,
            {"action": "get_security_summary", "project_id": project_id},
        )
        evidence_summary["security_scans"] = response.get("security_scans", []) or response.get(
            "vulnerability_scans", []
        )
        evidence_summary["audit_logs"] = [
            *evidence_summary["audit_logs"],
            *response.get("audit_logs", []),
        ]

    evidence_summary["privacy_impact_assessed"] = bool(evidence_summary["risk_mitigations"])

    return evidence_summary


async def _call_agent(
    agent: ComplianceRegulatoryAgent, target: Any, payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        response = await target.process(payload)
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
            "Agent evidence collection failed",
            extra={"error": str(exc), "payload": payload},
        )
        return {}
    return response if isinstance(response, dict) else {}


async def store_evidence_snapshot(
    agent: ComplianceRegulatoryAgent, project_id: str, evidence: dict[str, Any]
) -> None:
    snapshot_id = f"ES-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    snapshot = EvidenceSnapshot(
        snapshot_id=snapshot_id,
        project_id=project_id,
        collected_at=datetime.now(timezone.utc).isoformat(),
        sources=[key for key, value in evidence.items() if value],
        metadata={"agent_id": agent.agent_id},
        payload=evidence,
    )
    snapshot_record = {
        "snapshot_id": snapshot.snapshot_id,
        "project_id": snapshot.project_id,
        "collected_at": snapshot.collected_at,
        "sources": snapshot.sources,
        "metadata": snapshot.metadata,
        "payload": snapshot.payload,
    }
    await agent.db_service.store("evidence_snapshots", snapshot_id, snapshot_record)
    agent.evidence_store.upsert(project_id, snapshot_id, snapshot_record)
