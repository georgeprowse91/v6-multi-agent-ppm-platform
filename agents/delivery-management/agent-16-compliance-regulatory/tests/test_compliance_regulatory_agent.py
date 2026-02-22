from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend([str(SRC_DIR), str(REPO_ROOT), str(REPO_ROOT / "packages")])

if "requests" not in sys.modules:
    requests_mock = types.SimpleNamespace(
        RequestException=Exception,
        get=lambda *args, **kwargs: None,
        post=lambda *args, **kwargs: None,
    )
    sys.modules["requests"] = requests_mock

if "observability.tracing" not in sys.modules:
    observability_module = types.ModuleType("observability")
    tracing_module = types.ModuleType("observability.tracing")

    def _get_trace_id() -> str:
        return "trace-id"

    def _start_agent_span(*_args: object, **_kwargs: object) -> object:
        class DummySpan:
            def __enter__(self) -> DummySpan:
                return self

            def __exit__(self, *_exc: object) -> None:
                return None

        return DummySpan()

    tracing_module.get_trace_id = _get_trace_id  # type: ignore[attr-defined]
    tracing_module.start_agent_span = _start_agent_span  # type: ignore[attr-defined]
    sys.modules["observability"] = observability_module
    sys.modules["observability.tracing"] = tracing_module

from compliance_regulatory_agent import ComplianceRegulatoryAgent


class DummyEvidenceAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    async def process(self, _request: dict[str, object]) -> dict[str, object]:
        return self.payload


class DummyEventBus:
    def subscribe(self, _topic: str, _handler: object) -> None:
        return None

    async def publish(self, _topic: str, _payload: dict[str, object]) -> None:
        return None


@pytest.mark.anyio
async def test_control_mapping_includes_applicable_regulations() -> None:
    agent = ComplianceRegulatoryAgent(
        config={"seed_frameworks": True, "event_bus": DummyEventBus()}
    )
    await agent.initialize()

    result = await agent._map_controls_to_project(
        "P-001",
        {"industry": "technology", "geography": "eu", "data_types": ["personal"]},
        tenant_id="tenant",
        correlation_id="corr",
    )

    regulations = result["applicable_regulation_ids"]
    assert "REG-PRIVACY-ACT-AU" in regulations
    assert "REG-SOC-2" in regulations
    assert "REG-ISO-27001" in regulations


@pytest.mark.anyio
async def test_assessment_uses_agent_evidence() -> None:
    evidence_agents = {
        "risk": DummyEvidenceAgent({"risk_mitigations": ["risk register updated"]}),
        "quality": DummyEvidenceAgent({"test_results": ["unit tests passed"]}),
        "release": DummyEvidenceAgent(
            {"audit_logs": ["deployment audit"], "deployment_logs": ["release ok"]}
        ),
    }
    agent = ComplianceRegulatoryAgent(
        config={
            "seed_frameworks": True,
            "agent_clients": evidence_agents,
            "event_bus": DummyEventBus(),
        }
    )
    await agent.initialize()

    await agent._map_controls_to_project(
        "P-002",
        {"industry": "technology", "geography": "global"},
        tenant_id="tenant",
        correlation_id="corr",
    )

    mapping = agent.compliance_mappings["P-002"]
    last_test = (datetime.utcnow() - timedelta(days=1)).isoformat()
    for status in mapping["control_status"].values():
        status["implementation_status"] = "Implemented"
        status["evidence_uploaded"] = True
        status["last_tested"] = last_test

    assessment = await agent._assess_compliance("P-002", {"tenant_id": "tenant"})
    assert assessment["compliance_score"] > 0
    assert assessment["control_assessments"]


@pytest.mark.anyio
async def test_report_generation_persists_report() -> None:
    agent = ComplianceRegulatoryAgent(
        config={"seed_frameworks": True, "event_bus": DummyEventBus()}
    )
    await agent.initialize()

    report = await agent._generate_compliance_report(
        "summary", {"project_id": "P-003", "industry": "finance", "geography": "global"}
    )
    report_id = report["report_id"]

    assert report_id in agent.compliance_reports
    assert report["report_type"] == "summary"
