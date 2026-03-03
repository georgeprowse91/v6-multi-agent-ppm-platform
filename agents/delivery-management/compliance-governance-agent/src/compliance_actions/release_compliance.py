"""Action handler: verify_release_compliance"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_verify_release_compliance(
    agent: ComplianceRegulatoryAgent,
    release_id: str | None,
    release_data: dict[str, Any],
) -> dict[str, Any]:
    from actions.assess_compliance import handle_assess_compliance

    project_id = release_data.get("project_id") or release_data.get("project") or "unknown"
    assessment = await handle_assess_compliance(
        agent,
        project_id,
        {
            "tenant_id": release_data.get("tenant_id", "unknown"),
            "correlation_id": release_data.get("correlation_id", str(uuid.uuid4())),
            "mapping": release_data.get("mapping", {}),
        },
    )
    threshold = (
        float(agent.config.get("release_compliance_threshold", 85)) if agent.config else 85
    )
    return {
        "release_id": release_id,
        "project_id": project_id,
        "compliance_score": assessment.get("compliance_score", 0),
        "compliance_met": assessment.get("compliance_score", 0) >= threshold,
        "gaps": assessment.get("gaps", []),
        "assessment_date": assessment.get("assessment_date"),
    }
