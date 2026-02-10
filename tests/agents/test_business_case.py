import random

import pytest

from business_case_investment_agent import BusinessCaseInvestmentAgent


class EventCollector:
    async def publish(self, topic: str, payload: dict) -> None:
        return None


@pytest.mark.asyncio
async def test_business_case_manual_financial_calculations_with_inflation_and_discount(tmp_path) -> None:
    settings_file = tmp_path / "business-case-settings.yaml"
    settings_file.write_text(
        """
discount_rate: 0.08
inflation_rate: 0.02
currency_rates:
  USD: 1.0
simulation_iterations: 100
""".strip()
    )
    agent = BusinessCaseInvestmentAgent(
        config={
            "event_bus": EventCollector(),
            "business_case_settings_path": str(settings_file),
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "calculate_roi",
            "costs": {"total_cost": 300, "cash_flow": [100, 100, 100], "currency": "USD"},
            "benefits": {
                "total_benefits": 510,
                "cash_flow": [150, 170, 190],
                "currency": "USD",
            },
        }
    )

    expected_cash_flows = [50.0, 70.0, 90.0]
    expected_npv = sum(
        (cash_flow / ((1 + 0.02) ** period)) / ((1 + 0.08) ** period)
        for period, cash_flow in enumerate(expected_cash_flows, start=1)
    )
    assert response["npv"] == pytest.approx(expected_npv, abs=0.01)
    assert response["assumptions"]["discount_rate"] == pytest.approx(0.08)
    assert response["assumptions"]["inflation_rate"] == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_business_case_monte_carlo_is_stable_with_seed(tmp_path) -> None:
    settings_file = tmp_path / "business-case-settings.yaml"
    settings_file.write_text(
        """
discount_rate: 0.1
inflation_rate: 0.0
currency_rates:
  USD: 1.0
simulation_iterations: 200
""".strip()
    )
    random.seed(7)
    agent = BusinessCaseInvestmentAgent(
        config={
            "event_bus": EventCollector(),
            "business_case_settings_path": str(settings_file),
        }
    )

    result = agent.run_monte_carlo_simulation([120.0, 130.0, 140.0], 200)

    assert result["iterations"] == 200
    assert result["mean_npv"] > 250
    assert result["stddev_npv"] > 0
    assert 0 <= result["negative_npv_probability"] <= 1


@pytest.mark.asyncio
async def test_business_case_currency_conversion_applies_rates(tmp_path) -> None:
    settings_file = tmp_path / "business-case-settings.yaml"
    settings_file.write_text(
        """
discount_rate: 0.1
inflation_rate: 0.0
currency_rates:
  USD: 1.0
  EUR: 1.2
simulation_iterations: 100
""".strip()
    )
    agent = BusinessCaseInvestmentAgent(
        config={
            "event_bus": EventCollector(),
            "business_case_settings_path": str(settings_file),
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "calculate_roi",
            "costs": {"total_cost": 1000, "horizon_years": 1, "currency": "EUR"},
            "benefits": {"total_benefits": 1500, "horizon_years": 1, "currency": "EUR"},
        }
    )

    expected_npv = ((1500 * 1.2) - (1000 * 1.2)) / 1.1
    assert response["npv"] == pytest.approx(expected_npv, abs=0.01)
    assert response["assumptions"]["currency_rates"]["EUR"] == pytest.approx(1.2)
