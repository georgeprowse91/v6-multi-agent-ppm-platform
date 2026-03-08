"""
Business Case & Investment Analysis Models

Service and infrastructure model classes for the BusinessCaseInvestmentAgent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BusinessCaseConfig:
    """Configuration model for BusinessCaseInvestmentAgent."""

    min_roi_threshold: float = 0.15
    max_payback_period: int = 36
    discount_rate: float = 0.10
    inflation_rate: float = 0.0
    currency_rates: dict[str, float] = field(default_factory=lambda: {"AUD": 1.0})
    simulation_iterations: int = 1000
    sensitivity_variations: list[float] = field(default_factory=lambda: [-0.2, -0.1, 0.0, 0.1, 0.2])
    comparison_window_years: int = 3
    embedding_dimensions: int = 128

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> BusinessCaseConfig:
        """Create a BusinessCaseConfig from a raw config dictionary."""
        return cls(
            min_roi_threshold=config.get("min_roi_threshold", 0.15),
            max_payback_period=config.get("max_payback_period", 36),
            discount_rate=config.get("discount_rate", 0.10),
            inflation_rate=config.get("inflation_rate", 0.0),
            currency_rates={
                code.upper(): float(rate)
                for code, rate in config.get("currency_rates", {"AUD": 1.0}).items()
            },
            simulation_iterations=int(config.get("simulation_iterations", 1000)),
            sensitivity_variations=config.get(
                "sensitivity_variations", [-0.2, -0.1, 0.0, 0.1, 0.2]
            ),
            comparison_window_years=config.get("comparison_window_years", 3),
            embedding_dimensions=config.get("embedding_dimensions", 128),
        )


@dataclass
class FinancialMetrics:
    """Computed financial metrics for a business case."""

    npv: float
    irr: float
    payback_period_months: int
    tco: float
    roi_percentage: float
    discount_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "npv": self.npv,
            "irr": self.irr,
            "payback_period_months": self.payback_period_months,
            "tco": self.tco,
            "roi_percentage": self.roi_percentage,
            "discount_rate": self.discount_rate,
        }


@dataclass
class BusinessCaseRecord:
    """Structured record for a generated business case."""

    business_case_id: str
    title: str | None
    project_type: str | None
    methodology: str
    created_at: str
    created_by: str
    status: str
    demand_id: str
    template: str
    document: dict[str, Any]
    financial_metrics: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_case_id": self.business_case_id,
            "title": self.title,
            "project_type": self.project_type,
            "methodology": self.methodology,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "status": self.status,
            "demand_id": self.demand_id,
            "template": self.template,
            "document": self.document,
            "financial_metrics": self.financial_metrics,
            "metadata": self.metadata,
        }
