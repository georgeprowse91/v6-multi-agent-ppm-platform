from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.extend([str(REPO_ROOT), str(AGENT_SRC)])

from process_mining_agent import ProcessMiningAgent  # noqa: E402


class DummyKnowledgeAgent:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def process(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(payload)
        return {"status": "ok"}


def _build_event(
    activity: str,
    timestamp: datetime,
    case_id: str,
    process_id: str = "process-1",
    project_id: str = "project-1",
    program_id: str = "program-1",
) -> dict[str, object]:
    return {
        "activity": activity,
        "timestamp": timestamp.isoformat(),
        "case_id": case_id,
        "process_id": process_id,
        "metadata": {"project_id": project_id, "program_id": program_id},
    }


def _build_agent(tmp_path: Path, knowledge_agent: DummyKnowledgeAgent | None = None) -> ProcessMiningAgent:
    return ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "process_model_store_path": tmp_path / "process_models.json",
            "conformance_store_path": tmp_path / "conformance.json",
            "recommendations_store_path": tmp_path / "recommendations.json",
            "event_bus": None,
            "knowledge_agent": knowledge_agent,
        }
    )


@pytest.mark.anyio
async def test_event_ingestion_stores_traces(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()
    base_time = datetime.utcnow()
    events = [
        _build_event("start", base_time, "case-1"),
        _build_event("review", base_time + timedelta(hours=1), "case-1"),
        _build_event("finish", base_time + timedelta(hours=2), "case-1"),
    ]

    result = await agent.process(
        {"action": "ingest_event_log", "tenant_id": "tenant-1", "events": events}
    )

    assert result["events_ingested"] == 3
    assert result["cases_identified"] == 1
    stored = agent.event_log_store.get("tenant-1", result["log_id"])
    assert stored is not None
    assert stored["event_count"] == 3


@pytest.mark.anyio
async def test_process_discovery_generates_models(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()
    base_time = datetime.utcnow()
    events = [
        _build_event("intake", base_time, "case-1"),
        _build_event("approve", base_time + timedelta(hours=2), "case-1"),
        _build_event("deploy", base_time + timedelta(hours=4), "case-1"),
    ]
    await agent.process(
        {"action": "ingest_event_log", "tenant_id": "tenant-1", "events": events}
    )

    result = await agent.process(
        {"action": "discover_process", "tenant_id": "tenant-1", "process_id": "process-1"}
    )

    assert result["activities"] == 3
    assert result["bpmn"]["type"] == "bpmn"
    assert result["petri_net"]["type"] == "petri_net"


@pytest.mark.anyio
async def test_conformance_checks_detect_deviations(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()
    base_time = datetime.utcnow()
    events = [
        _build_event("start", base_time, "case-1"),
        _build_event("unexpected", base_time + timedelta(hours=1), "case-1"),
        _build_event("finish", base_time + timedelta(hours=2), "case-1"),
    ]
    await agent.process(
        {"action": "ingest_event_log", "tenant_id": "tenant-1", "events": events}
    )

    expected_model = {
        "activities": ["start", "finish"],
        "transitions": [{"from": "start", "to": "finish"}],
    }
    report = await agent.process(
        {
            "action": "check_conformance",
            "tenant_id": "tenant-1",
            "process_id": "process-1",
            "expected_model": expected_model,
        }
    )

    assert report["compliance_rate"] < 100
    assert report["deviations"]


@pytest.mark.anyio
async def test_recommendations_publish_to_knowledge_agent(tmp_path: Path) -> None:
    knowledge_agent = DummyKnowledgeAgent()
    agent = _build_agent(tmp_path, knowledge_agent=knowledge_agent)
    await agent.initialize()
    base_time = datetime.utcnow()
    events = [
        _build_event("start", base_time, "case-1"),
        _build_event("review", base_time + timedelta(hours=5), "case-1"),
        _build_event("finish", base_time + timedelta(hours=9), "case-1"),
    ]
    await agent.process(
        {"action": "ingest_event_log", "tenant_id": "tenant-1", "events": events}
    )

    insights = await agent.process(
        {"action": "get_process_insights", "tenant_id": "tenant-1", "process_id": "process-1"}
    )

    assert insights["recommendations"]
    assert knowledge_agent.payloads
    payload = knowledge_agent.payloads[-1]
    assert payload["action"] == "ingest_agent_output"


@pytest.mark.anyio
async def test_compliance_rate_no_deviations_returns_100(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()

    compliance_rate = await agent._calculate_compliance_rate(
        deviations=[], total_expected_activities=5, total_cases=10
    )

    assert compliance_rate == 100.0


@pytest.mark.anyio
async def test_compliance_rate_mixed_severity_and_categories(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()

    deviations = [
        {"category": "skipped_activities", "severity": "critical"},
        {"category": "extra_activities", "severity": "low"},
        {"category": "unexpected_transition", "severity": "medium"},
    ]

    compliance_rate = await agent._calculate_compliance_rate(
        deviations=deviations, total_expected_activities=5, total_cases=1
    )

    # weighted_penalty = (1.4*2.0) + (0.6*0.5) + (1.2*1.0) = 4.3
    # denominator = 5 * 1 = 5 => compliance = (1 - 4.3/5) * 100 = 14.0
    assert compliance_rate == 14.0


@pytest.mark.anyio
async def test_compliance_rate_high_volume_with_small_deviation_ratio(tmp_path: Path) -> None:
    agent = _build_agent(tmp_path)
    await agent.initialize()

    deviations = [
        {"category": "extra_activities", "severity": "low"},
        {"category": "unexpected_transition", "severity": "medium"},
    ]

    compliance_rate = await agent._calculate_compliance_rate(
        deviations=deviations, total_expected_activities=20, total_cases=100
    )

    # weighted_penalty = (0.6*0.5) + (1.2*1.0) = 1.5
    # denominator = 20 * 100 = 2000 => compliance ~= 99.93
    assert compliance_rate == 99.93
