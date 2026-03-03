"""Action handler: test_control"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from compliance_utils import calculate_next_test_date

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_test_control(
    agent: ComplianceRegulatoryAgent, control_id: str, test_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Test control effectiveness.

    Returns test results and status.
    """
    agent.logger.info("Testing control: %s", control_id)

    control = agent.control_registry.get(control_id)
    if not control:
        raise ValueError(f"Control not found: {control_id}")

    # Perform control test
    test_result = test_data.get("result", "pass")
    test_notes = test_data.get("notes", "")
    tester = test_data.get("tester", "unknown")

    # Update control
    control["last_test_date"] = datetime.now(timezone.utc).isoformat()
    control["last_test_result"] = test_result
    control["last_tester"] = tester

    # Update project mapping if exists
    for project_id, mapping in agent.compliance_mappings.items():
        if control_id in mapping.get("control_status", {}):
            mapping["control_status"][control_id]["last_tested"] = control["last_test_date"]
            mapping["control_status"][control_id]["test_result"] = test_result

    # Persist control test result
    test_record_id = f"TST-{control_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    test_record = {
        "test_id": test_record_id,
        "control_id": control_id,
        "result": test_result,
        "notes": test_notes,
        "tester": tester,
        "tested_at": control["last_test_date"],
    }
    await agent.db_service.store("control_tests", test_record_id, test_record)

    return {
        "control_id": control_id,
        "test_result": test_result,
        "test_date": control["last_test_date"],
        "tester": tester,
        "next_test_date": await calculate_next_test_date(control),
        "notes": test_notes,
    }
