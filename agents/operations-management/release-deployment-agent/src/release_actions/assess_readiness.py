"""Action handler: assess_readiness."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from release_utils import (
    collect_readiness_blockers,
    generate_readiness_assessment_id,
    publish_event,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def assess_readiness(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """
    Assess release readiness with go/no-go criteria.

    Returns readiness assessment and recommendations.
    """
    agent.logger.info("Assessing readiness for release: %s", release_id)

    release = agent.releases.get(release_id)
    if not release:
        raise ValueError(f"Release not found: {release_id}")

    quality_check = await _check_quality_criteria(agent, release_id)
    approval_check = await _check_approval_status(agent, release_id)
    change_check = await _check_change_approvals(agent, release_id)
    risk_check = await _check_risk_level(agent, release_id)
    compliance_check = await _check_compliance_requirements(agent, release_id)

    critical_blockers = await collect_readiness_blockers(
        {
            "quality": quality_check,
            "approval": approval_check,
            "change": change_check,
            "risk": risk_check,
            "compliance": compliance_check,
        }
    )

    # Calculate overall readiness score
    readiness_criteria = {
        "quality_passed": quality_check.get("passed", False),
        "approvals_complete": approval_check.get("complete", False),
        "changes_approved": change_check.get("approved", False),
        "risk_acceptable": risk_check.get("acceptable", False),
        "compliance_met": compliance_check.get("met", False),
    }

    all_passed = all(readiness_criteria.values()) and not critical_blockers
    readiness_score = sum(1 for v in readiness_criteria.values() if v) / len(readiness_criteria)

    # Generate go/no-go recommendation
    recommendation = "GO" if all_passed else "NO-GO"

    assessment_id = await generate_readiness_assessment_id()
    assessment_record = {
        "assessment_id": assessment_id,
        "release_id": release_id,
        "readiness_score": readiness_score,
        "recommendation": recommendation,
        "criteria": readiness_criteria,
        "quality_details": quality_check,
        "approval_details": approval_check,
        "change_details": change_check,
        "risk_details": risk_check,
        "compliance_details": compliance_check,
        "critical_blockers": critical_blockers,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.readiness_assessments[assessment_id] = assessment_record
    await agent.db_service.store("readiness_assessments", assessment_id, assessment_record)
    await publish_event(
        agent,
        "deployment.readiness_assessed",
        {
            "assessment_id": assessment_id,
            "release_id": release_id,
            "recommendation": recommendation,
            "readiness_score": readiness_score,
            "criteria": readiness_criteria,
        },
    )

    return {
        "release_id": release_id,
        "assessment_id": assessment_id,
        "readiness_score": readiness_score,
        "recommendation": recommendation,
        "criteria": readiness_criteria,
        "quality_details": quality_check,
        "approval_details": approval_check,
        "change_details": change_check,
        "risk_details": risk_check,
        "compliance_details": compliance_check,
        "critical_blockers": critical_blockers,
        "next_steps": "Proceed with deployment" if all_passed else "Address failing criteria",
    }


# ---------------------------------------------------------------------------
# Readiness sub-checks (private to this module)
# ---------------------------------------------------------------------------


async def _check_quality_criteria(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """Check quality criteria."""
    if agent.quality_agent:
        return await agent.quality_agent.process(
            {"action": "assess_release_quality", "release_id": release_id}
        )
    return {"passed": True, "test_pass_rate": 100.0}


async def _check_approval_status(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """Check approval status."""
    if agent.approval_agent:
        response = await agent.approval_agent.process(
            {
                "request_type": "release_readiness",
                "request_id": release_id,
            }
        )
        if isinstance(response, dict) and "complete" not in response:
            status = response.get("status")
            response["complete"] = status == "approved"
        return response
    return {"complete": True, "approvals": []}


async def _check_change_approvals(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """Check change approvals."""
    if agent.change_agent:
        return await agent.change_agent.process(
            {"action": "check_release_changes", "release_id": release_id}
        )
    return {"approved": True, "change_requests": []}


async def _check_risk_level(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """Check risk level."""
    if agent.risk_agent:
        return await agent.risk_agent.process(
            {"action": "assess_release_risk", "release_id": release_id}
        )
    return {"acceptable": True, "risk_score": 0.2}


async def _check_compliance_requirements(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    """Check compliance requirements."""
    if agent.compliance_agent:
        return await agent.compliance_agent.process(
            {"action": "verify_release_compliance", "release_id": release_id}
        )
    return {"met": True, "requirements": []}
