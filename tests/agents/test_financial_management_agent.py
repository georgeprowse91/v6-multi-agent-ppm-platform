import pytest

from financial_management_agent import FinancialManagementAgent


@pytest.mark.asyncio
async def test_financial_exchange_rates_and_profitability():
    agent = FinancialManagementAgent(
        config={"exchange_rate_fixture": "data/fixtures/exchange_rates.json"}
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
        config={"exchange_rate_fixture": "data/fixtures/exchange_rates.json"}
    )
    await agent.initialize()

    async def _mock_history(project_id):
        return [
            {"amount": 1000, "currency": "USD"},
            {"amount": 1000, "currency": "EUR"},
        ]

    monkeypatch.setattr(agent, "_get_historical_spending", _mock_history)

    forecast = await agent._generate_forecast("proj-1", {})
    assert forecast["forecast"]["currency"] == "USD"
