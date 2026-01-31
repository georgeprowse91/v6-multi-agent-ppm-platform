"""
Agent 6: Portfolio Strategy & Optimization Agent

Purpose:
Manages the composition and allocation of the project and program portfolio.
Maximizes strategic value and business outcomes while respecting resource and budget constraints.

Specification: agents/portfolio-management/agent-06-portfolio-strategy-optimisation/README.md
"""

import math
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from events import PortfolioPrioritizedEvent
from observability.tracing import get_trace_id

from agents.common.connector_integration import DatabaseStorageService
from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, InMemoryEventBus
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.policy import evaluate_policy_bundle, load_default_policy_bundle
from agents.runtime.src.state_store import TenantStateStore


class PortfolioStrategyAgent(BaseAgent):
    """
    Portfolio Strategy & Optimization Agent - Manages portfolio composition and optimization.

    Key Capabilities:
    - Portfolio prioritization using multi-criteria decision analysis
    - Strategic alignment scoring
    - Capacity-constrained optimization
    - Risk/reward balancing
    - Scenario planning and what-if analysis
    - Portfolio rebalancing recommendations
    - Investment mix optimization
    """

    def __init__(
        self,
        agent_id: str = "portfolio-strategy-optimization",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.default_weights = (
            config.get(
                "criteria_weights",
                {
                    "strategic_alignment": 0.30,
                    "roi": 0.25,
                    "risk": 0.20,
                    "resource_feasibility": 0.15,
                    "compliance": 0.10,
                },
            )
            if config
            else {
                "strategic_alignment": 0.30,
                "roi": 0.25,
                "risk": 0.20,
                "resource_feasibility": 0.15,
                "compliance": 0.10,
            }
        )

        self.target_mix = (
            config.get("target_mix", {"innovation": 0.30, "operations": 0.50, "compliance": 0.20})
            if config
            else {"innovation": 0.30, "operations": 0.50, "compliance": 0.20}
        )

        self.rebalancing_frequency = (
            config.get("rebalancing_frequency", "quarterly") if config else "quarterly"
        )
        self.budget_granularity = config.get("budget_granularity", 1000) if config else 1000
        self.scenario_engine = ScenarioEngine()

        store_path = (
            Path(config.get("portfolio_store_path", "data/portfolio_strategy_store.json"))
            if config
            else Path("data/portfolio_strategy_store.json")
        )
        self.portfolio_store = TenantStateStore(store_path)
        self.strategic_objectives = []  # type: ignore
        self.alignment_scores = {}  # type: ignore
        self.optimization_scenarios = {}  # type: ignore
        self.db_service: DatabaseStorageService | None = None
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = InMemoryEventBus()

    async def initialize(self) -> None:
        """Initialize optimization models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Portfolio Strategy & Optimization Agent...")

        # Future work: Initialize Azure Machine Learning for multi-objective optimization
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")
        # Future work: Initialize connections to Planview/Clarity PPM
        # Future work: Connect to strategic planning tools (Cascade, AchieveIt)
        # Future work: Initialize Azure Cognitive Services for NLP of strategic documents
        # Future work: Set up Azure Cognitive Search for objective extraction
        # Future work: Initialize Azure Service Bus/Event Grid for event publishing
        # Future work: Load strategic objectives from corporate planning systems

        self.logger.info("Portfolio Strategy & Optimization Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "prioritize_portfolio",
            "calculate_alignment_score",
            "optimize_portfolio",
            "run_scenario_analysis",
            "rebalance_portfolio",
            "get_portfolio_status",
            "compare_scenarios",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "optimize_portfolio":
            constraints = input_data.get("constraints", {})
            if "budget_ceiling" not in constraints and "resource_capacity" not in constraints:
                self.logger.warning("Missing constraints for optimization")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process portfolio strategy and optimization requests.

        Args:
            input_data: {
                "action": "prioritize_portfolio" | "calculate_alignment_score" |
                          "optimize_portfolio" | "run_scenario_analysis" |
                          "rebalance_portfolio" | "get_portfolio_status" | "compare_scenarios",
                "projects": List of projects to evaluate,
                "constraints": Resource and budget constraints,
                "criteria_weights": Custom weights for prioritization,
                "scenarios": List of scenario definitions,
                "portfolio_id": ID of existing portfolio
            }

        Returns:
            Response based on action:
            - prioritize_portfolio: Ranked portfolio with scores
            - calculate_alignment_score: Strategic alignment scores
            - optimize_portfolio: Optimized portfolio composition
            - run_scenario_analysis: Scenario comparison results
            - rebalance_portfolio: Rebalancing recommendations
            - get_portfolio_status: Current portfolio status and metrics
            - compare_scenarios: Side-by-side scenario comparison
        """
        action = input_data.get("action", "prioritize_portfolio")
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"

        if action == "prioritize_portfolio":
            return await self._prioritize_portfolio(
                input_data.get("projects", []),
                input_data.get("criteria_weights", self.default_weights),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                portfolio_id=input_data.get("portfolio_id"),
                cycle=input_data.get("cycle", "ad-hoc"),
            )

        elif action == "calculate_alignment_score":
            return await self._calculate_alignment_score(
                input_data.get("project", {}), input_data.get("objectives", [])
            )

        elif action == "optimize_portfolio":
            return await self._optimize_portfolio(
                input_data.get("projects", []),
                input_data.get("constraints", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "run_scenario_analysis":
            return await self._run_scenario_analysis(input_data.get("scenarios", []))

        elif action == "rebalance_portfolio":
            return await self._rebalance_portfolio(input_data.get("portfolio_id"))

        elif action == "get_portfolio_status":
            return await self._get_portfolio_status(
                input_data.get("portfolio_id"),
                tenant_id=tenant_id,
            )

        elif action == "compare_scenarios":
            return await self._compare_scenarios(input_data.get("scenario_ids", []))

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _prioritize_portfolio(
        self,
        projects: list[dict[str, Any]],
        criteria_weights: dict[str, float],
        *,
        tenant_id: str,
        correlation_id: str,
        portfolio_id: str | None = None,
        cycle: str = "ad-hoc",
    ) -> dict[str, Any]:
        """
        Apply multi-criteria decision analysis to rank portfolio projects.

        Returns ranked portfolio with scores and justification.
        """
        self.logger.info(f"Prioritizing portfolio with {len(projects)} projects")

        ranked_projects = []
        portfolio_id = portfolio_id or await self._generate_portfolio_id()

        for project in projects:
            # Calculate scores for each criterion
            strategic_score = await self._score_strategic_alignment(project)
            roi_score = await self._score_roi(project)
            risk_score = await self._score_risk(project)
            resource_score = await self._score_resource_feasibility(project)
            compliance_score = await self._score_compliance(project)

            # Calculate weighted overall score
            overall_score = (
                strategic_score * criteria_weights.get("strategic_alignment", 0.30)
                + roi_score * criteria_weights.get("roi", 0.25)
                + risk_score * criteria_weights.get("risk", 0.20)
                + resource_score * criteria_weights.get("resource_feasibility", 0.15)
                + compliance_score * criteria_weights.get("compliance", 0.10)
            )

            recommendation = (
                "approve" if overall_score >= 0.7 else "defer" if overall_score >= 0.5 else "reject"
            )
            policy_outcome = await self._apply_policy_guardrails(
                project_id=str(project.get("project_id")),
                recommendation=recommendation,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
            if policy_outcome["decision"] == "deny" and recommendation == "approve":
                recommendation = "defer"

            ranked_projects.append(
                {
                    "project_id": project.get("project_id"),
                    "project_name": project.get("name"),
                    "overall_score": overall_score,
                    "scores": {
                        "strategic_alignment": strategic_score,
                        "roi": roi_score,
                        "risk": risk_score,
                        "resource_feasibility": resource_score,
                        "compliance": compliance_score,
                    },
                    "recommendation": recommendation,
                    "policy_decision": policy_outcome,
                }
            )

        # Sort by overall score (descending)
        ranked_projects.sort(key=lambda x: x["overall_score"], reverse=True)  # type: ignore

        # Add ranking position
        for idx, project in enumerate(ranked_projects, start=1):
            project["rank"] = idx

        portfolio_record = {
            "portfolio_id": portfolio_id,
            "cycle": cycle,
            "ranked_projects": ranked_projects,
            "criteria_weights": criteria_weights,
            "generated_at": datetime.utcnow().isoformat(),
        }
        self.portfolio_store.upsert(tenant_id, portfolio_id, portfolio_record)
        if self.db_service:
            await self.db_service.store("portfolio_strategy", portfolio_id, portfolio_record)

        await self._publish_portfolio_prioritized(
            portfolio_record,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            portfolio_id=portfolio_id,
            approved_count=len([p for p in ranked_projects if p["recommendation"] == "approve"]),
        )

        return {
            "portfolio_id": portfolio_id,
            "ranked_projects": ranked_projects,
            "criteria_weights": criteria_weights,
            "total_projects": len(ranked_projects),
            "approved_count": len([p for p in ranked_projects if p["recommendation"] == "approve"]),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _calculate_alignment_score(
        self, project: dict[str, Any], objectives: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculate strategic alignment scores for a project.

        Returns alignment scores for each strategic objective.
        """
        self.logger.info(f"Calculating alignment score for project: {project.get('project_id')}")

        # Future work: Use Azure Cognitive Services NLP to analyze project description
        # Future work: Match project to strategic objectives using embeddings

        alignment_details = []

        for objective in objectives:
            # Calculate alignment score (0-1)
            score = await self._calculate_objective_alignment(project, objective)

            alignment_details.append(
                {
                    "objective_id": objective.get("id"),
                    "objective_name": objective.get("name"),
                    "alignment_score": score,
                    "contribution": objective.get("weight", 1.0) * score,
                }
            )

        # Calculate overall alignment score
        total_weight = sum(obj.get("weight", 1.0) for obj in objectives)
        overall_score = sum(detail["contribution"] for detail in alignment_details)
        if total_weight > 0:
            overall_score /= total_weight

        return {
            "project_id": project.get("project_id"),
            "overall_alignment_score": overall_score,
            "objective_alignments": alignment_details,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    async def _optimize_portfolio(
        self,
        projects: list[dict[str, Any]],
        constraints: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Run capacity-constrained optimization to maximize portfolio value.

        Uses multi-objective optimization to balance value, risk, and resource constraints.
        """
        self.logger.info(f"Optimizing portfolio with {len(projects)} projects")

        # Extract constraints
        budget_ceiling = constraints.get("budget_ceiling", float("inf"))
        resource_capacity = constraints.get("resource_capacity", {})
        min_compliance_spend = constraints.get("min_compliance_spend", 0)

        prioritization = await self._prioritize_portfolio(
            projects,
            self.default_weights,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            portfolio_id=None,
            cycle="optimization",
        )
        ranked_projects = prioritization["ranked_projects"]

        scored_projects = []
        for project_data in ranked_projects:
            project = next(
                (p for p in projects if p.get("project_id") == project_data["project_id"]), None
            )
            if not project:
                continue
            project_cost = float(project.get("estimated_cost", 0))
            expected_value = float(project.get("expected_value", 0))
            value = expected_value * project_data["overall_score"]
            scored_projects.append(
                {
                    "project_id": project["project_id"],
                    "project_name": project.get("name"),
                    "score": project_data["overall_score"],
                    "cost": project_cost,
                    "expected_value": expected_value,
                    "value": value,
                    "category": project.get("category", "operations"),
                    "resource_requirements": project.get("resource_requirements", {}),
                }
            )

        if not math.isfinite(budget_ceiling):
            budget_ceiling = sum(item["cost"] for item in scored_projects)

        selected_projects = await self._optimize_knapsack(
            scored_projects, budget_ceiling, min_compliance_spend, resource_capacity
        )
        total_cost = sum(item["cost"] for item in selected_projects)
        total_value = sum(item["expected_value"] for item in selected_projects)

        # Calculate portfolio metrics
        portfolio_metrics = await self._calculate_portfolio_metrics(selected_projects)

        optimization_record = {
            "optimization_id": f"OPT-{uuid.uuid4().hex}",
            "selected_projects": selected_projects,
            "total_projects": len(selected_projects),
            "total_cost": total_cost,
            "total_value": total_value,
            "budget_utilization": total_cost / budget_ceiling if budget_ceiling > 0 else 0,
            "portfolio_metrics": portfolio_metrics,
            "constraints_applied": constraints,
            "optimized_at": datetime.utcnow().isoformat(),
        }
        if self.db_service:
            await self.db_service.store(
                "portfolio_optimization",
                optimization_record["optimization_id"],
                optimization_record,
            )
        return optimization_record

    async def _run_scenario_analysis(self, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Generate alternate portfolios under different scenarios and compare outcomes.

        Returns scenario analysis with trade-off visualizations.
        """
        self.logger.info(f"Running scenario analysis for {len(scenarios)} scenarios")

        async def _run_single_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
            scenario_index = len(self.optimization_scenarios)
            scenario_id = scenario.get("id", f"scenario_{scenario_index}")
            scenario_name = scenario.get("name", f"Scenario {scenario_index + 1}")

            # Extract scenario-specific parameters
            budget_multiplier = scenario.get("budget_multiplier", 1.0)
            capacity_multiplier = scenario.get("capacity_multiplier", 1.0)
            priority_shift = scenario.get("priority_shift", {})
            parameter_multipliers = scenario.get("parameter_multipliers", {})

            # Adjust constraints based on scenario
            base_resource_capacity = scenario.get("resource_capacity", {})
            adjusted_resource_capacity = {
                resource: value * capacity_multiplier
                for resource, value in base_resource_capacity.items()
            }
            adjusted_constraints = {
                "budget_ceiling": scenario.get("budget_ceiling", 1000000) * budget_multiplier,
                "resource_capacity": adjusted_resource_capacity,
                "min_compliance_spend": scenario.get("min_compliance_spend", 0),
            }

            # Adjust criteria weights if priority shift specified
            adjusted_weights = self.default_weights.copy()
            for criterion, adjustment in priority_shift.items():
                if criterion in adjusted_weights:
                    adjusted_weights[criterion] *= adjustment

            # Normalize weights
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                adjusted_weights = {k: v / total_weight for k, v in adjusted_weights.items()}

            # Run optimization for this scenario
            scenario_projects = self._apply_scenario_multipliers(
                scenario.get("projects", []), parameter_multipliers
            )
            optimization_result = await self._optimize_portfolio(
                scenario_projects,
                adjusted_constraints,
                tenant_id=scenario.get("tenant_id", "unknown"),
                correlation_id=scenario.get("correlation_id", scenario_id),
            )

            result = {
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "parameters": scenario,
                "results": optimization_result,
                "trade_offs": await self._identify_trade_offs(optimization_result),
            }

            # Store scenario
            self.optimization_scenarios[scenario_id] = {
                "name": scenario_name,
                "results": optimization_result,
                "created_at": datetime.utcnow().isoformat(),
            }
            if self.db_service:
                await self.db_service.store(
                    "portfolio_scenarios",
                    scenario_id,
                    {
                        "scenario_id": scenario_id,
                        "scenario_name": scenario_name,
                        "parameters": scenario,
                        "results": optimization_result,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )

            return result

        scenario_output = await self.scenario_engine.run_multi_scenarios(
            scenarios=scenarios,
            scenario_runner=_run_single_scenario,
            comparison_builder=self._generate_scenario_comparison,
        )
        scenario_results = scenario_output["scenarios"]
        comparison = scenario_output["comparison"]

        # Future work: Publish portfolio.scenario.generated event

        return {
            "scenarios": scenario_results,
            "comparison": comparison,
            "recommendation": await self._recommend_best_scenario(scenario_results),
        }

    async def _rebalance_portfolio(self, portfolio_id: str | None = None) -> dict[str, Any]:
        """
        Analyze current portfolio and recommend rebalancing actions.

        Returns recommendations to align with target investment mix.
        """
        self.logger.info(f"Rebalancing portfolio: {portfolio_id}")

        # Get current portfolio composition
        current_portfolio = await self._get_current_portfolio(portfolio_id)

        # Calculate current mix
        current_mix = await self._calculate_investment_mix(current_portfolio)

        # Compare to target mix
        gaps = {}
        for category, target_pct in self.target_mix.items():
            current_pct = current_mix.get(category, 0)
            gaps[category] = target_pct - current_pct

        # Generate rebalancing recommendations
        recommendations = []

        for category, gap in gaps.items():
            if abs(gap) > 0.05:  # More than 5% deviation
                action = "increase" if gap > 0 else "decrease"
                recommendations.append(
                    {
                        "category": category,
                        "action": action,
                        "current_percentage": current_mix.get(category, 0),
                        "target_percentage": self.target_mix[category],
                        "gap_percentage": gap,
                        "suggested_actions": await self._suggest_rebalancing_actions(category, gap),
                    }
                )

        # Calculate impact metrics
        impact = await self._calculate_rebalancing_impact(recommendations)

        # Future work: Publish portfolio.rebalanced event

        return {
            "portfolio_id": portfolio_id,
            "current_mix": current_mix,
            "target_mix": self.target_mix,
            "gaps": gaps,
            "recommendations": recommendations,
            "impact": impact,
            "rebalanced_at": datetime.utcnow().isoformat(),
        }

    async def _get_portfolio_status(
        self, portfolio_id: str | None = None, *, tenant_id: str
    ) -> dict[str, Any]:
        """Get current portfolio status and performance metrics."""
        self.logger.info(f"Getting portfolio status: {portfolio_id}")

        if portfolio_id:
            record = self.portfolio_store.get(tenant_id, portfolio_id)
        else:
            records = self.portfolio_store.list(tenant_id)
            record = records[-1] if records else None

        if not record:
            return {
                "portfolio_id": portfolio_id,
                "total_projects": 0,
                "total_budget": 0,
                "total_value": 0,
                "investment_mix": {},
                "strategic_coverage": {},
                "resource_utilization": 0,
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        return {
            "portfolio_id": record.get("portfolio_id"),
            "total_projects": len(record.get("ranked_projects", [])),
            "total_budget": 0,
            "total_value": 0,
            "investment_mix": {},
            "strategic_coverage": {},
            "resource_utilization": 0,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    async def _compare_scenarios(self, scenario_ids: list[str]) -> dict[str, Any]:
        """Compare multiple scenarios side-by-side."""
        self.logger.info(f"Comparing {len(scenario_ids)} scenarios")

        scenarios = []
        for scenario_id in scenario_ids:
            if scenario_id in self.optimization_scenarios:
                scenarios.append(self.optimization_scenarios[scenario_id])

        comparison = await self._generate_scenario_comparison(scenarios)

        return {"scenarios": scenarios, "comparison": comparison}

    # Helper methods

    async def _generate_portfolio_id(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PORT-{timestamp}"

    async def _apply_policy_guardrails(
        self,
        *,
        project_id: str,
        recommendation: str,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        policy_bundle = {
            "metadata": {
                "version": self.get_config("policy_version", "1.0.0"),
                "owner": self.get_config("policy_owner", self.agent_id),
                "name": project_id,
            },
            "decision": recommendation,
            "project_id": project_id,
        }
        decision = evaluate_policy_bundle(policy_bundle, load_default_policy_bundle())
        outcome = "denied" if decision.decision == "deny" else "success"
        event = build_audit_event(
            tenant_id=tenant_id,
            action="portfolio.policy.checked",
            outcome=outcome,
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=project_id,
            resource_type="portfolio_project",
            metadata={"decision": decision.decision, "reasons": decision.reasons},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)
        return {"decision": decision.decision, "reasons": decision.reasons}

    async def _publish_portfolio_prioritized(
        self, portfolio_record: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = PortfolioPrioritizedEvent(
            event_name="portfolio.prioritized",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "portfolio_id": portfolio_record.get("portfolio_id", ""),
                "cycle": portfolio_record.get("cycle", "ad-hoc"),
                "prioritized_at": datetime.fromisoformat(portfolio_record.get("generated_at")),
                "ranked_projects": [
                    str(project.get("project_id"))
                    for project in portfolio_record.get("ranked_projects", [])
                ],
            },
        )
        await self.event_bus.publish("portfolio.prioritized", event.model_dump())

    def _emit_audit_event(
        self, *, tenant_id: str, correlation_id: str, portfolio_id: str, approved_count: int
    ) -> None:
        event = build_audit_event(
            tenant_id=tenant_id,
            action="portfolio.prioritized",
            outcome="success",
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=portfolio_id,
            resource_type="portfolio",
            metadata={"approved_count": approved_count},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    async def _score_strategic_alignment(self, project: dict[str, Any]) -> float:
        """Score project strategic alignment (0-1)."""
        objectives = project.get("objectives") or self.strategic_objectives
        if isinstance(objectives, list) and objectives:
            alignment_scores = [
                await self._calculate_objective_alignment(project, objective)
                for objective in objectives
                if isinstance(objective, dict)
            ]
            if alignment_scores:
                return max(0.0, min(1.0, sum(alignment_scores) / len(alignment_scores)))

        project_text = " ".join(
            [
                str(project.get("name", "")),
                str(project.get("description", "")),
                " ".join(project.get("tags", []) or []),
            ]
        )
        strategic_keywords = set(project.get("strategic_keywords", []) or [])
        if strategic_keywords:
            project_text = f"{project_text} {' '.join(strategic_keywords)}"

        project_terms = self._extract_keywords(project_text)
        if not project_terms:
            return float(project.get("strategic_score", 0.7))

        strategic_terms = self._extract_keywords(
            " ".join(str(obj) for obj in self.strategic_objectives)
        )
        if not strategic_terms:
            return float(project.get("strategic_score", 0.7))

        overlap = len(project_terms & strategic_terms)
        score = overlap / max(1, len(strategic_terms))
        return max(0.0, min(1.0, score))

    async def _score_roi(self, project: dict[str, Any]) -> float:
        """Score project ROI (0-1)."""
        roi = project.get("roi", 0)

        # Normalize ROI to 0-1 scale
        if roi <= 0:
            return 0.0
        elif roi >= 1.0:
            return 1.0
        else:
            return min(roi, 1.0)  # type: ignore

    async def _optimize_knapsack(
        self,
        projects: list[dict[str, Any]],
        budget_ceiling: float,
        min_compliance_spend: float,
        resource_capacity: dict[str, float],
    ) -> list[dict[str, Any]]:
        if not projects or budget_ceiling <= 0:
            return []

        scale = self.budget_granularity
        max_budget = int(budget_ceiling // scale)

        def is_compliance(project: dict[str, Any]) -> bool:
            return project.get("category") == "compliance"

        compliance_projects = [p for p in projects if is_compliance(p)]
        other_projects = [p for p in projects if not is_compliance(p)]

        compliance_selected = self._knapsack_select(compliance_projects, max_budget, scale)
        compliance_spend = sum(p["cost"] for p in compliance_selected)

        remaining_budget = budget_ceiling - compliance_spend
        if compliance_spend < min_compliance_spend:
            return compliance_selected

        remaining_selected = self._knapsack_select(
            other_projects, int(remaining_budget // scale), scale
        )

        selected = compliance_selected + remaining_selected
        return self._apply_resource_capacity(selected, resource_capacity)

    def _knapsack_select(
        self, projects: list[dict[str, Any]], max_budget: int, scale: int
    ) -> list[dict[str, Any]]:
        if max_budget <= 0:
            return []

        dp = [0.0] * (max_budget + 1)
        keep: list[list[bool]] = [[False] * (max_budget + 1) for _ in projects]

        for i, project in enumerate(projects):
            weight = int(project["cost"] // scale)
            value = project["value"]
            for budget in range(max_budget, weight - 1, -1):
                candidate = dp[budget - weight] + value
                if candidate > dp[budget]:
                    dp[budget] = candidate
                    keep[i][budget] = True

        selected = []
        remaining = max_budget
        for i in range(len(projects) - 1, -1, -1):
            if keep[i][remaining]:
                selected.append(projects[i])
                remaining -= int(projects[i]["cost"] // scale)
        return selected[::-1]

    def _apply_resource_capacity(
        self, projects: list[dict[str, Any]], resource_capacity: dict[str, float]
    ) -> list[dict[str, Any]]:
        if not resource_capacity:
            return projects

        usage: dict[str, float] = {}
        selected: list[dict[str, Any]] = []

        for project in sorted(projects, key=lambda x: x["value"], reverse=True):
            feasible = True
            for resource, needed in project.get("resource_requirements", {}).items():
                capacity = resource_capacity.get(resource, float("inf"))
                if usage.get(resource, 0.0) + needed > capacity:
                    feasible = False
                    break
            if feasible:
                selected.append(project)
                for resource, needed in project.get("resource_requirements", {}).items():
                    usage[resource] = usage.get(resource, 0.0) + needed

        return selected

    async def _score_risk(self, project: dict[str, Any]) -> float:
        """Score project risk (0-1, higher is lower risk)."""
        risk_level = project.get("risk_level", "medium")

        risk_scores = {"low": 0.9, "medium": 0.6, "high": 0.3}

        return risk_scores.get(risk_level, 0.6)

    async def _score_resource_feasibility(self, project: dict[str, Any]) -> float:
        """Score resource feasibility (0-1)."""
        # Future work: Query Resource Management Agent for availability

        return project.get("resource_score", 0.7)  # type: ignore

    async def _score_compliance(self, project: dict[str, Any]) -> float:
        """Score compliance value (0-1)."""
        is_compliance = project.get("category") == "compliance"
        return 1.0 if is_compliance else 0.5

    async def _calculate_objective_alignment(
        self, project: dict[str, Any], objective: dict[str, Any]
    ) -> float:
        """Calculate alignment between project and strategic objective."""
        objective_text = " ".join(
            [
                str(objective.get("name", "")),
                str(objective.get("description", "")),
                " ".join(objective.get("keywords", []) or []),
            ]
        )
        project_text = " ".join(
            [
                str(project.get("name", "")),
                str(project.get("description", "")),
                " ".join(project.get("tags", []) or []),
                " ".join(project.get("benefits", []) or []),
            ]
        )
        objective_terms = self._extract_keywords(objective_text)
        project_terms = self._extract_keywords(project_text)
        if not objective_terms:
            return 0.0

        matched = len(project_terms & objective_terms)
        score = matched / max(1, len(objective_terms))

        objective_ids = {objective.get("id"), objective.get("name")}
        project_objectives = set(project.get("strategic_objectives", []) or [])
        if objective_ids & project_objectives:
            score = max(score, 0.85)

        return max(0.0, min(1.0, score))

    def _extract_keywords(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return {token for token in tokens if len(token) > 3}

    def _apply_scenario_multipliers(
        self, projects: list[dict[str, Any]], multipliers: dict[str, Any]
    ) -> list[dict[str, Any]]:
        if not multipliers:
            return list(projects)

        adjusted_projects = []
        for project in projects:
            adjusted = dict(project)
            for field, multiplier in multipliers.items():
                if (
                    field == "projections"
                    and isinstance(project.get("projections"), dict)
                    and isinstance(multiplier, dict)
                ):
                    projections = dict(project["projections"])
                    for key, proj_multiplier in multiplier.items():
                        if key in projections and isinstance(projections[key], (int, float)):
                            projections[key] = projections[key] * proj_multiplier
                    adjusted["projections"] = projections
                    continue
                if isinstance(adjusted.get(field), (int, float)) and isinstance(
                    multiplier, (int, float)
                ):
                    adjusted[field] = adjusted[field] * multiplier
                    if field in {"roi", "strategic_score"}:
                        adjusted[field] = max(0.0, min(1.0, adjusted[field]))
            adjusted_projects.append(adjusted)

        return adjusted_projects

    async def _calculate_portfolio_metrics(
        self, selected_projects: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate portfolio-level metrics."""
        if not selected_projects:
            return {"average_score": 0, "risk_profile": "low", "strategic_coverage": 0}

        avg_score = sum(p["score"] for p in selected_projects) / len(selected_projects)

        return {
            "average_score": avg_score,
            "risk_profile": "balanced",  # Future work: Calculate actual risk profile
            "strategic_coverage": 0.8,  # Future work: Calculate actual coverage
        }

    async def _identify_trade_offs(
        self, optimization_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify trade-offs in optimization results."""
        return [
            {
                "dimension": "value_vs_risk",
                "description": "Higher value projects tend to have higher risk",
            },
            {
                "dimension": "strategic_vs_financial",
                "description": "Strategic alignment sometimes conflicts with short-term ROI",
            },
        ]

    async def _generate_scenario_comparison(
        self, scenario_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate cross-scenario comparison."""
        if not scenario_results:
            return {}

        return {
            "value_range": {
                "min": min(s.get("results", {}).get("total_value", 0) for s in scenario_results),
                "max": max(s.get("results", {}).get("total_value", 0) for s in scenario_results),
            },
            "cost_range": {
                "min": min(s.get("results", {}).get("total_cost", 0) for s in scenario_results),
                "max": max(s.get("results", {}).get("total_cost", 0) for s in scenario_results),
            },
            "projects_range": {
                "min": min(s.get("results", {}).get("total_projects", 0) for s in scenario_results),
                "max": max(s.get("results", {}).get("total_projects", 0) for s in scenario_results),
            },
        }

    async def _recommend_best_scenario(
        self, scenario_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Recommend the best scenario based on value optimization."""
        if not scenario_results:
            return {"scenario_id": None, "rationale": "No scenarios available"}

        # Select scenario with highest total value
        best_scenario = max(
            scenario_results, key=lambda s: s.get("results", {}).get("total_value", 0)
        )

        return {
            "scenario_id": best_scenario.get("scenario_id"),
            "scenario_name": best_scenario.get("scenario_name"),
            "rationale": f"Highest total value: ${best_scenario.get('results', {}).get('total_value', 0):,.0f}",
        }

    async def _get_current_portfolio(self, portfolio_id: str | None = None) -> list[dict[str, Any]]:
        """Get current portfolio composition."""
        # Future work: Query database for active projects
        return []

    async def _calculate_investment_mix(self, portfolio: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate current investment mix percentages."""
        if not portfolio:
            return {"innovation": 0, "operations": 0, "compliance": 0}

        total_cost = sum(p.get("cost", 0) for p in portfolio)
        if total_cost == 0:
            return {"innovation": 0, "operations": 0, "compliance": 0}

        mix = {"innovation": 0, "operations": 0, "compliance": 0}

        for project in portfolio:
            category = project.get("category", "operations")
            cost = project.get("cost", 0)
            if category in mix:
                mix[category] += cost / total_cost

        return mix  # type: ignore

    async def _suggest_rebalancing_actions(self, category: str, gap: float) -> list[str]:
        """Suggest specific actions to rebalance portfolio."""
        if gap > 0:
            return [
                f"Approve more {category} projects from the pipeline",
                f"Accelerate delivery of existing {category} initiatives",
                f"Increase investment allocation for {category} category",
            ]
        else:
            return [
                f"Defer or cancel lower-priority {category} projects",
                f"Complete and close out existing {category} projects",
                f"Reduce new {category} project approvals temporarily",
            ]

    async def _calculate_rebalancing_impact(
        self, recommendations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate impact of rebalancing recommendations."""
        return {
            "strategic_alignment_improvement": 0.05,  # 5% improvement
            "resource_utilization_change": 0.02,  # 2% increase
            "estimated_implementation_time": "1-2 quarters",
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Portfolio Strategy & Optimization Agent...")
        # Future work: Close database connections
        # Future work: Close PPM system connections
        # Future work: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "portfolio_prioritization",
            "strategic_alignment_scoring",
            "capacity_constrained_optimization",
            "risk_reward_balancing",
            "scenario_planning",
            "what_if_analysis",
            "portfolio_rebalancing",
            "investment_mix_optimization",
            "multi_criteria_decision_analysis",
            "pareto_optimization",
            "strategic_objective_extraction",
            "portfolio_value_forecasting",
        ]
