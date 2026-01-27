"""
Agent 12: Financial Management Agent

Purpose:
Provides comprehensive financial oversight across portfolios, programs and projects.
Supports budgeting, cost tracking, forecasting, variance analysis and profitability assessment.

Specification: agents/delivery-management/agent-12-financial-management/README.md
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from approval_workflow_agent import ApprovalWorkflowAgent
from data_quality.rules import evaluate_quality_rules
from observability.tracing import get_trace_id

from agents.runtime import BaseAgent
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.state_store import TenantStateStore


class FinancialManagementAgent(BaseAgent):
    """
    Financial Management Agent - Provides financial oversight and analysis.

    Key Capabilities:
    - Budget creation and baseline management
    - Cost tracking and accruals
    - Forecasting and re-forecasting
    - Variance and trend analysis
    - Multi-currency and tax handling
    - Financial approvals integration
    - Profitability and ROI analysis
    - Financial compliance and auditability
    - Reporting and dashboards
    """

    def __init__(
        self, agent_id: str = "financial-management", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.default_currency = config.get("default_currency", "USD") if config else "USD"
        self.fiscal_year_start = config.get("fiscal_year_start", "01-01") if config else "01-01"
        self.variance_threshold_pct = config.get("variance_threshold_pct", 0.10) if config else 0.10
        self.variance_threshold_abs = (
            config.get("variance_threshold_abs", 10000) if config else 10000
        )

        # Cost categories
        self.cost_categories = (
            config.get(
                "cost_categories",
                ["labor", "overhead", "materials", "contracts", "travel", "software", "other"],
            )
            if config
            else ["labor", "overhead", "materials", "contracts", "travel", "software", "other"]
        )

        budget_store_path = (
            Path(config.get("budget_store_path", "data/financial_budgets.json"))
            if config
            else Path("data/financial_budgets.json")
        )
        actuals_store_path = (
            Path(config.get("actuals_store_path", "data/financial_actuals.json"))
            if config
            else Path("data/financial_actuals.json")
        )
        forecast_store_path = (
            Path(config.get("forecast_store_path", "data/financial_forecasts.json"))
            if config
            else Path("data/financial_forecasts.json")
        )
        self.budget_store = TenantStateStore(budget_store_path)
        self.actuals_store = TenantStateStore(actuals_store_path)
        self.forecast_store = TenantStateStore(forecast_store_path)

        # Data stores (will be replaced with database)
        self.budgets = {}  # type: ignore
        self.actuals = {}  # type: ignore
        self.forecasts = {}  # type: ignore
        self.variances = {}  # type: ignore
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config", {}) if config else {}
            self.approval_agent = ApprovalWorkflowAgent(config=approval_config)
        self.exchange_rate_provider = ExchangeRateProvider(
            fixture_path=Path(
                config.get("exchange_rate_fixture", "data/fixtures/exchange_rates.json")
                if config
                else "data/fixtures/exchange_rates.json"
            ),
            ttl_seconds=config.get("exchange_rate_ttl", 3600) if config else 3600,
            api_url=config.get("exchange_rate_api_url") if config else None,
        )

    async def initialize(self) -> None:
        """Initialize database connections, ERP integrations, and ML models."""
        await super().initialize()
        self.logger.info("Initializing Financial Management Agent...")

        # Future work: Initialize Azure SQL Database or Synapse Analytics connection
        # Future work: Set up Azure Data Factory pipelines for ERP integration
        # Future work: Connect to ERP systems (SAP, Oracle, Workday Financials, Dynamics 365)
        # Future work: Connect to timesheet systems (Planview, Jira, Azure DevOps)
        # Future work: Initialize Azure Machine Learning for forecasting models
        # Future work: Set up currency exchange rate API connections
        # Future work: Connect to tax service APIs
        # Future work: Initialize Azure Service Bus for event publishing
        # Future work: Set up Azure Key Vault for storing credentials

        self.logger.info("Financial Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "create_budget",
            "track_costs",
            "generate_forecast",
            "analyze_variance",
            "calculate_evm",
            "get_financial_summary",
            "generate_report",
            "update_budget",
            "approve_budget",
            "convert_currency",
            "calculate_profitability",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "create_budget":
            budget_data = input_data.get("budget", {})
            required_fields = ["project_id", "total_amount", "cost_breakdown"]
            for field in required_fields:
                if field not in budget_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process financial management requests.

        Args:
            input_data: {
                "action": "create_budget" | "track_costs" | "generate_forecast" |
                          "analyze_variance" | "calculate_evm" | "get_financial_summary" |
                          "generate_report" | "update_budget" | "approve_budget" |
                          "convert_currency" | "calculate_profitability",
                "budget": Budget data for creation/update,
                "costs": Cost transaction data,
                "project_id": Project identifier,
                "portfolio_id": Portfolio identifier,
                "time_period": Time period for reporting,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - create_budget: Budget ID and baseline details
            - track_costs: Cost tracking confirmation and summary
            - generate_forecast: Forecast data and projections
            - analyze_variance: Variance analysis results
            - calculate_evm: Earned value metrics (EV, PV, AC, CPI, SPI)
            - get_financial_summary: Financial summary for entity
            - generate_report: Financial report data
            - update_budget: Updated budget confirmation
            - approve_budget: Approval status
            - convert_currency: Converted amount
            - calculate_profitability: ROI, NPV, IRR metrics
        """
        action = input_data.get("action", "get_financial_summary")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "create_budget":
            return await self._create_budget(
                input_data.get("budget", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "track_costs":
            return await self._track_costs(
                input_data.get("costs", {}), tenant_id=tenant_id, actor_id=actor_id
            )

        elif action == "generate_forecast":
            return await self._generate_forecast(
                input_data.get("project_id"),  # type: ignore
                input_data.get("time_period", {}),
                tenant_id=tenant_id,
            )

        elif action == "analyze_variance":
            return await self._analyze_variance(
                input_data.get("project_id"), input_data.get("time_period", {}), tenant_id=tenant_id  # type: ignore
            )

        elif action == "calculate_evm":
            return await self._calculate_evm(input_data.get("project_id"), tenant_id=tenant_id)  # type: ignore

        elif action == "get_financial_summary":
            return await self._get_financial_summary(
                input_data.get("project_id"), input_data.get("portfolio_id"), tenant_id=tenant_id
            )

        elif action == "generate_report":
            return await self._generate_report(
                input_data.get("report_type", "summary"),
                input_data.get("filters", {}),
                tenant_id=tenant_id,
            )

        elif action == "update_budget":
            return await self._update_budget(
                input_data.get("budget_id"),  # type: ignore
                input_data.get("updates", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "approve_budget":
            return await self._approve_budget(
                input_data.get("budget_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "convert_currency":
            return await self._convert_currency(
                input_data.get("amount"),  # type: ignore
                input_data.get("from_currency"),  # type: ignore
                input_data.get("to_currency"),  # type: ignore
            )

        elif action == "calculate_profitability":
            return await self._calculate_profitability(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _create_budget(
        self,
        budget_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Create a new budget baseline.

        Returns budget ID and baseline confirmation.
        """
        self.logger.info(f"Creating budget for project: {budget_data.get('project_id')}")

        # Generate budget ID
        budget_id = await self._generate_budget_id()

        # Validate cost breakdown
        cost_breakdown = budget_data.get("cost_breakdown", {})
        total_from_breakdown = sum(cost_breakdown.values())
        total_amount = budget_data.get("total_amount", 0)

        if abs(total_from_breakdown - total_amount) > 0.01:
            self.logger.warning(
                f"Cost breakdown sum ({total_from_breakdown}) doesn't match total ({total_amount})"
            )

        # Create budget structure aligned to WBS
        budget = {
            "budget_id": budget_id,
            "project_id": budget_data.get("project_id"),
            "portfolio_id": budget_data.get("portfolio_id"),
            "total_amount": total_amount,
            "currency": budget_data.get("currency", self.default_currency),
            "fiscal_year": budget_data.get("fiscal_year", datetime.utcnow().year),
            "cost_breakdown": cost_breakdown,
            "cost_type": budget_data.get("cost_type", "mixed"),  # capex, opex, or mixed
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": budget_data.get("owner", "unknown"),
            "baseline_date": None,  # Set when approved
            "wbs_allocation": budget_data.get("wbs_allocation", {}),
        }

        validation = await self._validate_budget_record(
            budget, tenant_id=tenant_id, portfolio_id=budget_data.get("portfolio_id")
        )

        # Store budget
        self.budgets[budget_id] = budget
        self.budget_store.upsert(tenant_id, budget_id, budget)

        approval = await self._request_budget_approval(
            budget_id=budget_id,
            budget=budget,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            requester=actor_id,
        )

        self._emit_budget_audit(
            action="budget.created",
            budget=budget,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

        # Future work: Store in database
        # Future work: Validate funding availability with ERP

        return {
            "budget_id": budget_id,
            "status": "Draft",
            "total_amount": total_amount,
            "currency": budget["currency"],
            "cost_breakdown": cost_breakdown,
            "next_steps": "Submit budget for approval via Approval Workflow Agent",
            "created_at": budget["created_at"],
            "data_quality": validation,
            "approval": approval,
        }

    async def _track_costs(
        self, cost_data: dict[str, Any], *, tenant_id: str, actor_id: str
    ) -> dict[str, Any]:
        """
        Track actual costs and accruals.

        Returns cost tracking confirmation.
        """
        self.logger.info(f"Tracking costs for project: {cost_data.get('project_id')}")

        # Import cost transactions from ERP
        transactions = await self._import_cost_transactions(cost_data.get("project_id"))  # type: ignore

        # Match costs to WBS elements
        matched_costs = await self._match_costs_to_wbs(transactions)

        # Calculate accrued expenses
        accruals = await self._calculate_accruals(cost_data.get("project_id"))  # type: ignore

        # Update actuals
        project_id = cost_data.get("project_id")
        if project_id not in self.actuals:
            self.actuals[project_id] = {"transactions": [], "total_actual": 0, "by_category": {}}

        total_actual = sum(t.get("amount", 0) for t in matched_costs)
        self.actuals[project_id]["transactions"].extend(matched_costs)
        self.actuals[project_id]["total_actual"] = total_actual

        # Calculate by category
        by_category = {}
        for transaction in matched_costs:
            category = transaction.get("category", "other")
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += transaction.get("amount", 0)

        self.actuals[project_id]["by_category"] = by_category

        if project_id:
            self.actuals_store.upsert(tenant_id, project_id, self.actuals[project_id])

        self._emit_budget_audit(
            action="budget.costs.tracked",
            budget={
                "project_id": project_id,
                "amount": total_actual,
                "currency": self.default_currency,
            },
            tenant_id=tenant_id,
            correlation_id=None,
            actor_id=actor_id,
        )

        # Future work: Trigger variance alerts if thresholds exceeded

        return {
            "project_id": project_id,
            "transactions_imported": len(matched_costs),
            "total_actual": total_actual,
            "by_category": by_category,
            "accruals": accruals,
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def _generate_forecast(
        self, project_id: str, time_period: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Generate rolling forecast using AI-driven models.

        Returns forecast data and projections.
        """
        self.logger.info(f"Generating forecast for project: {project_id}")

        # Get historical spending data
        historical_data = await self._get_historical_spending(project_id)

        # Get resource allocation plans
        resource_plans = await self._get_resource_plans(project_id)

        # Get schedule progress
        schedule_progress = await self._get_schedule_progress(project_id)

        # Run forecasting model
        # Future work: Use Azure Machine Learning (Prophet, ARIMA, LSTM)
        forecast = await self._run_forecasting_model(
            historical_data, resource_plans, schedule_progress
        )

        # Calculate Estimate at Completion (EAC)
        eac = await self._calculate_eac(project_id, forecast)

        # Store forecast
        self.forecasts[project_id] = {
            "forecast_data": forecast,
            "eac": eac,
            "generated_at": datetime.utcnow().isoformat(),
            "time_period": time_period,
        }
        self.forecast_store.upsert(tenant_id, project_id, self.forecasts[project_id])

        # Future work: Store in database
        # Future work: Publish forecast.updated event

        return {
            "project_id": project_id,
            "forecast": forecast,
            "eac": eac,
            "variance_from_baseline": await self._calculate_forecast_variance(
                project_id, eac, tenant_id=tenant_id
            ),
            "confidence_interval": await self._calculate_confidence_interval(forecast),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _analyze_variance(
        self, project_id: str, time_period: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Analyze cost and schedule variances.

        Returns variance analysis with trends and alerts.
        """
        self.logger.info(f"Analyzing variance for project: {project_id}")

        # Get budget baseline
        budget = await self._get_budget_for_project(project_id, tenant_id=tenant_id)
        if not budget:
            raise ValueError(f"No budget found for project: {project_id}")

        # Get actual costs
        actuals = (
            self.actuals.get(project_id) or self.actuals_store.get(tenant_id, project_id) or {}
        )
        total_actual = actuals.get("total_actual", 0)

        # Get forecast/EAC
        forecast = (
            self.forecasts.get(project_id) or self.forecast_store.get(tenant_id, project_id) or {}
        )
        eac = forecast.get("eac", budget.get("total_amount", 0))

        # Calculate variances
        budget_variance = total_actual - budget.get("total_amount", 0)
        budget_variance_pct = budget_variance / budget.get("total_amount", 1)

        forecast_variance = eac - budget.get("total_amount", 0)
        forecast_variance_pct = forecast_variance / budget.get("total_amount", 1)

        # Analyze variance by category
        variance_by_category = await self._analyze_variance_by_category(
            project_id, budget, tenant_id=tenant_id
        )

        # Identify variance drivers
        drivers = await self._identify_variance_drivers(project_id, variance_by_category)

        # Generate alerts if thresholds exceeded
        alerts = []
        if (
            abs(budget_variance_pct) > self.variance_threshold_pct
            or abs(budget_variance) > self.variance_threshold_abs
        ):
            alerts.append(
                {
                    "severity": "high" if abs(budget_variance_pct) > 0.20 else "medium",
                    "type": "budget_variance",
                    "message": f"Budget variance of {budget_variance_pct:.1%} exceeds threshold",
                    "recommended_actions": await self._suggest_corrective_actions(
                        budget_variance_pct
                    ),
                }
            )

        # Future work: Generate contextual narrative using Azure OpenAI
        narrative = await self._generate_variance_narrative(
            budget_variance_pct, forecast_variance_pct, drivers
        )

        return {
            "project_id": project_id,
            "budget_baseline": budget.get("total_amount", 0),
            "total_actual": total_actual,
            "eac": eac,
            "budget_variance": budget_variance,
            "budget_variance_pct": budget_variance_pct,
            "forecast_variance": forecast_variance,
            "forecast_variance_pct": forecast_variance_pct,
            "variance_by_category": variance_by_category,
            "variance_drivers": drivers,
            "alerts": alerts,
            "narrative": narrative,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    async def _calculate_evm(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Calculate Earned Value Management metrics.

        Returns EV, PV, AC, CPI, SPI, and other EVM metrics.
        """
        self.logger.info(f"Calculating EVM metrics for project: {project_id}")

        # Get budget and actuals
        budget = await self._get_budget_for_project(project_id, tenant_id=tenant_id)
        actuals = (
            self.actuals.get(project_id) or self.actuals_store.get(tenant_id, project_id) or {}
        )

        # Get schedule progress from Schedule Agent
        schedule_progress = await self._get_schedule_progress(project_id)
        percent_complete = schedule_progress.get("percent_complete", 0)

        # Calculate EVM metrics
        budget_at_completion = budget.get("total_amount", 0) if budget else 0
        actual_cost = actuals.get("total_actual", 0)

        # Planned Value (PV) - should be based on schedule baseline
        planned_value = budget_at_completion * schedule_progress.get(
            "planned_percent", percent_complete
        )

        # Earned Value (EV) - based on work completed
        earned_value = budget_at_completion * percent_complete

        # Cost Performance Index (CPI)
        cpi = earned_value / actual_cost if actual_cost > 0 else 1.0

        # Schedule Performance Index (SPI)
        spi = earned_value / planned_value if planned_value > 0 else 1.0

        # Cost Variance (CV)
        cv = earned_value - actual_cost

        # Schedule Variance (SV)
        sv = earned_value - planned_value

        # Estimate at Completion (EAC)
        eac = budget_at_completion / cpi if cpi > 0 else budget_at_completion

        # Estimate to Complete (ETC)
        etc = eac - actual_cost

        # Variance at Completion (VAC)
        vac = budget_at_completion - eac

        # To Complete Performance Index (TCPI)
        tcpi = (
            (budget_at_completion - earned_value) / (budget_at_completion - actual_cost)
            if (budget_at_completion - actual_cost) > 0
            else 1.0
        )

        return {
            "project_id": project_id,
            "budget_at_completion": budget_at_completion,
            "actual_cost": actual_cost,
            "planned_value": planned_value,
            "earned_value": earned_value,
            "percent_complete": percent_complete,
            "cost_performance_index": cpi,
            "schedule_performance_index": spi,
            "cost_variance": cv,
            "schedule_variance": sv,
            "estimate_at_completion": eac,
            "estimate_to_complete": etc,
            "variance_at_completion": vac,
            "to_complete_performance_index": tcpi,
            "performance_status": await self._assess_performance_status(cpi, spi),
            "calculated_at": datetime.utcnow().isoformat(),
        }

    async def _get_financial_summary(
        self,
        project_id: str | None = None,
        portfolio_id: str | None = None,
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Get financial summary for a project or portfolio.

        Returns comprehensive financial overview.
        """
        self.logger.info(
            f"Getting financial summary for project={project_id}, portfolio={portfolio_id}"
        )

        if project_id:
            return await self._get_project_financial_summary(project_id, tenant_id=tenant_id)
        elif portfolio_id:
            return await self._get_portfolio_financial_summary(portfolio_id, tenant_id=tenant_id)
        else:
            raise ValueError("Either project_id or portfolio_id must be provided")

    async def _generate_report(
        self, report_type: str, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Generate financial reports.

        Returns report data for visualization.
        """
        self.logger.info(f"Generating {report_type} report")

        if report_type == "summary":
            return await self._generate_summary_report(filters, tenant_id=tenant_id)
        elif report_type == "variance":
            return await self._generate_variance_report(filters, tenant_id=tenant_id)
        elif report_type == "forecast":
            return await self._generate_forecast_report(filters, tenant_id=tenant_id)
        elif report_type == "cash_flow":
            return await self._generate_cash_flow_report(filters, tenant_id=tenant_id)
        elif report_type == "profitability":
            return await self._generate_profitability_report(filters, tenant_id=tenant_id)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    async def _update_budget(
        self,
        budget_id: str,
        updates: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """Update an existing budget (requires approval for baseline changes)."""
        self.logger.info(f"Updating budget: {budget_id}")

        budget = self.budgets.get(budget_id) or self.budget_store.get(tenant_id, budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")

        # Check if this is a baseline change
        is_baseline_change = "total_amount" in updates or "cost_breakdown" in updates
        approval = None
        if is_baseline_change:
            self.logger.info(f"Budget change requires approval for budget: {budget_id}")
            approval = await self._request_budget_approval(
                budget_id=budget_id,
                budget={**budget, **updates},
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=actor_id,
            )
            budget["status"] = "Pending Approval"

        # Apply updates
        for key, value in updates.items():
            if key in budget:
                budget[key] = value

        budget["last_updated"] = datetime.utcnow().isoformat()

        validation = await self._validate_budget_record(
            budget, tenant_id=tenant_id, portfolio_id=budget.get("portfolio_id")
        )

        self.budgets[budget_id] = budget
        self.budget_store.upsert(tenant_id, budget_id, budget)

        self._emit_budget_audit(
            action="budget.updated",
            budget=budget,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

        return {
            "budget_id": budget_id,
            "status": budget["status"],
            "updated_at": budget["last_updated"],
            "approval": approval,
            "data_quality": validation,
        }

    async def _approve_budget(
        self,
        budget_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """Approve a budget and lock it as baseline."""
        self.logger.info(f"Approving budget: {budget_id}")

        budget = self.budgets.get(budget_id) or self.budget_store.get(tenant_id, budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")

        budget["status"] = "Approved"
        budget["baseline_date"] = datetime.utcnow().isoformat()

        self.budgets[budget_id] = budget
        self.budget_store.upsert(tenant_id, budget_id, budget)

        self._emit_budget_audit(
            action="budget.approved",
            budget=budget,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

        return {
            "budget_id": budget_id,
            "status": "Approved",
            "baseline_date": budget["baseline_date"],
        }

    async def _convert_currency(
        self, amount: float, from_currency: str, to_currency: str
    ) -> dict[str, Any]:
        """Convert amount between currencies."""
        self.logger.info(f"Converting {amount} {from_currency} to {to_currency}")

        exchange_rates = await self.exchange_rate_provider.get_rates()

        if (
            from_currency not in exchange_rates["rates"]
            or to_currency not in exchange_rates["rates"]
        ):
            raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")

        # Convert to USD first, then to target currency
        usd_amount = amount / exchange_rates["rates"][from_currency]
        converted_amount = usd_amount * exchange_rates["rates"][to_currency]

        return {
            "original_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "converted_amount": converted_amount,
            "exchange_rate": exchange_rates["rates"][to_currency]
            / exchange_rates["rates"][from_currency],
            "conversion_date": datetime.utcnow().isoformat(),
            "rate_as_of": exchange_rates["as_of"],
        }

    async def _calculate_profitability(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Calculate profitability metrics including ROI, NPV, and IRR."""
        self.logger.info(f"Calculating profitability for project: {project_id}")

        # Get budget and actuals
        budget = await self._get_budget_for_project(project_id, tenant_id=tenant_id)
        self.actuals.get(project_id) or self.actuals_store.get(tenant_id, project_id) or {}
        forecast = (
            self.forecasts.get(project_id) or self.forecast_store.get(tenant_id, project_id) or {}
        )

        # Get benefit cash flows
        # Future work: Get from Business Case Agent
        benefits = await self._get_project_benefits(project_id)

        # Calculate metrics
        total_cost = (
            forecast.get("eac", budget.get("total_amount", 0))  # type: ignore
            if forecast
            else budget.get("total_amount", 0)  # type: ignore
        )
        total_benefits = sum(benefits.get("cash_flows", []))

        # Calculate NPV
        npv = await self._calculate_npv(total_cost, benefits.get("cash_flows", []))

        # Calculate IRR
        irr = await self._calculate_irr(total_cost, benefits.get("cash_flows", []))

        # Calculate ROI
        roi = (total_benefits - total_cost) / total_cost if total_cost > 0 else 0

        # Calculate payback period
        payback_period = await self._calculate_payback_period(
            total_cost, benefits.get("cash_flows", [])
        )

        return {
            "project_id": project_id,
            "total_cost": total_cost,
            "total_benefits": total_benefits,
            "npv": npv,
            "irr": irr,
            "roi": roi,
            "roi_percentage": roi * 100,
            "payback_period_months": payback_period,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    # Helper methods

    async def _generate_budget_id(self) -> str:
        """Generate unique budget ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"BDG-{timestamp}-{uuid.uuid4().hex[:6]}"

    async def _validate_budget_record(
        self, budget: dict[str, Any], *, tenant_id: str, portfolio_id: str | None
    ) -> dict[str, Any]:
        record = {
            "id": budget.get("budget_id"),
            "tenant_id": tenant_id,
            "portfolio_id": portfolio_id or "unknown",
            "name": budget.get("name") or f"Budget {budget.get('project_id', '')}",
            "currency": budget.get("currency", self.default_currency),
            "amount": budget.get("total_amount", 0),
            "fiscal_year": budget.get("fiscal_year", datetime.utcnow().year),
            "status": budget.get("status", "Draft").lower(),
            "owner": budget.get("created_by", "unknown"),
            "classification": budget.get("classification", "internal"),
            "created_at": budget.get("created_at"),
            "metadata": {
                "project_id": budget.get("project_id"),
                "cost_type": budget.get("cost_type"),
            },
        }
        if budget.get("last_updated"):
            record["updated_at"] = budget.get("last_updated")
        report = evaluate_quality_rules("budget", record)
        return {
            "record": record,
            "is_valid": report.is_valid,
            "issues": [issue.__dict__ for issue in report.issues],
        }

    async def _request_budget_approval(
        self,
        *,
        budget_id: str,
        budget: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
        requester: str,
    ) -> dict[str, Any]:
        if not self.approval_agent:
            return {"status": "skipped", "reason": "approval_agent_not_configured"}
        return await self.approval_agent.process(
            {
                "request_type": "budget_change",
                "request_id": budget_id,
                "requester": requester,
                "details": {
                    "amount": budget.get("total_amount", 0),
                    "description": "Budget approval request",
                    "project_id": budget.get("project_id"),
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )

    def _emit_budget_audit(
        self,
        *,
        action: str,
        budget: dict[str, Any],
        tenant_id: str,
        correlation_id: str | None,
        actor_id: str,
    ) -> None:
        event = build_audit_event(
            tenant_id=tenant_id,
            action=action,
            outcome="success",
            actor_id=actor_id,
            actor_type="user" if actor_id != "system" else "service",
            actor_roles=[],
            resource_id=budget.get("budget_id") or budget.get("project_id", "unknown"),
            resource_type="budget",
            metadata={"amount": budget.get("total_amount") or budget.get("amount")},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    async def _import_cost_transactions(self, project_id: str) -> list[dict[str, Any]]:
        """Import cost transactions from ERP."""
        # Future work: Query ERP system for transactions
        return []

    async def _match_costs_to_wbs(self, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Match cost transactions to WBS elements."""
        # Future work: Use AI classification when codes are missing
        return transactions

    async def _calculate_accruals(self, project_id: str) -> dict[str, Any]:
        """Calculate accrued expenses based on percent complete."""
        # Future work: Calculate accruals
        return {"total_accruals": 0}

    async def _get_historical_spending(self, project_id: str) -> list[dict[str, Any]]:
        """Get historical spending data."""
        # Future work: Query database
        return []

    async def _get_resource_plans(self, project_id: str) -> dict[str, Any]:
        """Get resource allocation plans from Resource Agent."""
        # Future work: Call Resource Management Agent
        return {}

    async def _get_schedule_progress(self, project_id: str) -> dict[str, Any]:
        """Get schedule progress from Schedule Agent."""
        # Future work: Call Schedule & Planning Agent
        return {"percent_complete": 0.5, "planned_percent": 0.5}

    async def _run_forecasting_model(
        self,
        historical_data: list[dict[str, Any]],
        resource_plans: dict[str, Any],
        schedule_progress: dict[str, Any],
    ) -> dict[str, Any]:
        """Run AI forecasting model."""
        exchange_rates = await self.exchange_rate_provider.get_rates()

        normalized_costs = []
        for entry in historical_data:
            amount = float(entry.get("amount", 0))
            currency = entry.get("currency", self.default_currency)
            if currency != self.default_currency:
                amount = amount / exchange_rates["rates"][currency]
            normalized_costs.append(amount)

        if not normalized_costs:
            normalized_costs = [0.0]

        rolling_avg = sum(normalized_costs[-3:]) / min(len(normalized_costs), 3)
        progress = schedule_progress.get("percent_complete", 0.0)
        remaining_factor = max(0.0, 1.0 - progress)
        monthly_forecast = [rolling_avg * remaining_factor for _ in range(3)]
        total_forecast = sum(normalized_costs) + sum(monthly_forecast)

        return {
            "monthly_forecast": monthly_forecast,
            "total_forecast": total_forecast,
            "currency": self.default_currency,
            "rate_as_of": exchange_rates["as_of"],
        }

    async def _calculate_eac(self, project_id: str, forecast: dict[str, Any]) -> float:
        """Calculate Estimate at Completion."""
        # Future work: More sophisticated EAC calculation
        return forecast.get("total_forecast", 0)  # type: ignore

    async def _calculate_forecast_variance(
        self, project_id: str, eac: float, *, tenant_id: str
    ) -> dict[str, Any]:
        """Calculate variance between forecast and baseline."""
        budget = await self._get_budget_for_project(project_id, tenant_id=tenant_id)
        baseline = budget.get("total_amount", 0) if budget else 0

        variance = eac - baseline
        variance_pct = variance / baseline if baseline > 0 else 0

        return {"variance": variance, "variance_pct": variance_pct}

    async def _calculate_confidence_interval(self, forecast: dict[str, Any]) -> dict[str, Any]:
        """Calculate forecast confidence interval."""
        monthly = forecast.get("monthly_forecast", [])
        if not monthly:
            return {"lower_bound": 0, "upper_bound": 0, "confidence_level": 0.95}
        mean = sum(monthly) / len(monthly)
        variance = sum((x - mean) ** 2 for x in monthly) / len(monthly)
        std_dev = variance**0.5
        return {
            "lower_bound": max(0.0, mean - 1.28 * std_dev),
            "upper_bound": mean + 1.28 * std_dev,
            "confidence_level": 0.8,
        }

    async def _get_budget_for_project(
        self, project_id: str, *, tenant_id: str
    ) -> dict[str, Any] | None:
        """Get budget for a specific project."""
        for budget in self.budgets.values():
            if budget.get("project_id") == project_id:
                return budget  # type: ignore
        for budget in self.budget_store.list(tenant_id):
            if budget.get("project_id") == project_id:
                return budget
        return None

    async def _analyze_variance_by_category(
        self, project_id: str, budget: dict[str, Any], *, tenant_id: str
    ) -> dict[str, dict[str, Any]]:
        """Analyze variance broken down by cost category."""
        actuals = (
            self.actuals.get(project_id) or self.actuals_store.get(tenant_id, project_id) or {}
        )
        budget_breakdown = budget.get("cost_breakdown", {})
        actual_breakdown = actuals.get("by_category", {})

        variance_by_category = {}

        for category in self.cost_categories:
            budget_amount = budget_breakdown.get(category, 0)
            actual_amount = actual_breakdown.get(category, 0)
            variance = actual_amount - budget_amount
            variance_pct = variance / budget_amount if budget_amount > 0 else 0

            variance_by_category[category] = {
                "budget": budget_amount,
                "actual": actual_amount,
                "variance": variance,
                "variance_pct": variance_pct,
            }

        return variance_by_category

    async def _identify_variance_drivers(
        self, project_id: str, variance_by_category: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify key drivers of cost variance."""
        # Future work: Use regression and clustering to determine drivers

        drivers = []
        for category, data in variance_by_category.items():
            if abs(data["variance_pct"]) > 0.15:  # More than 15% variance
                drivers.append(
                    {
                        "category": category,
                        "impact": data["variance"],
                        "variance_pct": data["variance_pct"],
                        "explanation": f"{category.title()} costs are {data['variance_pct']:.1%} over budget",
                    }
                )

        return drivers

    async def _suggest_corrective_actions(self, variance_pct: float) -> list[str]:
        """Suggest corrective actions based on variance."""
        if variance_pct > 0.10:  # Over budget
            return [
                "Review and reduce discretionary spending",
                "Defer non-critical activities",
                "Request budget increase through change control",
                "Optimize resource allocation",
            ]
        elif variance_pct < -0.10:  # Under budget
            return [
                "Verify all costs are being captured",
                "Check for delayed invoices or accruals",
                "Review project schedule for delays",
            ]
        else:
            return ["Continue monitoring"]

    async def _generate_variance_narrative(
        self,
        budget_variance_pct: float,
        forecast_variance_pct: float,
        drivers: list[dict[str, Any]],
    ) -> str:
        """Generate narrative explanation of variance."""
        # Future work: Use Azure OpenAI for NLG

        if abs(budget_variance_pct) < 0.05:
            return "Project is tracking within budget with minimal variance."

        direction = "over" if budget_variance_pct > 0 else "under"
        severity = "significantly" if abs(budget_variance_pct) > 0.15 else "moderately"

        narrative = f"Project is {severity} {direction} budget by {abs(budget_variance_pct):.1%}. "

        if drivers:
            top_driver = drivers[0]
            narrative += f"Primary driver is {top_driver['category']} variance of {top_driver['variance_pct']:.1%}."

        return narrative

    async def _assess_performance_status(self, cpi: float, spi: float) -> str:
        """Assess overall project performance status."""
        if cpi >= 0.95 and spi >= 0.95:
            return "On Track"
        elif cpi >= 0.85 and spi >= 0.85:
            return "At Risk"
        else:
            return "Off Track"

    async def _get_project_financial_summary(
        self, project_id: str, *, tenant_id: str
    ) -> dict[str, Any]:
        """Get financial summary for a project."""
        budget = await self._get_budget_for_project(project_id, tenant_id=tenant_id)
        actuals = (
            self.actuals.get(project_id) or self.actuals_store.get(tenant_id, project_id) or {}
        )
        forecast = (
            self.forecasts.get(project_id) or self.forecast_store.get(tenant_id, project_id) or {}
        )

        evm = await self._calculate_evm(project_id, tenant_id=tenant_id)

        return {
            "project_id": project_id,
            "budget_baseline": budget.get("total_amount", 0) if budget else 0,
            "actual_cost": actuals.get("total_actual", 0),
            "forecast_eac": forecast.get("eac", 0),
            "cost_performance_index": evm.get("cost_performance_index", 1.0),
            "schedule_performance_index": evm.get("schedule_performance_index", 1.0),
            "variance_at_completion": evm.get("variance_at_completion", 0),
            "performance_status": evm.get("performance_status", "Unknown"),
        }

    async def _get_portfolio_financial_summary(
        self, portfolio_id: str, *, tenant_id: str
    ) -> dict[str, Any]:
        """Get financial summary for a portfolio."""
        budgets = list(self.budgets.values())
        if not budgets:
            budgets = self.budget_store.list(tenant_id)
        total_budget = sum(
            budget.get("total_amount", 0)
            for budget in budgets
            if budget.get("portfolio_id") == portfolio_id
        )
        total_actual = sum(
            actuals.get("total_actual", 0)
            for actuals in (
                self.actuals.values() if self.actuals else self.actuals_store.list(tenant_id)
            )
        )
        total_forecast = sum(
            forecast.get("eac", 0)
            for forecast in (
                self.forecasts.values() if self.forecasts else self.forecast_store.list(tenant_id)
            )
        )

        return {
            "portfolio_id": portfolio_id,
            "total_budget": total_budget,
            "total_actual": total_actual,
            "total_forecast": total_forecast,
            "average_cpi": 1.0,
            "project_count": len(budgets),
        }

    async def _generate_summary_report(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Generate summary financial report."""
        return {
            "report_type": "summary",
            "data": {
                "budget_count": len(self.budgets) or len(self.budget_store.list(tenant_id)),
                "forecast_count": len(self.forecasts) or len(self.forecast_store.list(tenant_id)),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_variance_report(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Generate variance analysis report."""
        return {
            "report_type": "variance",
            "data": {"portfolio_id": filters.get("portfolio_id")},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_forecast_report(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Generate forecast report."""
        return {
            "report_type": "forecast",
            "data": {
                "forecast_count": len(self.forecasts) or len(self.forecast_store.list(tenant_id))
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_cash_flow_report(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Generate cash flow report."""
        return {
            "report_type": "cash_flow",
            "data": {"currency": self.default_currency},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_profitability_report(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Generate profitability analysis report."""
        return {
            "report_type": "profitability",
            "data": {"currency": self.default_currency},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _get_project_benefits(self, project_id: str) -> dict[str, Any]:
        """Get project benefits and cash flows."""
        # Future work: Query Business Case Agent
        return {"cash_flows": [], "total_benefits": 0}

    async def _calculate_npv(self, total_cost: float, cash_flows: list[float]) -> float:
        """Calculate Net Present Value."""
        discount_rate = self.config.get("discount_rate", 0.10)
        npv = -total_cost
        for i, cash_flow in enumerate(cash_flows, start=1):
            npv += cash_flow / ((1 + discount_rate) ** i)
        return npv

    async def _calculate_irr(self, total_cost: float, cash_flows: list[float]) -> float:
        """Calculate Internal Rate of Return."""
        cash_series = [-total_cost] + cash_flows

        def npv_for_rate(rate: float) -> float:
            return sum(value / ((1 + rate) ** idx) for idx, value in enumerate(cash_series))

        lower, upper = -0.9, 1.5
        for _ in range(50):
            mid = (lower + upper) / 2
            value = npv_for_rate(mid)
            if abs(value) < 1e-6:
                return mid
            if value > 0:
                lower = mid
            else:
                upper = mid
        return (lower + upper) / 2

    async def _calculate_payback_period(self, total_cost: float, cash_flows: list[float]) -> int:
        """Calculate payback period in months."""
        # Future work: Implement proper payback period calculation
        if not cash_flows or sum(cash_flows) == 0:
            return 999

        annual_cash_flow = sum(cash_flows) / len(cash_flows)
        if annual_cash_flow == 0:
            return 999

        payback_years = total_cost / annual_cash_flow
        return int(payback_years * 12)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Financial Management Agent...")
        # Future work: Close database connections
        # Future work: Close ERP connections
        # Future work: Flush any pending events
        # Future work: Save any unsaved data

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "budget_creation",
            "budget_baseline_management",
            "cost_tracking",
            "cost_accruals",
            "financial_forecasting",
            "variance_analysis",
            "earned_value_management",
            "multi_currency_support",
            "tax_handling",
            "financial_approvals",
            "profitability_analysis",
            "roi_calculation",
            "npv_calculation",
            "irr_calculation",
            "financial_reporting",
            "cash_flow_analysis",
            "budget_variance_alerts",
            "cost_driver_analysis",
            "financial_compliance",
            "audit_trail_management",
        ]


class ExchangeRateProvider:
    """Exchange rate provider with caching and optional API fetch."""

    def __init__(self, fixture_path: Path, ttl_seconds: int, api_url: str | None = None):
        self.fixture_path = fixture_path
        self.ttl_seconds = ttl_seconds
        self.api_url = api_url
        self._cache: dict[str, Any] | None = None
        self._last_loaded: datetime | None = None

    async def get_rates(self) -> dict[str, Any]:
        if self._cache and self._last_loaded:
            age = (datetime.utcnow() - self._last_loaded).total_seconds()
            if age < self.ttl_seconds:
                return self._cache

        if self.api_url:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                data = response.json()
        else:
            data = json.loads(self.fixture_path.read_text())

        self._cache = {
            "base": data.get("base", "USD"),
            "rates": data.get("rates", {}),
            "as_of": data.get("as_of", datetime.utcnow().isoformat()),
        }
        self._last_loaded = datetime.utcnow()
        return self._cache
