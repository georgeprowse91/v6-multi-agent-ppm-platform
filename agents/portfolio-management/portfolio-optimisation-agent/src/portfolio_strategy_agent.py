"""
Portfolio Strategy & Optimization Agent

Purpose:
Manages the composition and allocation of the project and program portfolio.
Maximizes strategic value and business outcomes while respecting resource and budget constraints.

Specification: agents/portfolio-management/portfolio-optimisation-agent/README.md
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from events import PortfolioPrioritizedEvent
from observability.tracing import get_trace_id
from portfolio_actions import (
    calculate_alignment_score,
    compare_scenarios,
    get_portfolio_status,
    get_scenario,
    list_scenarios,
    optimize_portfolio,
    prioritize_portfolio,
    rebalance_portfolio,
    record_portfolio_decision,
    run_scenario_analysis,
    submit_portfolio_for_approval,
    upsert_scenario,
)
from portfolio_utils import (
    apply_resource_capacity,
    apply_scenario_multipliers,
    calculate_project_value,
    extract_keywords,
    knapsack_select,
    select_ahp,
    select_mean_variance,
    select_multi_objective,
)

from agents.common.connector_integration import DatabaseStorageService
from agents.common.integration_services import LocalEmbeddingService, VectorSearchIndex
from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
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
        agent_id: str = "portfolio-optimisation-agent",
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
        self.scenario_definitions = {}  # type: ignore
        self.db_service: DatabaseStorageService | None = None
        self.embedding_service = LocalEmbeddingService(
            config.get("embedding_dimensions", 128) if config else 128
        )
        self.vector_index = VectorSearchIndex(self.embedding_service)
        self.integration_clients = config.get("integration_clients", {}) if config else {}
        self.integration_status: dict[str, bool] = {}
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.financial_agent = config.get("financial_agent") if config else None
        self.approval_agent = config.get("approval_agent") if config else None
        self.approval_agent_config = config.get("approval_agent_config", {}) if config else {}
        self.approval_agent_enabled = config.get("approval_agent_enabled", True) if config else True

    async def initialize(self) -> None:
        """Initialize optimization models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Portfolio Strategy & Optimization Agent...")

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")
        self._register_integrations()
        await self._load_strategic_objectives()

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
            "upsert_scenario",
            "get_scenario",
            "list_scenarios",
            "submit_portfolio_for_approval",
            "record_portfolio_decision",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "optimize_portfolio":
            constraints = input_data.get("constraints", {})
            if "budget_ceiling" not in constraints and "resource_capacity" not in constraints:
                self.logger.warning("Missing constraints for optimization")
                return False
        if action in {"get_scenario"} and "scenario_id" not in input_data:
            self.logger.warning("Missing scenario_id")
            return False
        if action in {"submit_portfolio_for_approval", "record_portfolio_decision"}:
            if "portfolio_id" not in input_data:
                self.logger.warning("Missing portfolio_id")
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
            return await prioritize_portfolio(
                self,
                input_data.get("projects", []),
                input_data.get("criteria_weights", self.default_weights),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                portfolio_id=input_data.get("portfolio_id"),
                cycle=input_data.get("cycle", "ad-hoc"),
            )

        elif action == "calculate_alignment_score":
            return await calculate_alignment_score(
                self,
                input_data.get("project", {}),
                input_data.get("objectives", []),
            )

        elif action == "optimize_portfolio":
            return await optimize_portfolio(
                self,
                input_data.get("projects", []),
                input_data.get("constraints", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "run_scenario_analysis":
            scenarios = input_data.get("scenarios", [])
            scenario_ids = input_data.get("scenario_ids", [])
            if not scenarios and scenario_ids:
                scenarios = await self._load_scenarios_by_id(scenario_ids)
            return await run_scenario_analysis(
                self,
                scenarios,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "rebalance_portfolio":
            return await rebalance_portfolio(self, input_data.get("portfolio_id"))

        elif action == "get_portfolio_status":
            return await get_portfolio_status(
                self,
                input_data.get("portfolio_id"),
                tenant_id=tenant_id,
            )

        elif action == "compare_scenarios":
            return await compare_scenarios(self, input_data.get("scenario_ids", []))
        elif action == "upsert_scenario":
            return await upsert_scenario(
                self,
                input_data.get("scenario", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "get_scenario":
            return await get_scenario(self, input_data.get("scenario_id"))
        elif action == "list_scenarios":
            return await list_scenarios(self)
        elif action == "submit_portfolio_for_approval":
            return await submit_portfolio_for_approval(
                self,
                input_data.get("portfolio_id"),
                decision_payload=input_data.get("decision_payload", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "record_portfolio_decision":
            return await record_portfolio_decision(
                self,
                input_data.get("portfolio_id"),
                decision=input_data.get("decision", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

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
        """Delegate to the prioritization action handler."""
        return await prioritize_portfolio(
            self,
            projects,
            criteria_weights,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            portfolio_id=portfolio_id,
            cycle=cycle,
        )

    async def _calculate_alignment_score(
        self, project: dict[str, Any], objectives: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Delegate to the prioritization action handler."""
        return await calculate_alignment_score(self, project, objectives)

    async def _optimize_portfolio(
        self,
        projects: list[dict[str, Any]],
        constraints: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Delegate to the optimization action handler."""
        return await optimize_portfolio(
            self, projects, constraints, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _run_scenario_analysis(
        self, scenarios: list[dict[str, Any]], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Delegate to the scenario action handler."""
        return await run_scenario_analysis(
            self, scenarios, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _rebalance_portfolio(
        self, portfolio_id: str | None = None, tenant_id: str = "", correlation_id: str = ""
    ) -> dict[str, Any]:
        """Delegate to the optimization action handler."""
        return await rebalance_portfolio(
            self, portfolio_id, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _get_portfolio_status(
        self, portfolio_id: str | None = None, *, tenant_id: str
    ) -> dict[str, Any]:
        """Delegate to the status action handler."""
        return await get_portfolio_status(self, portfolio_id, tenant_id=tenant_id)

    async def _upsert_scenario(
        self, scenario: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Delegate to the scenario action handler."""
        return await upsert_scenario(
            self, scenario, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _get_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Delegate to the scenario action handler."""
        return await get_scenario(self, scenario_id)

    async def _list_scenarios(self) -> dict[str, Any]:
        """Delegate to the scenario action handler."""
        return await list_scenarios(self)

    async def _load_scenarios_by_id(self, scenario_ids: list[str]) -> list[dict[str, Any]]:
        scenarios = []
        for scenario_id in scenario_ids:
            scenario = self.scenario_definitions.get(scenario_id)
            if scenario and scenario.get("scenario"):
                scenarios.append(scenario["scenario"])
        return scenarios

    async def _compare_scenarios(self, scenario_ids: list[str]) -> dict[str, Any]:
        """Delegate to the scenario action handler."""
        return await compare_scenarios(self, scenario_ids)

    # Helper methods

    async def _enrich_projects_with_financials(
        self, projects: list[dict[str, Any]], *, tenant_id: str, correlation_id: str
    ) -> list[dict[str, Any]]:
        if not self.financial_agent:
            return projects
        enriched: list[dict[str, Any]] = []
        for project in projects:
            project_id = project.get("project_id")
            if not project_id:
                enriched.append(project)
                continue
            financials = await self.financial_agent.process(
                {
                    "action": "get_financial_summary",
                    "project_id": project_id,
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
                }
            )
            enriched_project = project.copy()
            enriched_project.setdefault(
                "estimated_cost",
                financials.get("total_cost")
                or financials.get("total_costs")
                or financials.get("budget_total"),
            )
            enriched_project.setdefault(
                "expected_value",
                financials.get("expected_value")
                or financials.get("roi_value")
                or financials.get("forecast_value"),
            )
            enriched_project.setdefault("roi", financials.get("roi"))
            if "cash_flows" not in enriched_project:
                enriched_project["cash_flows"] = (
                    financials.get("cash_flows")
                    or financials.get("cashflow")
                    or financials.get("cash_flow_forecast")
                    or []
                )
            enriched_project.setdefault("npv", financials.get("net_present_value"))
            enriched_project.setdefault("irr", financials.get("irr"))
            enriched.append(enriched_project)
        return enriched

    def _calculate_project_value(self, project: dict[str, Any], *, discount_rate: float) -> float:
        return calculate_project_value(project, discount_rate=discount_rate)

    async def _select_optimized_projects(
        self,
        scored_projects: list[dict[str, Any]],
        *,
        budget_ceiling: float,
        min_compliance_spend: float,
        resource_capacity: dict[str, float],
        method: str,
        risk_aversion: float,
        objective_weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        method = method.lower()
        if method == "mean_variance":
            return select_mean_variance(
                scored_projects, budget_ceiling, resource_capacity, risk_aversion
            )
        if method == "ahp":
            return select_ahp(scored_projects, budget_ceiling, resource_capacity)
        if method in {"multi_objective", "weighted_sum"}:
            return select_multi_objective(
                scored_projects, budget_ceiling, resource_capacity, objective_weights
            )
        return await self._optimize_knapsack(
            scored_projects, budget_ceiling, min_compliance_spend, resource_capacity
        )

    async def _submit_portfolio_for_approval(
        self,
        portfolio_id: str,
        *,
        decision_payload: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Delegate to the status action handler."""
        return await submit_portfolio_for_approval(
            self,
            portfolio_id,
            decision_payload=decision_payload,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    async def _record_portfolio_decision(
        self,
        portfolio_id: str,
        *,
        decision: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Delegate to the status action handler."""
        return await record_portfolio_decision(
            self,
            portfolio_id,
            decision=decision,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    async def _generate_portfolio_id(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
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
            timestamp=datetime.now(timezone.utc),
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

        compliance_projects = [p for p in projects if p.get("category") == "compliance"]
        other_projects = [p for p in projects if p.get("category") != "compliance"]

        compliance_selected = knapsack_select(compliance_projects, max_budget, scale)
        compliance_spend = sum(p["cost"] for p in compliance_selected)

        remaining_budget = budget_ceiling - compliance_spend
        if compliance_spend < min_compliance_spend:
            return compliance_selected

        remaining_selected = knapsack_select(
            other_projects, int(remaining_budget // scale), scale
        )

        selected = compliance_selected + remaining_selected
        return apply_resource_capacity(selected, resource_capacity)

    async def _score_risk(self, project: dict[str, Any]) -> float:
        """Score project risk (0-1, higher is lower risk)."""
        risk_level = project.get("risk_level", "medium")

        risk_scores = {"low": 0.9, "medium": 0.6, "high": 0.3}

        return risk_scores.get(risk_level, 0.6)

    async def _score_resource_feasibility(self, project: dict[str, Any]) -> float:
        """Score resource feasibility (0-1)."""
        resource_agent = self.integration_clients.get("resource_agent")
        if resource_agent:
            response = await resource_agent.process(
                {
                    "action": "get_capacity",
                    "resource_requirements": project.get("resource_requirements", {}),
                }
            )
            return float(response.get("feasibility_score", project.get("resource_score", 0.7)))
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
        keyword_score = matched / max(1, len(objective_terms))
        embedding_score = self._embedding_similarity(objective_text, project_text)
        score = max(keyword_score, embedding_score)

        objective_ids = {objective.get("id"), objective.get("name")}
        project_objectives = set(project.get("strategic_objectives", []) or [])
        if objective_ids & project_objectives:
            score = max(score, 0.85)

        return max(0.0, min(1.0, score))

    def _embedding_similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        vectors = self.embedding_service.embed([left, right])
        a, b = vectors[0], vectors[1]
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def _register_integrations(self) -> None:
        self.integration_status = {
            "ml_optimizer": bool(self.integration_clients.get("ml_optimizer")),
            "ppm_connector": bool(self.integration_clients.get("ppm_connector")),
            "planning_tools": bool(self.integration_clients.get("planning_tools")),
            "cognitive_nlp": bool(self.integration_clients.get("cognitive_nlp")),
            "cognitive_search": bool(self.integration_clients.get("cognitive_search")),
            "event_bus": self.event_bus is not None,
        }

    async def _load_strategic_objectives(self) -> None:
        objectives = self.config.get("strategic_objectives") if self.config else None
        if isinstance(objectives, list):
            self.strategic_objectives = objectives
            for objective in objectives:
                if isinstance(objective, dict):
                    objective_text = (
                        f"{objective.get('name', '')} {objective.get('description', '')}"
                    )
                    self.vector_index.add(
                        str(objective.get("id", objective.get("name", uuid.uuid4().hex))),
                        objective_text,
                        objective,
                    )

    async def _publish_event(
        self, topic: str, payload: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        if not self.event_bus:
            return
        enriched = {
            **payload,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.event_bus.publish(topic, enriched)

    def _extract_keywords(self, text: str) -> set[str]:
        return extract_keywords(text)

    def _apply_scenario_multipliers(
        self, projects: list[dict[str, Any]], multipliers: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return apply_scenario_multipliers(projects, multipliers)

    async def _get_current_portfolio(self, portfolio_id: str | None = None) -> list[dict[str, Any]]:
        """Get current portfolio composition."""
        if self.db_service and portfolio_id:
            record = await self.db_service.get("portfolio_strategy", portfolio_id)
            if record:
                return record.get("ranked_projects", [])
        return []

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Portfolio Strategy & Optimization Agent...")
        if self.db_service and hasattr(self.db_service, "close"):
            await self.db_service.close()
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()

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
