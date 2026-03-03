"""Action handler: map_controls_to_project"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_utils import (
    build_project_profile,
    generate_mapping_id,
    matches_regulation,
)

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_map_controls_to_project(
    agent: ComplianceRegulatoryAgent,
    project_id: str,
    mapping_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Map controls to project.

    Returns mapping ID and control checklist.
    """
    agent.logger.info("Mapping controls to project: %s", project_id)

    project_profile = build_project_profile(project_id, mapping_data)

    # Determine applicable regulations
    applicable_regulations = await _determine_applicable_regulations(
        agent, project_id, project_profile
    )

    # Get all controls for applicable regulations
    applicable_controls = []
    for regulation_id in applicable_regulations:
        regulation = agent.regulation_library.get(regulation_id)
        if regulation:
            applicable_controls.extend(regulation.get("related_controls", []))

    # Create compliance mapping
    mapping_id = await generate_mapping_id()

    mapping = {
        "mapping_id": mapping_id,
        "project_id": project_id,
        "process_id": mapping_data.get("process_id"),
        "project_profile": project_profile,
        "applicable_regulations": applicable_regulations,
        "applicable_controls": applicable_controls,
        "control_status": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Initialize control status
    for control_id in applicable_controls:
        mapping["control_status"][control_id] = {  # type: ignore
            "implementation_status": "Not Started",
            "evidence_uploaded": False,
            "last_tested": None,
            "test_result": None,
        }

    policy_decision = await agent._evaluate_control_mapping_policy(
        project_id=project_id,
        mapping=mapping,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    mapping["policy_decision"] = policy_decision

    # Store mapping
    agent.compliance_mappings[project_id] = mapping

    # Persist to database
    await agent.db_service.store("compliance_mappings", mapping_id, mapping)

    return {
        "mapping_id": mapping_id,
        "project_id": project_id,
        "applicable_regulations": len(applicable_regulations),
        "applicable_regulation_ids": applicable_regulations,
        "applicable_controls": len(applicable_controls),
        "applicable_control_ids": applicable_controls,
        "policy_decision": policy_decision,
        "compliance_checklist": [
            {
                "control_id": c_id,
                "description": agent.control_registry.get(c_id, {}).get("description"),
                "status": "Not Started",
            }
            for c_id in applicable_controls
        ],
    }


async def _determine_applicable_regulations(
    agent: ComplianceRegulatoryAgent,
    project_id: str,
    project_profile: dict[str, Any],
) -> list[str]:
    """Determine which regulations apply to project."""
    applicable = []
    for regulation_id, regulation in agent.regulation_library.items():
        if matches_regulation(project_profile, regulation):
            applicable.append(regulation_id)

    if not applicable:
        return list(agent.regulation_library.keys())[:3]
    return applicable
