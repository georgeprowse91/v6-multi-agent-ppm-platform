import pytest
from financial_management_agent import FinancialManagementAgent


@pytest.mark.asyncio
async def test_financial_exchange_rates_and_profitability():
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
        }
    )
    await agent.initialize()

    conversion = await agent._convert_currency(100, "EUR", "USD")
    assert conversion["converted_amount"] > 0

    npv = await agent._calculate_npv(1000, [400, 400, 400])
    irr = await agent._calculate_irr(1000, [400, 400, 400])

    assert npv != 0
    assert 0 < irr < 1


@pytest.mark.asyncio
async def test_financial_forecast_normalizes_currency(monkeypatch):
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
            "related_agent_fixtures": {
                "resource_plan": {"forecast_periods": 2},
                "schedule_progress": {"percent_complete": 0.4, "planned_percent": 0.5},
            },
        }
    )
    await agent.initialize()

    async def _mock_history(project_id):
        return [
            {"amount": 1000, "currency": "USD"},
            {"amount": 1000, "currency": "EUR"},
        ]

    monkeypatch.setattr(agent, "_get_historical_spending", _mock_history)

    forecast = await agent._generate_forecast("proj-1", {}, tenant_id="tenant-a")
    assert forecast["forecast"]["currency"] == "USD"


class ApprovalMock:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-1", "status": "pending"}


@pytest.mark.asyncio
async def test_financial_budget_persistence_and_approvals(tmp_path):
    approval_mock = ApprovalMock()
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
            "budget_store_path": tmp_path / "budgets.json",
            "approval_agent": approval_mock,
        }
    )
    await agent.initialize()

    create_response = await agent.process(
        {
            "action": "create_budget",
            "tenant_id": "tenant-a",
            "budget": {
                "project_id": "proj-1",
                "portfolio_id": "port-1",
                "total_amount": 1000,
                "cost_breakdown": {"labor": 1000},
                "owner": "finance-1",
                "currency": "USD",
                "name": "Budget FY25",
            },
        }
    )

    budget_id = create_response["budget_id"]
    assert create_response["data_quality"]["is_valid"] is True
    assert approval_mock.requests

    update_response = await agent.process(
        {
            "action": "update_budget",
            "tenant_id": "tenant-a",
            "budget_id": budget_id,
            "updates": {"total_amount": 1200},
        }
    )
    assert update_response["approval"]["status"] == "pending"

    approve_response = await agent.process(
        {
            "action": "approve_budget",
            "tenant_id": "tenant-a",
            "budget_id": budget_id,
        }
    )
    assert approve_response["status"] == "Approved"


@pytest.mark.asyncio
async def test_financial_validation_rejects_invalid_action():
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_financial_validation_rejects_missing_budget_fields():
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "create_budget", "budget": {"project_id": "X"}})

    assert valid is False


class EventBusMock:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_financial_cost_classification_and_accruals(monkeypatch):
    event_bus = EventBusMock()
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
            "event_bus": event_bus,
            "related_agent_fixtures": {
                "schedule_progress": {"percent_complete": 0.5, "planned_percent": 0.6},
                "resource_plan": {"baseline_cost": 1000, "current_cost": 1200},
            },
        }
    )
    await agent.initialize()

    async def _mock_transactions(project_id):
        return [
            {"amount": 500, "description": "vendor contract invoice", "project_id": project_id},
            {
                "amount": 200,
                "description": "flight and hotel",
                "project_id": project_id,
                "tax_region": "US",
            },
        ]

    async def _mock_budget(project_id, tenant_id):
        return {"project_id": project_id, "total_amount": 1000, "cost_breakdown": {"contracts": 500}}

    monkeypatch.setattr(agent, "_import_cost_transactions", _mock_transactions)
    monkeypatch.setattr(agent, "_get_budget_for_project", _mock_budget)

    response = await agent._track_costs(
        {"project_id": "proj-2"}, tenant_id="tenant-a", actor_id="user-1"
    )

    assert response["transactions_imported"] == 2
    assert "contracts" in response["by_category"]
    assert response["accruals"]["total_accruals"] >= 0
    assert event_bus.events


@pytest.mark.asyncio
async def test_financial_payback_period_calculation():
    agent = FinancialManagementAgent(
        config={
            "exchange_rate_fixture": "data/fixtures/exchange_rates.json",
            "tax_rate_fixture": "data/fixtures/tax_rates.json",
        }
    )
    await agent.initialize()

    payback = await agent._calculate_payback_period(500, [100, 150, 300])

    assert payback == 3
