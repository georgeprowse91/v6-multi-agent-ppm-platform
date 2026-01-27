"""
Agent 5: Business Case & Investment Analysis Agent

Purpose:
Develops comprehensive business cases for proposed projects or change initiatives.
Performs financial analysis and ROI modelling to support investment decisions.

Specification: agents/portfolio-management/agent-05-business-case-investment/README.md
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from data_quality.helpers import apply_rule_set, validate_against_schema
from events import BusinessCaseCreatedEvent, InvestmentRecommendationEvent
from observability.tracing import get_trace_id

from agents.runtime import BaseAgent, InMemoryEventBus
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

    def __init__(
        self, agent_id: str = "business-case-investment", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.templates = config.get("templates", {}) if config else {}
        self.min_roi_threshold = config.get("min_roi_threshold", 0.15) if config else 0.15
        self.max_payback_period = config.get("max_payback_period", 36) if config else 36
        self.discount_rate = config.get("discount_rate", 0.10) if config else 0.10
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
            self.event_bus = InMemoryEventBus()
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

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Business Case & Investment Analysis Agent...")

        # Future work: Initialize Azure OpenAI Service for natural language generation
        # Future work: Initialize Azure Machine Learning for ROI prediction models
        # Future work: Connect to database for business case storage
        # Future work: Initialize ERP system connections (SAP, Oracle) for cost data
        # Future work: Initialize CRM connections (Salesforce) for revenue data
        # Future work: Connect to market data providers (Bloomberg, S&P Capital IQ)
        # Future work: Initialize document management system (SharePoint, Confluence)
        # Future work: Set up Azure Service Bus/Event Grid for event publishing

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
            self.logger.warning(f"Invalid action: {action}")
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
                    self.logger.warning(f"Missing required field: {field}")
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
            return await self._generate_business_case(
                input_data.get("request", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "calculate_roi":
            return await self._calculate_roi(input_data)

        elif action == "run_scenario_analysis":
            return await self._run_scenario_analysis(
                input_data.get("business_case_id"), input_data.get("scenarios", [])  # type: ignore
            )

        elif action == "compare_to_historical":
            return await self._compare_to_historical(input_data.get("request", {}))

        elif action == "generate_recommendation":
            return await self._generate_recommendation(
                input_data.get("business_case_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_business_case":
            return await self._get_business_case(
                input_data.get("business_case_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _generate_business_case(
        self, request_data: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Generate a comprehensive business case document.

        Returns business case ID and document structure.
        """
        self.logger.info("Generating business case")

        # Generate unique business case ID
        business_case_id = await self._generate_business_case_id()

        # Select appropriate template
        template = await self._select_template(request_data)

        # Gather data from external sources
        cost_data = await self._gather_cost_data(request_data)
        benefit_data = await self._gather_benefit_data(request_data)
        market_data = await self._gather_market_data(request_data)

        # Generate document sections using AI
        executive_summary = await self._generate_executive_summary(
            request_data, cost_data, benefit_data
        )
        problem_statement = await self._generate_problem_statement(request_data)
        proposed_solution = await self._generate_proposed_solution(request_data)

        # Calculate financial metrics
        financial_analysis = await self._calculate_financial_metrics(cost_data, benefit_data)

        # Identify and assess risks
        risks = await self._identify_risks(request_data)

        # Generate implementation approach
        implementation_approach = await self._generate_implementation_approach(request_data)

        # Create business case document
        business_case = {
            "business_case_id": business_case_id,
            "title": request_data.get("title"),
            "project_type": request_data.get("project_type"),
            "methodology": request_data.get("methodology", "hybrid"),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": request_data.get("requester", "unknown"),
            "status": "Draft",
            "demand_id": request_data.get("demand_id", "unknown"),
            "template": template,
            "document": {
                "executive_summary": executive_summary,
                "problem_statement": problem_statement,
                "proposed_solution": proposed_solution,
                "financial_analysis": financial_analysis,
                "market_analysis": market_data,
                "risks_and_mitigations": risks,
                "implementation_approach": implementation_approach,
            },
            "financial_metrics": financial_analysis.get("metrics", {}),
            "metadata": {
                "estimated_cost": cost_data.get("total_cost", 0),
                "estimated_benefits": benefit_data.get("total_benefits", 0),
                "created_at": datetime.utcnow().isoformat(),
            },
        }

        self.business_case_store.upsert(tenant_id, business_case_id, business_case)

        self.logger.info(f"Generated business case: {business_case_id}")

        await self._publish_business_case_created(
            business_case,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return {
            "business_case_id": business_case_id,
            "status": "Draft",
            "document": business_case["document"],
            "financial_metrics": business_case["financial_metrics"],
            "next_steps": "Review and edit the business case, then run scenario analysis or generate recommendation.",
        }

    async def _calculate_roi(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate ROI metrics including NPV, IRR, payback period, and TCO.

        Returns detailed financial metrics.
        """
        self.logger.info("Calculating ROI metrics")

        costs = input_data.get("costs", {})
        benefits = input_data.get("benefits", {})

        # Calculate Net Present Value (NPV)
        npv = await self._calculate_npv(costs, benefits)

        # Calculate Internal Rate of Return (IRR)
        irr = await self._calculate_irr(costs, benefits)

        # Calculate payback period
        payback_period = await self._calculate_payback_period(costs, benefits)

        # Calculate Total Cost of Ownership (TCO)
        tco = await self._calculate_tco(costs)

        # Calculate ROI percentage
        roi = await self._calculate_roi_percentage(costs, benefits)

        return {
            "npv": npv,
            "irr": irr,
            "payback_period_months": payback_period,
            "tco": tco,
            "roi_percentage": roi,
            "discount_rate": self.discount_rate,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    async def _run_scenario_analysis(
        self, business_case_id: str, scenarios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Run what-if scenario analysis with varying assumptions.

        Returns scenario comparison results.
        """
        self.logger.info(f"Running scenario analysis for business case: {business_case_id}")

        # Future work: Implement Monte Carlo simulation using Azure Machine Learning

        scenario_results: list[dict[str, Any]] = []

        for scenario in scenarios:
            scenario_name = scenario.get("name", "Unnamed Scenario")

            # Adjust costs and benefits based on scenario parameters
            adjusted_costs = await self._adjust_costs(scenario)
            adjusted_benefits = await self._adjust_benefits(scenario)

            # Recalculate financial metrics
            metrics = await self._calculate_roi(
                {"costs": adjusted_costs, "benefits": adjusted_benefits}
            )

            scenario_results.append(
                {
                    "scenario_name": scenario_name,
                    "parameters": scenario.get("parameters", {}),
                    "metrics": metrics,
                    "risk_level": scenario.get("risk_level", "medium"),
                }
            )

        # Generate comparison summary
        comparison = await self._compare_scenarios(scenario_results)

        return {
            "business_case_id": business_case_id,
            "scenarios": scenario_results,
            "comparison": comparison,
            "recommendation": await self._select_best_scenario(scenario_results),
        }

    async def _compare_to_historical(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Compare proposed initiative to historical projects for benchmarking.

        Returns similar projects with outcomes.
        """
        self.logger.info("Comparing to historical projects")

        # Future work: Use Azure Cognitive Search for similarity search
        # Future work: Use embedding models to find comparable business cases

        # Baseline: Return empty list for now
        similar_projects: list[dict[str, Any]] = []

        return {
            "similar_projects": similar_projects,
            "benchmark_roi": 0.0,
            "benchmark_payback": 0,
            "comparison_window_years": self.comparison_window_years,
        }

    async def _generate_recommendation(
        self, business_case_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Generate investment recommendation with confidence level.

        Returns recommendation (approve/defer/reject) with rationale.
        """
        self.logger.info(f"Generating recommendation for business case: {business_case_id}")

        business_case = self.business_case_store.get(tenant_id, business_case_id)
        if not business_case:
            raise ValueError(f"Business case not found: {business_case_id}")

        # Analyze financial metrics
        metrics = business_case.get("financial_metrics", {})
        roi = metrics.get("roi_percentage", 0)
        payback_period = metrics.get("payback_period_months", 999)
        npv = metrics.get("npv", 0)

        # Compare to historical projects
        historical_comparison = await self._compare_to_historical(business_case)

        # Calculate confidence level
        confidence = await self._calculate_confidence(metrics, historical_comparison)

        # Generate recommendation
        if roi >= self.min_roi_threshold and payback_period <= self.max_payback_period and npv > 0:
            recommendation = "approve"
            rationale = f"Strong financial metrics: ROI {roi:.1%}, payback period {payback_period} months, positive NPV"
        elif roi >= self.min_roi_threshold * 0.7:
            recommendation = "defer"
            rationale = (
                "Moderate financial metrics. Consider phased approach or MVP to reduce risk."
            )
        else:
            recommendation = "reject"
            rationale = f"Financial metrics below thresholds: ROI {roi:.1%} (required: {self.min_roi_threshold:.1%})"

        # Future work: Use Azure OpenAI to generate detailed narrative explanation

        recommendation_payload = {
            "business_case_id": business_case_id,
            "recommendation": recommendation,
            "confidence_level": confidence,
            "rationale": rationale,
            "phasing_suggestion": "Consider MVP approach" if recommendation == "defer" else None,
            "comparable_projects": historical_comparison.get("similar_projects", []),
            "generated_at": datetime.utcnow().isoformat(),
        }

        await self._publish_investment_recommendation(
            business_case,
            recommendation_payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return recommendation_payload

    async def _get_business_case(self, business_case_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve a business case by ID."""
        business_case = self.business_case_store.get(tenant_id, business_case_id)
        if not business_case:
            raise ValueError(f"Business case not found: {business_case_id}")
        return business_case  # type: ignore

    # Helper methods

    async def _validate_roi_inputs(self, input_data: dict[str, Any]) -> bool:
        costs = input_data.get("costs", {})
        benefits = input_data.get("benefits", {})
        roi_payload = {"roi": {"costs": costs, "benefits": benefits}}

        errors = validate_against_schema(self.roi_schema_path, roi_payload)
        if errors:
            for error in errors:
                self.logger.warning(f"ROI schema error {error.path}: {error.message}")
            return False

        result = apply_rule_set(self.roi_rule_set, roi_payload)
        if not result.is_valid:
            for issue in result.issues:
                self.logger.warning(f"ROI data quality issue {issue.rule_id}: {issue.message}")
            return False

        return True

    async def _generate_business_case_id(self) -> str:
        """Generate unique business case ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"BC-{timestamp}"

    async def _select_template(self, request_data: dict[str, Any]) -> str:
        """Select appropriate business case template."""
        project_type = request_data.get("project_type", "general")
        methodology = request_data.get("methodology", "hybrid")

        # Future work: Implement template selection logic based on configuration
        return f"template_{project_type}_{methodology}"

    async def _gather_cost_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather cost data from ERP and other sources."""
        # Future work: Query ERP systems for labor rates, overhead rates
        # Future work: Get resource costs from Resource Management Agent

        estimated_cost = request_data.get("estimated_cost", 0)

        return {
            "total_cost": estimated_cost,
            "labor_costs": estimated_cost * 0.6,
            "overhead_costs": estimated_cost * 0.2,
            "material_costs": estimated_cost * 0.2,
            "contingency": estimated_cost * 0.1,
        }

    async def _gather_benefit_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather benefit data from CRM and other sources."""
        # Future work: Query CRM for revenue opportunities
        # Future work: Get benefit estimates from request data

        estimated_benefits = request_data.get("estimated_benefits", 0)

        return {
            "total_benefits": estimated_benefits,
            "revenue_increase": estimated_benefits * 0.5,
            "cost_savings": estimated_benefits * 0.3,
            "risk_reduction": estimated_benefits * 0.2,
        }

    async def _gather_market_data(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Gather market data from external providers."""
        # Future work: Integrate with Bloomberg, S&P Capital IQ

        return {
            "market_size": "To be determined",
            "growth_rate": "To be determined",
            "competitive_landscape": "To be determined",
        }

    async def _generate_executive_summary(
        self, request_data: dict[str, Any], cost_data: dict[str, Any], benefit_data: dict[str, Any]
    ) -> str:
        """Generate executive summary using AI."""
        # Future work: Use Azure OpenAI for natural language generation

        title = request_data.get("title", "Unnamed Project")
        total_cost = cost_data.get("total_cost", 0)
        total_benefits = benefit_data.get("total_benefits", 0)

        return (
            f"This business case proposes {title} with an estimated investment of ${total_cost:,.0f} "
            f"and projected benefits of ${total_benefits:,.0f}."
        )

    async def _generate_problem_statement(self, request_data: dict[str, Any]) -> str:
        """Generate problem statement."""
        # Future work: Use Azure OpenAI for narrative generation
        return request_data.get("description", "Problem statement to be defined")  # type: ignore

    async def _generate_proposed_solution(self, request_data: dict[str, Any]) -> str:
        """Generate proposed solution description."""
        # Future work: Use Azure OpenAI for narrative generation
        return request_data.get("proposed_solution", "Solution to be defined")  # type: ignore

    async def _calculate_financial_metrics(
        self, cost_data: dict[str, Any], benefit_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate comprehensive financial metrics."""
        metrics = await self._calculate_roi({"costs": cost_data, "benefits": benefit_data})

        return {"metrics": metrics, "cost_breakdown": cost_data, "benefit_breakdown": benefit_data}

    async def _identify_risks(self, request_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify and assess risks."""
        # Future work: Use AI to identify risks from description
        # Future work: Integrate with Risk Management Agent

        return [
            {
                "risk": "Implementation delay",
                "likelihood": "medium",
                "impact": "medium",
                "mitigation": "Establish clear milestones and monitoring",
            },
            {
                "risk": "Cost overrun",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Include contingency buffer and regular cost reviews",
            },
        ]

    async def _generate_implementation_approach(self, request_data: dict[str, Any]) -> str:
        """Generate implementation approach."""
        methodology = request_data.get("methodology", "hybrid")

        if methodology == "agile":
            return "Iterative delivery with 2-week sprints, focusing on MVP and incremental value."
        elif methodology == "waterfall":
            return "Phased approach with defined gates and deliverables at each stage."
        else:
            return "Hybrid approach combining agile delivery within waterfall governance."

    async def _calculate_npv(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        """Calculate Net Present Value."""
        # Future work: Implement proper NPV calculation with cash flows
        total_cost = costs.get("total_cost", 0)
        total_benefits = benefits.get("total_benefits", 0)

        # Simplified NPV calculation (baseline)
        return total_benefits - total_cost  # type: ignore

    async def _calculate_irr(self, costs: dict[str, Any], benefits: dict[str, Any]) -> float:
        """Calculate Internal Rate of Return."""
        # Future work: Implement proper IRR calculation
        return 0.15  # Baseline

    async def _calculate_payback_period(
        self, costs: dict[str, Any], benefits: dict[str, Any]
    ) -> int:
        """Calculate payback period in months."""
        # Future work: Implement proper payback period calculation
        total_cost = costs.get("total_cost", 0)
        total_benefits = benefits.get("total_benefits", 0)

        if total_benefits == 0:
            return 999

        annual_benefit = total_benefits / 3  # Assume 3-year benefit period
        if annual_benefit == 0:
            return 999

        payback_years = total_cost / annual_benefit
        return int(payback_years * 12)

    async def _calculate_tco(self, costs: dict[str, Any]) -> float:
        """Calculate Total Cost of Ownership."""
        total_cost = float(costs.get("total_cost", 0))
        # Future work: Add ongoing operational costs
        return total_cost * 1.3  # Assume 30% ongoing costs

    async def _calculate_roi_percentage(
        self, costs: dict[str, Any], benefits: dict[str, Any]
    ) -> float:
        """Calculate ROI percentage."""
        total_cost = costs.get("total_cost", 0)
        total_benefits = benefits.get("total_benefits", 0)

        if total_cost == 0:
            return 0.0

        return (total_benefits - total_cost) / total_cost  # type: ignore

    async def _adjust_costs(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Adjust costs based on scenario parameters."""
        # Future work: Implement scenario-based cost adjustments
        return {"total_cost": 100000}  # Baseline

    async def _adjust_benefits(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Adjust benefits based on scenario parameters."""
        # Future work: Implement scenario-based benefit adjustments
        return {"total_benefits": 150000}  # Baseline

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
        # Future work: Use machine learning model to calculate confidence
        # Based on historical accuracy and metric quality

        return 0.75  # Baseline (75% confidence)

    async def _publish_business_case_created(
        self, business_case: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = BusinessCaseCreatedEvent(
            event_name="business_case.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
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
            timestamp=datetime.utcnow(),
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
        # Future work: Close database connections
        # Future work: Close external API connections
        # Future work: Flush any pending events

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
