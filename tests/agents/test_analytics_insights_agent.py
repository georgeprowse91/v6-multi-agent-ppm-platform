import json

import pytest

from analytics_insights_agent import AnalyticsInsightsAgent


@pytest.mark.asyncio
async def test_analytics_persists_outputs_and_masks_lineage(tmp_path, monkeypatch):
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
        }
    )
    await agent.initialize()

    dashboard = await agent.process(
        {
            "action": "create_dashboard",
            "tenant_id": "tenant-analytics",
            "dashboard": {"name": "Exec View", "widgets": []},
        }
    )
    assert agent.analytics_output_store.get("tenant-analytics", dashboard["dashboard_id"])

    lineage = await agent.process(
        {
            "action": "update_data_lineage",
            "tenant_id": "tenant-analytics",
            "lineage": {
                "sources": ["crm"],
                "transformations": [{"actor": {"email": "jane.doe@example.com"}}],
                "target": "executive_summary",
            },
        }
    )

    stored_lineage = agent.analytics_lineage_store.get("tenant-analytics", lineage["lineage_id"])
    assert stored_lineage is not None
    assert "jane.doe@example.com" not in json.dumps(stored_lineage)
