"""
Business Case & Investment Analysis Agent

Purpose:
Develops comprehensive business cases for proposed projects or change initiatives.
Performs financial analysis and ROI modelling to support investment decisions.

Specification: agents/portfolio-management/business-case-agent/README.md
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from business_case_actions import (
    calculate_roi,
    compare_to_historical,
    generate_business_case,
    generate_recommendation,
    get_business_case,
    run_scenario_analysis,
)
from business_case_utils import (
    build_cash_flow,
    calculate_confidence,
    calculate_payback_period,
    calculate_roi_percentage,
    calculate_tco,
    convert_currency_inputs,
    inflate_adjust_cash_flows,
    irr_from_cash_flows,
    npv_from_cash_flows,
    run_monte_carlo_simulation,
    run_sensitivity_analysis,
)
from data_quality.helpers import apply_rule_set, validate_against_schema
from events import BusinessCaseCreatedEvent, InvestmentRecommendationEvent
from feature_flags import is_feature_enabled
from observability.tracing import get_trace_id

from agents.common.integration_services import (
    DataConnector,
    FaissBackedVectorSearchIndex,
    ForecastingModel,
    LocalEmbeddingService,
    NaiveBayesTextClassifier,
    NotificationService,
)
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class BusinessCaseInvestmentAgent(BaseAgent):
    """
    Business Case & Investment Analysis Agent - Develops business cases and performs ROI analysis.

    Key Capabilities:
    - Business case generation using configurable templates
    - Cost-benefit and ROI analysis (NPV, payback period, TCO)
    - Scenario modelling and sensitivity analysis
    - Comparative analysis against historical projects
    - Investment recommendations with confidence levels
    - Market analysis integration
    """

    def __init__(self, agent_id: str = "business-case-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.templates = config.get("templates", {}) if config else {}
        self.min_roi_threshold = config.get("min_roi_threshold", 0.15) if config else 0.15
        self.max_payback_period = config.get("max_payback_period", 36) if config else 36
        self.financial_settings = self._load_financial_settings(config or {})
        self.discount_rate = float(
            (config or {}).get("discount_rate", self.financial_settings.get("discount_rate", 0.10))
        )
        self.inflation_rate = float(
            (config or {}).get("inflation_rate", self.financial_settings.get("inflation_rate", 0.0))
        )
        self.currency_rates = {
            code.upper(): float(rate)
            for code, rate in self.financial_settings.get("currency_rates", {"AUD": 1.0}).items()
        }
        self.simulation_iterations = int(self.financial_settings.get("simulation_iterations", 1000))
        self.sensitivity_variations = self.financial_settings.get(
            "sensitivity_variations", [-0.2, -0.1, 0.0, 0.1, 0.2]
        )
        self.comparison_window_years = config.get("comparison_window_years", 3) if config else 3

        store_path = (
            Path(config.get("business_case_store_path", "data/business_case_store.json"))
            if config
            else Path("data/business_case_store.json")
        )
        self.business_case_store = TenantStateStore(store_path)
        self.financial_models = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.notification_service = NotificationService(self.event_bus)
        self.data_connector = DataConnector(config.get("data_sources") if config else None)
        self.embedding_service = LocalEmbeddingService(
            dimensions=config.get("embedding_dimensions", 128) if config else 128
        )
        self.vector_index = FaissBackedVectorSearchIndex(
            self.embedding_service,
            index_name="business_case",
        )
        self.forecasting_model = ForecastingModel()
        self.template_classifier = NaiveBayesTextClassifier(
            labels=["it", "operations", "finance", "customer", "general"]
        )
        self.openai_client = config.get("openai_client") if config else None
        self.erp_client = config.get("erp_client") if config else None
        self.crm_client = config.get("crm_client") if config else None
        self.market_client = config.get("market_client") if config else None
        self.roi_schema_path = Path(
            config.get("roi_schema_path", "data/schemas/roi.schema.json")
            if config
            else "data/schemas/roi.schema.json"
        )
        self.roi_rule_set = {
            "rules": [
                {
                    "id": "roi-inputs-required",
                    "checks": [
                        {"field": "roi.costs.total_cost", "type": "required"},
                        {"field": "roi.benefits.total_benefits", "type": "required"},
                    ],
                },
                {
                    "id": "roi-values-non-negative",
                    "checks": [
                        {"field": "roi.costs.total_cost", "type": "min", "value": 0},
                        {"field": "roi.benefits.total_benefits", "type": "min", "value": 0},
                    ],
                },
            ]
        }

    def _load_financial_settings(self, config: dict[str, Any]) -> dict[str, Any]:
        settings_path = Path(
            config.get(
                "business_case_settings_path", "ops/config/agents/business-case-settings.yaml"
            )
        )
        defaults: dict[str, Any] = {
            "discount_rate": 0.10,
            "inflation_rate": 0.0,
            "currency_rates": {"AUD": 1.0},
            "simulation_iterations": 1000,
            "sensitivity_variations": [-0.2, -0.1, 0.0, 0.1, 0.2],
        }
        if not settings_path.exists():
            return defaults

        loaded = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
        defaults.update(loaded)
        return defaults

    def _autonomous_deliverables_enabled(self) -> bool:
        if self.config and "autonomous_deliverables" in self.config:
            return bool(self.config.get("autonomous_deliverables"))
        environment = os.getenv("ENVIRONMENT", "dev")
        return is_feature_enabled("autonomous_deliverables", environment=environment, default=False)

    def _serialize_business_case(self, business_case: dict[str, Any]) -> str:
        document = business_case.get("document", {})
        return (
            f"Executive Summary\n{document.get('executive_summary', '')}\n\n"
            f"Problem Statement\n{document.get('problem_statement', '')}\n\n"
            f"Proposed Solution\n{document.get('proposed_solution', '')}\n\n"
            f"Financial Analysis\n{document.get('financial_analysis', '')}\n\n"
            f"Market Analysis\n{document.get('market_analysis', '')}\n\n"
            f"Risks and Mitigations\n{document.get('risks_and_mitigations', '')}\n\n"
            f"Implementation Approach\n{document.get('implementation_approach', '')}"
        )

    def _build_document_entity(
        self, business_case: dict[str, Any], *, correlation_id: str
    ) -> dict[str, Any]:
        created_at = business_case.get("created_at") or datetime.now(timezone.utc).isoformat()
        title = business_case.get("title") or "Business Case"
        project_type = business_case.get("project_type") or "general"
        provenance = {
            "sourceAgent": self.agent_id,
            "generatedAt": created_at,
            "correlationId": correlation_id,
            "inputContext": {
                "demand_id": business_case.get("demand_id", "unknown"),
                "project_type": project_type,
            },
        }
        return {
            "title": f"{title} Business Case",
            "content": self._serialize_business_case(business_case),
            "author": business_case.get("created_by", "unknown"),
            "project_id": business_case.get("demand_id", "unknown"),
            "tags": ["business-case", project_type],
            "metadata": {
                "business_case_id": business_case.get("business_case_id", ""),
                "status": business_case.get("status", "Draft"),
                "provenance": provenance,
            },
            "source": "agent_output",
            "status": business_case.get("status", "Draft"),
        }

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Business Case & Investment Analysis Agent...")

        template_training = [
            ("upgrade ERP finance module", "finance"),
            ("customer experience portal", "customer"),
            ("cloud infrastructure modernization", "it"),
            ("warehouse automation and robotics", "operations"),
            ("general improvement initiative", "general"),
        ]
        self.template_classifier.fit(template_training)
        existing_cases = self.business_case_store.list("default")
        for item in existing_cases:
            text = f"{item.get('title','')} {item.get('project_type','')} {item.get('template','')}"
            if item.get("business_case_id"):
                self.vector_index.add(item["business_case_id"], text, item)

        self.logger.info("Business Case & Investment Analysis Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "generate_business_case",
            "calculate_roi",
            "run_scenario_analysis",
            "compare_to_historical",
            "generate_recommendation",
            "get_business_case",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "generate_business_case":
            request_data = input_data.get("request", {})
            required_fields = [
                "title",
                "description",
                "project_type",
                "estimated_cost",
                "estimated_benefits",
            ]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        elif action == "calculate_roi":
            if not await self._validate_roi_inputs(input_data):
                return False

        elif action == "run_scenario_analysis":
            if "business_case_id" not in input_data or "scenarios" not in input_data:
                self.logger.warning("Missing business_case_id or scenarios")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process business case and investment analysis requests.

        Args:
            input_data: {
                "action": "generate_business_case" | "calculate_roi" | "run_scenario_analysis" |
                          "compare_to_historical" | "generate_recommendation" | "get_business_case",
                "request": Request data for business case generation,
                "business_case_id": ID of existing business case,
                "scenarios": List of scenario parameters,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - generate_business_case: Business case ID, document, financial metrics
            - calculate_roi: NPV, IRR, payback period, ROI
            - run_scenario_analysis: Scenario comparison results
            - compare_to_historical: Similar projects with outcomes
            - generate_recommendation: Recommendation with confidence level
            - get_business_case: Full business case details
        """
        action = input_data.get("action", "generate_business_case")
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"

        if action == "generate_business_case":
            return await generate_business_case(
                self,
                input_data.get("request", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "calculate_roi":
            return await calculate_roi(self, input_data)

        elif action == "run_scenario_analysis":
            return await run_scenario_analysis(
                self,
                input_data.get("business_case_id"),  # type: ignore
                input_data.get("scenarios", []),
            )

        elif action == "compare_to_historical":
            return await compare_to_historical(self, input_data.get("request", {}))

        elif action == "generate_recommendation":
            return await generate_recommendation(
                self,
                input_data.get("business_case_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_business_case":
            return await get_business_case(
                self,
                input_data.get("business_case_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _generate_business_case(
        self, request_data: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Delegate to the generation action handler."""
        return await generate_business_case(
            self, request_data, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _calculate_roi(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to the ROI action handler."""
        return await calculate_roi(self, input_data)

    async def _run_scenario_analysis(
        self, business_case_id: str, scenarios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Delegate to the ROI/scenario action handler."""
        return await run_scenario_analysis(self, business_case_id, scenarios)

    async def _compare_to_historical(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to the analysis action handler."""
        return await compare_to_historical(self, request_data)

    async def _generate_recommendation(
        self, business_case_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Delegate to the analysis action handler."""
        return await generate_recommendation(
            self, business_case_id, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _get_business_case(self, business_case_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Delegate to the query action handler."""
        return await get_business_case(self, business_case_id, tenant_id=tenant_id)

    # Helper methods

    async def _validate_roi_inputs(self, input_data: dict[str, Any]) -> bool:
        costs = input_data.get("costs", {})
        benefits = input_data.get("benefits", {})
        roi_payload = {"roi": {"costs": costs, "benefits": benefits}}

        errors = validate_against_schema(self.roi_schema_path, roi_payload)
        if errors:
            for error in errors:
                self.logger.warning("ROI schema error %s: %s", error.path, error.message)
            return False

        result = apply_rule_set(self.roi_rule_set, roi_payload)
        if not result.is_valid:
            for issue in result.issues:
                self.logger.warning("ROI data quality issue %s: %s", issue.rule_id, issue.message)
            return False

        return True

    async def _generate_business_case_id(self) -> str:
        """Generate unique business case ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"BC-{timestamp}"

    async def _select_template(self, request_data: dict[str, Any]) -> str:
        """Select appropriate business case template."""
        project_type = request_data.get("project_type", "general")
        methodology = request_data.get("methodology", "hybrid")

        template_key = f"{project_type}:{methodology}"
        if template_key in self.templates:
            return self.templates[template_key]
        label, _scores = self.template_classifier.predict(
            f"{request_data.get('title','')} {request_data.get('description','')}"
        )
        return self.templates.get(label, f"template_{project_type}_{methodology}")

    async def _gather_cost_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather cost data from ERP and other sources."""
        estimated_cost = request_data.get("estimated_cost", 0)
        erp_payload = self.data_connector.get_cost_data(request_data.get("project_type", "general"))
        if self.erp_client:
            erp_payload = {**erp_payload, **self.erp_client.get("costs", {})}  # type: ignore
        resource_costs = request_data.get("resource_costs", 0)
        labor_share = erp_payload.get("labor_share", 0.6)
        overhead_share = erp_payload.get("overhead_share", 0.2)
        material_share = erp_payload.get("material_share", 0.2)
        contingency_rate = erp_payload.get("contingency_rate", 0.1)

        return {
            "total_cost": estimated_cost + resource_costs,
            "labor_costs": estimated_cost * labor_share,
            "overhead_costs": estimated_cost * overhead_share,
            "material_costs": estimated_cost * material_share,
            "contingency": estimated_cost * contingency_rate,
            "operational_costs": erp_payload.get("operational_costs", estimated_cost * 0.15),
            "cash_flow": erp_payload.get("cash_flow"),
        }

    async def _gather_benefit_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather benefit data from CRM and other sources."""
        estimated_benefits = request_data.get("estimated_benefits", 0)
        crm_payload = self.data_connector.get_benefit_data(
            request_data.get("project_type", "general")
        )
        if self.crm_client:
            crm_payload = {**crm_payload, **self.crm_client.get("benefits", {})}  # type: ignore

        return {
            "total_benefits": estimated_benefits,
            "revenue_increase": estimated_benefits * crm_payload.get("revenue_share", 0.5),
            "cost_savings": estimated_benefits * crm_payload.get("savings_share", 0.3),
            "risk_reduction": estimated_benefits * crm_payload.get("risk_share", 0.2),
            "cash_flow": crm_payload.get("cash_flow"),
        }

    async def _gather_market_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather market data from external providers."""
        market_key = request_data.get("market", request_data.get("project_type", "general"))
        market_data = self.data_connector.get_market_data(market_key)
        if self.market_client:
            market_data = {**market_data, **self.market_client.get("market_data", {})}  # type: ignore
        return {
            "market_size": market_data.get("market_size", "Unknown"),
            "growth_rate": market_data.get("growth_rate", "Unknown"),
            "competitive_landscape": market_data.get("competitive_landscape", "Unknown"),
            "drivers": market_data.get("drivers", []),
            "risks": market_data.get("risks", []),
        }

    async def _generate_executive_summary(
        self, request_data: dict[str, Any], cost_data: dict[str, Any], benefit_data: dict[str, Any]
    ) -> str:
        """Generate executive summary using AI."""
        title = request_data.get("title", "Unnamed Project")
        total_cost = cost_data.get("total_cost", 0)
        total_benefits = benefit_data.get("total_benefits", 0)

        return (
            f"This business case proposes {title} with an estimated investment of ${total_cost:,.0f} "
            f"and projected benefits of ${total_benefits:,.0f}."
        )

    async def _generate_problem_statement(self, request_data: dict[str, Any]) -> str:
        """Generate problem statement."""
        description = request_data.get("description", "")
        if not description:
            return "Problem statement to be defined."
        return description

    async def _generate_proposed_solution(self, request_data: dict[str, Any]) -> str:
        """Generate proposed solution description."""
        solution = request_data.get("proposed_solution")
        if solution:
            return solution
        return "Solution to be defined with stakeholder inputs."

    async def _calculate_financial_metrics(
        self, cost_data: dict[str, Any], benefit_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate comprehensive financial metrics."""
        metrics = await self._calculate_roi({"costs": cost_data, "benefits": benefit_data})
        historical_benefits = benefit_data.get("historical_benefits", [])
        forecast = []
        if isinstance(historical_benefits, list) and historical_benefits:
            forecast = self.forecasting_model.forecast(historical_benefits, periods=3)

        return {
            "metrics": metrics,
            "cost_breakdown": cost_data,
            "benefit_breakdown": benefit_data,
            "benefit_forecast": forecast,
        }

    async def _identify_risks(self, request_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify and assess risks."""
        description = (request_data.get("description") or "").lower()
        risks = []
        if "vendor" in description or "supplier" in description:
            risks.append(
                {
                    "risk": "Vendor dependency",
                    "likelihood": "medium",
                    "impact": "high",
                    "mitigation": "Include exit clauses and diversified suppliers",
                }
            )
        if "integration" in description:
            risks.append(
                {
                    "risk": "Integration complexity",
                    "likelihood": "medium",
                    "impact": "medium",
                    "mitigation": "Allocate integration buffer and test cycles",
                }
            )
        if not risks:
            risks.append(
                {
                    "risk": "Implementation delay",
                    "likelihood": "medium",
                    "impact": "medium",
                    "mitigation": "Establish clear milestones and monitoring",
                }
            )
        risks.append(
            {
                "risk": "Cost overrun",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Include contingency buffer and regular cost reviews",
            }
        )
        return risks

    async def _generate_implementation_approach(self, request_data: dict[str, Any]) -> str:
        """Generate implementation approach."""
        methodology = request_data.get("methodology", "hybrid")

        if methodology == "adaptive":
            return "Iterative delivery with 2-week sprints, focusing on MVP and incremental value."
        elif methodology == "predictive":
            return "Phased approach with defined gates and deliverables at each stage."
        else:
            return "Hybrid approach combining adaptive delivery within predictive governance."

    def _build_cash_flow(self, costs: dict[str, Any], benefits: dict[str, Any]) -> list[float]:
        return build_cash_flow(costs, benefits, self.currency_rates)

    def _convert_currency_inputs(self, data: dict[str, Any]) -> dict[str, Any]:
        return convert_currency_inputs(data, self.currency_rates)

    def _inflate_adjust_cash_flows(self, cash_flows: list[float]) -> list[float]:
        return inflate_adjust_cash_flows(cash_flows, self.inflation_rate)

    def _irr(self, cash_flows: list[float]) -> float:
        return irr_from_cash_flows(cash_flows, self.inflation_rate)

    def _run_monte_carlo(
        self, costs: dict[str, Any], benefits: dict[str, Any], *, simulations: int
    ) -> dict[str, Any]:
        cash_flows = self._build_cash_flow(costs, benefits)
        return self.run_monte_carlo_simulation(cash_flows, simulations)

    def run_monte_carlo_simulation(
        self, cash_flows: list[float], iterations: int
    ) -> dict[str, float]:
        return run_monte_carlo_simulation(
            cash_flows, iterations, self.discount_rate, self.inflation_rate
        )

    def _run_sensitivity_analysis(
        self, costs: dict[str, Any], benefits: dict[str, Any]
    ) -> list[dict[str, float | str]]:
        return run_sensitivity_analysis(
            costs,
            benefits,
            self.currency_rates,
            self.discount_rate,
            self.inflation_rate,
            self.sensitivity_variations,
        )

    def _npv_sync(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        cash_flows = self._build_cash_flow(costs, benefits)
        return self._npv_from_cash_flows(cash_flows)

    def _npv_from_cash_flows(self, cash_flows: list[float]) -> float:
        return npv_from_cash_flows(cash_flows, self.discount_rate, self.inflation_rate)

    def _roi_sync(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        return calculate_roi_percentage(costs, benefits, self.currency_rates)

    async def _generate_recommendation_narrative(
        self, business_case: dict[str, Any], recommendation: str, rationale: str
    ) -> str:
        if self.openai_client:
            return (
                "AI-generated recommendation narrative is available via configured OpenAI client."
            )
        title = business_case.get("title", "the initiative")
        roi = business_case.get("financial_metrics", {}).get("roi_percentage", 0.0)
        npv = business_case.get("financial_metrics", {}).get("npv", 0.0)
        return (
            f"For {title}, the financial outlook indicates an ROI of {roi:.1%} with an NPV of "
            f"{npv:,.0f}. Recommendation: {recommendation}. {rationale}"
        )

    async def _calculate_npv(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        """Calculate Net Present Value."""
        cash_flows = self._build_cash_flow(costs, benefits)
        return self._npv_from_cash_flows(cash_flows)

    async def _calculate_irr(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        """Calculate Internal Rate of Return."""
        cash_flows = self._build_cash_flow(costs, benefits)
        return self._irr(cash_flows)

    async def _calculate_payback_period(
        self, costs: dict[str, Any], benefits: dict[str, Any]
    ) -> int:
        """Calculate payback period in months."""
        cash_flows = self._build_cash_flow(costs, benefits)
        return calculate_payback_period(cash_flows)

    async def _calculate_tco(self, costs: dict[str, Any]) -> float:
        """Calculate Total Cost of Ownership."""
        return calculate_tco(costs, self.currency_rates)

    async def _calculate_roi_percentage(
        self, costs: dict[str, Any], benefits: dict[str, Any]
    ) -> float:
        """Calculate ROI percentage."""
        return calculate_roi_percentage(costs, benefits, self.currency_rates)

    async def _adjust_costs(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Adjust costs based on scenario parameters."""
        base_cost = scenario.get("base_cost", scenario.get("parameters", {}).get("base_cost", 0))
        multiplier = scenario.get("parameters", {}).get("cost_multiplier", 1.0)
        return {"total_cost": base_cost * multiplier}

    async def _adjust_benefits(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Adjust benefits based on scenario parameters."""
        base_benefit = scenario.get(
            "base_benefit", scenario.get("parameters", {}).get("base_benefit", 0)
        )
        multiplier = scenario.get("parameters", {}).get("benefit_multiplier", 1.0)
        return {"total_benefits": base_benefit * multiplier}

    async def _compare_scenarios(self, scenario_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate scenario comparison summary."""
        return {
            "best_case": scenario_results[0]["scenario_name"] if scenario_results else None,
            "worst_case": scenario_results[-1]["scenario_name"] if scenario_results else None,
        }

    async def _select_best_scenario(self, scenario_results: list[dict[str, Any]]) -> str:
        """Select the best scenario based on metrics."""
        if not scenario_results:
            return "No scenarios available"

        # Select scenario with highest NPV
        best_scenario = max(scenario_results, key=lambda s: s["metrics"].get("npv", 0))
        return best_scenario["scenario_name"]  # type: ignore

    async def _calculate_confidence(
        self, metrics: dict[str, Any], historical_comparison: dict[str, Any]
    ) -> float:
        """Calculate confidence level for recommendation."""
        return calculate_confidence(metrics, historical_comparison, self.min_roi_threshold)

    async def _publish_business_case_created(
        self, business_case: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = BusinessCaseCreatedEvent(
            event_name="business_case.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "business_case_id": business_case.get("business_case_id", ""),
                "demand_id": business_case.get("demand_id", "unknown"),
                "project_name": business_case.get("title", ""),
                "created_at": datetime.fromisoformat(business_case.get("created_at")),
                "owner": business_case.get("created_by", "unknown"),
            },
        )
        await self.event_bus.publish("business_case.created", event.model_dump())

    async def _publish_investment_recommendation(
        self,
        business_case: dict[str, Any],
        recommendation: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> None:
        event = InvestmentRecommendationEvent(
            event_name="investment.recommendation",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "business_case_id": business_case.get("business_case_id", ""),
                "recommendation": recommendation.get("recommendation", "defer"),
                "confidence_level": recommendation.get("confidence_level", 0.0),
                "generated_at": datetime.fromisoformat(recommendation.get("generated_at")),
                "owner": business_case.get("created_by", "unknown"),
            },
        )
        await self.event_bus.publish("investment.recommendation", event.model_dump())

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Business Case & Investment Analysis Agent...")
        for client in (self.openai_client, self.erp_client, self.crm_client, self.market_client):
            close_method = getattr(client, "close", None)
            if callable(close_method):
                await close_method()  # type: ignore

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "business_case_generation",
            "cost_benefit_analysis",
            "roi_calculation",
            "scenario_modelling",
            "sensitivity_analysis",
            "comparative_analysis",
            "investment_recommendation",
            "market_analysis_integration",
            "financial_metrics_calculation",
            "npv_calculation",
            "irr_calculation",
            "payback_period_calculation",
            "tco_calculation",
        ]
