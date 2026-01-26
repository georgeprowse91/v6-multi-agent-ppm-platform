import pytest

from compliance_regulatory_agent import ComplianceRegulatoryAgent


@pytest.mark.asyncio
async def test_compliance_regulatory_persists_evidence_and_policy_check(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    regulation = await agent.process(
        {
            "action": "add_regulation",
            "regulation": {"name": "SOX", "description": "Controls"},
        }
    )
    control = await agent.process(
        {
            "action": "define_control",
            "control": {
                "description": "Access control",
                "regulation": regulation["regulation_id"],
                "owner": "compliance-owner",
            },
        }
    )
    mapping = await agent.process(
        {
            "action": "map_controls_to_project",
            "tenant_id": "tenant-c",
            "project_id": "project-1",
            "mapping": {},
        }
    )
    assert mapping["policy_decision"]["decision"] in {"allow", "deny"}

    evidence = await agent.process(
        {
            "action": "upload_evidence",
            "tenant_id": "tenant-c",
            "control_id": control["control_id"],
            "evidence": {
                "file_name": "access_log.csv",
                "file_url": "https://example.com/access_log.csv",
            },
        }
    )
    assert agent.evidence_store.get("tenant-c", evidence["evidence_id"])
