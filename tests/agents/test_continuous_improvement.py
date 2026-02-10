import pytest

from process_mining_agent import ProcessMiningAgent

from tests.helpers.service_bus import build_test_event_bus


@pytest.mark.asyncio
async def test_ingest_analytics_report_creates_prioritized_backlog(tmp_path):
    event_bus = build_test_event_bus()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "improvement_backlog_store_path": tmp_path / "improvement_backlog.json",
            "improvement_history_store_path": tmp_path / "improvement_history.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    analytics_report = {
        "report_id": "RPT-MONTHLY-001",
        "period": "monthly",
        "recommendations": [
            "Reduce recurring scope changes through tighter change control",
            "Provide targeted training for estimation and planning",
            "Investigate budget variance root causes with finance",
        ],
        "anomalies": [{"metric": "cycle_time_days", "value": 28}],
        "trends": [{"pattern": "recurring_scope_creep", "count": 4}],
    }

    response = await agent.process(
        {
            "action": "ingest_analytics_report",
            "tenant_id": "tenant-ci",
            "analytics_report": analytics_report,
        }
    )

    assert response["created_items"] == 3
    prioritized = response["prioritized_backlog"]
    assert prioritized[0]["priority_score"] >= prioritized[1]["priority_score"]
    assert prioritized[1]["priority_score"] >= prioritized[2]["priority_score"]
    assert prioritized[0]["owner"] in {"pmo-lead", "finance-partner", "continuous-improvement-lead"}


@pytest.mark.asyncio
async def test_completed_improvement_history_is_persisted_and_retrievable(tmp_path):
    event_bus = build_test_event_bus()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "improvement_backlog_store_path": tmp_path / "improvement_backlog.json",
            "improvement_history_store_path": tmp_path / "improvement_history.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    ingest = await agent.process(
        {
            "action": "ingest_analytics_report",
            "tenant_id": "tenant-ci",
            "analytics_report": {
                "report_id": "RPT-MONTHLY-002",
                "period": "monthly",
                "recommendations": ["Provide targeted training for sprint planning"],
            },
        }
    )

    improvement_id = ingest["prioritized_backlog"][0]["improvement_id"]
    completed = await agent.process(
        {
            "action": "complete_improvement",
            "tenant_id": "tenant-ci",
            "improvement_id": improvement_id,
            "completed_by": "delivery-manager",
            "outcome": "Cycle time reduced by 12%",
        }
    )
    assert completed["status"] == "Completed"

    history = await agent.process(
        {
            "action": "get_improvement_history",
            "tenant_id": "tenant-ci",
        }
    )

    assert history["count"] >= 1
    assert any(entry["improvement_id"] == improvement_id for entry in history["entries"])
