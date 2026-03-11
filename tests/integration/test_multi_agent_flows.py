from __future__ import annotations

import pytest

try:
    import pytest_asyncio  # noqa: F401

    _has_pytest_asyncio = True
except ModuleNotFoundError:
    _has_pytest_asyncio = False

from response_orchestration_agent import ResponseOrchestrationAgent

pytestmark = pytest.mark.skipif(not _has_pytest_asyncio, reason="pytest-asyncio is not installed")


class EventCollector:
    async def publish(self, topic: str, payload: dict) -> None:
        return None


class MockConnector:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data or {}
        self.calls: list[dict] = []

    async def fetch(self, payload: dict) -> dict:
        self.calls.append(payload)
        return self.data


class MockAgent:
    def __init__(self, *, output: dict, connector: MockConnector | None = None) -> None:
        self.output = output
        self.connector = connector
        self.calls: list[dict] = []

    async def execute(self, payload: dict) -> dict:
        self.calls.append(payload)
        connector_data: dict = {}
        if self.connector:
            connector_data = await self.connector.fetch(payload)
        return {**self.output, **connector_data}


@pytest.fixture
async def orchestration_agent() -> ResponseOrchestrationAgent:
    orchestrator = ResponseOrchestrationAgent(config={"event_bus": EventCollector()})
    await orchestrator.initialize()
    return orchestrator


@pytest.mark.asyncio
async def test_portfolio_intake_to_business_case(
    orchestration_agent: ResponseOrchestrationAgent,
) -> None:
    intake_connector = MockConnector(data={"source": "demand-intake-agent"})
    business_case_connector = MockConnector(data={"source": "business-case"})

    demand_intake_agent = MockAgent(
        connector=intake_connector,
        output={
            "classification": "project",
            "demand_id": "DEM-4201",
            "title": "Portfolio optimization initiative",
        },
    )
    business_case_agent = MockAgent(
        connector=business_case_connector,
        output={
            "demand_id": "DEM-4201",
            "financial_metrics": {
                "estimated_cost": 125000,
                "estimated_benefits": 310000,
                "roi": 1.48,
            },
            "recommendation": "proceed",
        },
    )

    orchestration_agent.agent_registry = {
        "demand-intake-agent": demand_intake_agent,
        "business-case-agent": business_case_agent,
    }

    response = await orchestration_agent.process(
        {
            "routing": [
                {"agent_id": "demand-intake-agent", "action": "submit_request"},
                {
                    "agent_id": "business-case-agent",
                    "action": "generate_business_case",
                    "depends_on": ["demand-intake-agent"],
                },
            ],
            "parameters": {
                "request": {
                    "title": "Portfolio optimization initiative",
                    "description": "Improve portfolio health and return profile",
                    "business_objective": "Increase strategic value delivery",
                    "requester": "portfolio.lead",
                }
            },
            "query": "Intake demand and generate business case",
            "context": {"tenant_id": "tenant-a", "correlation_id": "corr-portfolio-1"},
        }
    )

    payload = response.model_dump()

    assert payload["execution_summary"]["successful"] == 2
    assert payload["execution_summary"]["failed"] == 0
    assert "demand-intake-agent" in payload["aggregated_response"]
    assert "business-case-agent" in payload["aggregated_response"]

    intake_response = payload["aggregated_response"]["demand-intake-agent"]
    business_case_response = payload["aggregated_response"]["business-case-agent"]
    assert intake_response["classification"] == "project"
    assert intake_response["demand_id"] == "DEM-4201"
    assert business_case_response["demand_id"] == intake_response["demand_id"]
    assert business_case_response["financial_metrics"]["roi"] > 0

    assert demand_intake_agent.calls and business_case_agent.calls
    assert intake_connector.calls and business_case_connector.calls


@pytest.mark.asyncio
async def test_project_definition_schedule_planning_resource_capacity_flow(
    orchestration_agent: ResponseOrchestrationAgent,
) -> None:
    project_definition_agent = MockAgent(
        output={"project_id": "PROJ-44", "scope_baseline": ["Discovery", "Build", "Rollout"]}
    )
    schedule_planning_agent = MockAgent(
        output={"project_id": "PROJ-44", "schedule_id": "SCH-44", "critical_path_days": 95}
    )
    resource_capacity_agent = MockAgent(
        output={"project_id": "PROJ-44", "resource_capacity": {"available_fte": 18, "gap_fte": 2}}
    )

    orchestration_agent.agent_registry = {
        "scope-definition-agent": project_definition_agent,
        "schedule-planning-agent": schedule_planning_agent,
        "resource-management-agent": resource_capacity_agent,
    }

    response = await orchestration_agent.process(
        {
            "routing": [
                {"agent_id": "scope-definition-agent", "action": "generate_charter"},
                {
                    "agent_id": "schedule-planning-agent",
                    "action": "generate_schedule",
                    "depends_on": ["scope-definition-agent"],
                },
                {
                    "agent_id": "resource-management-agent",
                    "action": "analyze_capacity",
                    "depends_on": ["schedule-planning-agent"],
                },
            ],
            "parameters": {"project_name": "Apollo"},
            "query": "Define project and validate schedule/resource readiness",
            "context": {"tenant_id": "tenant-a", "correlation_id": "corr-delivery-1"},
        }
    )

    payload = response.model_dump()

    assert payload["execution_summary"]["successful"] == 3
    assert payload["execution_summary"]["failed"] == 0
    assert payload["aggregated_response"]["scope-definition-agent"]["project_id"] == "PROJ-44"
    assert payload["aggregated_response"]["schedule-planning-agent"]["schedule_id"] == "SCH-44"
    assert (
        payload["aggregated_response"]["resource-management-agent"]["resource_capacity"]["gap_fte"]
        == 2
    )


@pytest.mark.asyncio
async def test_risk_management_compliance_approval_flow(
    orchestration_agent: ResponseOrchestrationAgent,
) -> None:
    risk_agent = MockAgent(output={"risk_register_id": "RISK-77", "highest_risk": "Vendor delay"})
    compliance_agent = MockAgent(
        output={"compliance_assessment_id": "COMP-77", "status": "conditional"}
    )
    approval_agent = MockAgent(
        output={"approval_id": "APR-77", "status": "approved", "conditions": ["monthly audit"]}
    )

    orchestration_agent.agent_registry = {
        "risk-management-agent": risk_agent,
        "compliance-governance-agent": compliance_agent,
        "approval-workflow-agent": approval_agent,
    }

    response = await orchestration_agent.process(
        {
            "routing": [
                {"agent_id": "risk-management-agent", "action": "assess_risks"},
                {
                    "agent_id": "compliance-governance-agent",
                    "action": "run_compliance_check",
                    "depends_on": ["risk-management-agent"],
                },
                {
                    "agent_id": "approval-workflow-agent",
                    "action": "submit_for_approval",
                    "depends_on": ["compliance-governance-agent"],
                },
            ],
            "parameters": {"project_id": "PROJ-77"},
            "query": "Validate risk, compliance, and approval",
            "context": {"tenant_id": "tenant-b", "correlation_id": "corr-governance-1"},
        }
    )

    payload = response.model_dump()

    assert payload["execution_summary"]["successful"] == 3
    assert payload["execution_summary"]["failed"] == 0
    assert payload["aggregated_response"]["risk-management-agent"]["risk_register_id"] == "RISK-77"
    assert payload["aggregated_response"]["compliance-governance-agent"]["status"] == "conditional"
    assert payload["aggregated_response"]["approval-workflow-agent"]["status"] == "approved"
