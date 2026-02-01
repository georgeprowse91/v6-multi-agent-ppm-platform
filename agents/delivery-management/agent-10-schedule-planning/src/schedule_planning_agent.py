"""
Agent 10: Schedule & Planning Agent

Purpose:
Constructs and manages project timelines, transforms WBS into schedules, maps task dependencies
and performs critical path analysis. Supports both predictive and adaptive planning.

Specification: agents/delivery-management/agent-10-schedule-planning/README.md
"""

import math
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from change_configuration_agent import ChangeConfigurationAgent
from events import ScheduleBaselineLockedEvent, ScheduleDelayEvent
from observability.tracing import get_trace_id
from sqlalchemy.orm import Session

from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from services.integration import (
    AnalyticsClient,
    CacheClient,
    CacheSettings,
    DatabricksMonteCarloClient,
    EventBusClient,
    EventEnvelope,
    ExternalSyncClient,
    ExternalSyncSettings,
    PersistenceSettings,
    SqlRepository,
    create_sql_engine,
    Base,
)
from services.integration.ml import AzureMLClient


class SchedulePlanningAgent(BaseAgent):
    """
    Schedule & Planning Agent - Creates and manages project schedules and timelines.

    Key Capabilities:
    - WBS to schedule conversion
    - Task duration estimation using AI and historical data
    - Dependency mapping (FS, SS, FF, SF)
    - Critical path method (CPM) analysis
    - Resource-constrained scheduling
    - Schedule risk analysis and Monte Carlo simulation
    - Milestone tracking and deadline management
    - Schedule optimization and what-if scenarios
    - Baseline management and variance tracking
    """

    def __init__(self, agent_id: str = "schedule-planning", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.default_working_hours = config.get("default_working_hours", 8) if config else 8
        self.default_working_days = config.get("default_working_days", 5) if config else 5
        self.max_resource_allocation = config.get("max_resource_allocation", 1.0) if config else 1.0
        self.risk_threshold = config.get("risk_threshold", 0.70) if config else 0.70
        self.baseline_approval_threshold = (
            config.get("baseline_approval_threshold", 0.10) if config else 0.10
        )
        self.simulation_seed = config.get("simulation_seed", 42) if config else 42
        self.scenario_engine = ScenarioEngine()
        self.enable_persistence = config.get("enable_persistence", True) if config else True
        self.enable_event_publishing = (
            config.get("enable_event_publishing", True) if config else True
        )
        self.enable_analytics = config.get("enable_analytics", True) if config else True
        self.enable_azure_ml = config.get("enable_azure_ml", False) if config else False
        self.enable_databricks = config.get("enable_databricks", False) if config else False
        self.enable_dependency_ai = config.get("enable_dependency_ai", True) if config else True
        self.enable_external_sync = config.get("enable_external_sync", False) if config else False
        self.enable_calendar_sync = config.get("enable_calendar_sync", False) if config else False
        self.enable_cache = config.get("enable_cache", True) if config else True
        self.cache_ttl_seconds = config.get("cache_ttl_seconds", 600) if config else 600

        schedule_store_path = (
            Path(config.get("schedule_store_path", "data/project_schedules.json"))
            if config
            else Path("data/project_schedules.json")
        )
        baseline_store_path = (
            Path(config.get("schedule_baseline_store_path", "data/schedule_baselines.json"))
            if config
            else Path("data/schedule_baselines.json")
        )
        self.schedule_store = TenantStateStore(schedule_store_path)
        self.baseline_store = TenantStateStore(baseline_store_path)

        # Data stores (will be replaced with database connections)
        self.schedules = {}  # type: ignore
        self.baselines = {}  # type: ignore
        self.dependencies = {}  # type: ignore
        self.milestones = {}  # type: ignore
        self.task_actuals = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.integration_event_bus = EventBusClient() if self.enable_event_publishing else None
        self.analytics_client = AnalyticsClient() if self.enable_analytics else None
        self.cache_client = (
            CacheClient(
                CacheSettings(
                    provider=config.get("cache_provider", "in_memory") if config else "in_memory",
                    redis_url=config.get("redis_url") if config else None,
                    default_ttl_seconds=self.cache_ttl_seconds,
                )
            )
            if self.enable_cache
            else None
        )
        self.azure_ml_client = AzureMLClient() if self.enable_azure_ml else None
        self.databricks_client = (
            DatabricksMonteCarloClient(seed=self.simulation_seed)
            if self.enable_databricks
            else None
        )
        self.external_sync_client = (
            ExternalSyncClient(
                ExternalSyncSettings(
                    enable_ms_project=config.get("enable_ms_project", False) if config else False,
                    enable_jira=config.get("enable_jira", False) if config else False,
                    enable_azure_devops=config.get("enable_azure_devops", False)
                    if config
                    else False,
                    enable_smartsheet=config.get("enable_smartsheet", False) if config else False,
                    enable_outlook=config.get("enable_outlook", False) if config else False,
                    enable_google_calendar=config.get("enable_google_calendar", False)
                    if config
                    else False,
                )
            )
            if self.enable_external_sync or self.enable_calendar_sync
            else None
        )
        self.duration_model_id: str | None = None
        self._sql_engine = None
        if self.enable_persistence:
            persistence_settings = PersistenceSettings()
            connection_string = (
                config.get("sql_connection_string") if config else None
            ) or persistence_settings.sql_connection_string
            self._sql_engine = create_sql_engine(connection_string)
            Base.metadata.create_all(self._sql_engine)
        self.change_agent = config.get("change_agent") if config else None
        if self.change_agent is None:
            change_config = config.get("change_agent_config", {}) if config else {}
            self.change_agent = ChangeConfigurationAgent(config=change_config)

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Schedule & Planning Agent...")

        # Future work: Initialize Azure Machine Learning for duration estimation models
        # Future work: Initialize Azure Databricks for Monte Carlo simulation
        # Future work: Connect to Azure SQL Database for schedule data storage
        # Future work: Initialize Azure Cache for Redis for frequently accessed schedules
        # Future work: Connect to Microsoft Project via Logic Apps for Gantt chart sync
        # Future work: Initialize Jira/Azure DevOps integration for sprint planning
        # Future work: Connect to Smartsheet API for timeline sync
        # Future work: Initialize Outlook/Google Calendar integration for milestone sync
        # Future work: Set up Azure Service Bus/Event Grid for schedule event publishing
        # Future work: Initialize Azure Synapse Analytics for historical performance analysis

        self.logger.info("Schedule & Planning Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "create_schedule",
            "estimate_duration",
            "map_dependencies",
            "calculate_critical_path",
            "resource_constrained_schedule",
            "run_monte_carlo",
            "track_milestones",
            "optimize_schedule",
            "what_if_analysis",
            "manage_baseline",
            "track_variance",
            "sprint_planning",
            "get_schedule",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "create_schedule":
            if "project_id" not in input_data or "wbs" not in input_data:
                self.logger.warning("Missing project_id or wbs")
                return False

        elif action in ["what_if_analysis", "optimize_schedule"]:
            if "schedule_id" not in input_data:
                self.logger.warning("Missing schedule_id")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process schedule and planning requests.

        Args:
            input_data: {
                "action": "create_schedule" | "estimate_duration" | "map_dependencies" |
                          "calculate_critical_path" | "resource_constrained_schedule" |
                          "run_monte_carlo" | "track_milestones" | "optimize_schedule" |
                          "what_if_analysis" | "manage_baseline" | "track_variance" |
                          "sprint_planning" | "get_schedule",
                "project_id": Project ID,
                "schedule_id": Schedule ID,
                "wbs": Work breakdown structure,
                "dependencies": Dependency definitions,
                "resources": Resource assignments,
                "what_if_params": Parameters for what-if analysis,
                "sprint_data": Sprint planning data,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - create_schedule: Schedule ID, Gantt chart data, critical path
            - estimate_duration: Task durations with confidence intervals
            - map_dependencies: Dependency network diagram
            - calculate_critical_path: Critical path tasks and total duration
            - resource_constrained_schedule: Optimized schedule respecting resources
            - run_monte_carlo: Probabilistic completion dates and risk analysis
            - track_milestones: Milestone status and upcoming deadlines
            - optimize_schedule: Optimized schedule with improvements
            - what_if_analysis: Scenario comparison results
            - manage_baseline: Baseline ID and locked schedule
            - track_variance: Schedule variance analysis
            - sprint_planning: Sprint backlog and capacity planning
            - get_schedule: Complete schedule details
        """
        action = input_data.get("action", "create_schedule")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "create_schedule":
            return await self._create_schedule(
                input_data.get("project_id"),  # type: ignore
                input_data.get("wbs", {}),
                input_data.get("methodology", "waterfall"),
                tenant_id=tenant_id,
            )

        elif action == "estimate_duration":
            return await self._estimate_duration(
                input_data.get("tasks", []), input_data.get("project_context", {})
            )

        elif action == "map_dependencies":
            return await self._map_dependencies(
                input_data.get("schedule_id"), input_data.get("dependencies", [])  # type: ignore
            )

        elif action == "calculate_critical_path":
            return await self._calculate_critical_path(input_data.get("schedule_id"))  # type: ignore

        elif action == "resource_constrained_schedule":
            return await self._resource_constrained_schedule(
                input_data.get("schedule_id"), input_data.get("resources", {})  # type: ignore
            )

        elif action == "run_monte_carlo":
            return await self._run_monte_carlo(
                input_data.get("schedule_id"), input_data.get("iterations", 1000)  # type: ignore
            )

        elif action == "track_milestones":
            return await self._track_milestones(input_data.get("schedule_id"))  # type: ignore

        elif action == "optimize_schedule":
            return await self._optimize_schedule(input_data.get("schedule_id"))  # type: ignore

        elif action == "what_if_analysis":
            return await self._what_if_analysis(
                input_data.get("schedule_id"), input_data.get("what_if_params", {})  # type: ignore
            )

        elif action == "manage_baseline":
            return await self._manage_baseline(
                input_data.get("schedule_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "track_variance":
            return await self._track_variance(
                input_data.get("schedule_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "sprint_planning":
            return await self._sprint_planning(
                input_data.get("project_id"), input_data.get("sprint_data", {})  # type: ignore
            )

        elif action == "get_schedule":
            return await self._get_schedule(input_data.get("schedule_id"), tenant_id=tenant_id)  # type: ignore

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _create_schedule(
        self,
        project_id: str,
        wbs: dict[str, Any],
        methodology: str = "waterfall",
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Create project schedule from WBS.

        Returns schedule ID and Gantt chart data.
        """
        self.logger.info(f"Creating schedule for project: {project_id}")

        # Generate unique schedule ID
        schedule_id = await self._generate_schedule_id(project_id)

        # Convert WBS to task list
        tasks = await self._wbs_to_tasks(wbs)

        # Estimate durations for all tasks
        duration_estimates = await self._estimate_duration(tasks, {"project_id": project_id})

        # Apply duration estimates to tasks
        tasks_with_durations = await self._apply_duration_estimates(tasks, duration_estimates)

        # Define dependencies
        # Future work: Use AI to suggest dependencies based on task relationships
        dependencies = await self._suggest_dependencies(tasks_with_durations)

        # Calculate early/late start/finish dates using CPM
        scheduled_tasks = await self._calculate_cpm_dates(tasks_with_durations, dependencies)

        # Identify critical path
        critical_path = await self._identify_critical_path(scheduled_tasks, dependencies)

        # Calculate project duration
        project_duration = await self._calculate_project_duration(scheduled_tasks)

        # Generate Gantt chart data
        gantt_data = await self._generate_gantt_data(scheduled_tasks, dependencies)

        # Identify milestones
        milestones = await self._identify_milestones(scheduled_tasks)

        # Create schedule record
        schedule = {
            "schedule_id": schedule_id,
            "project_id": project_id,
            "methodology": methodology,
            "tasks": scheduled_tasks,
            "dependencies": dependencies,
            "critical_path": critical_path,
            "project_duration_days": project_duration,
            "start_date": await self._calculate_schedule_start(scheduled_tasks),
            "end_date": await self._calculate_schedule_end(scheduled_tasks),
            "milestones": milestones,
            "gantt_data": gantt_data,
            "created_at": datetime.utcnow().isoformat(),
            "status": "Draft",
        }

        # Store schedule
        self.schedules[schedule_id] = schedule
        self.milestones[schedule_id] = milestones
        self.schedule_store.upsert(tenant_id, schedule_id, schedule)

        if self.enable_persistence and self._sql_engine:
            await self._persist_schedule(schedule)

        if self.integration_event_bus:
            await self._publish_schedule_created(schedule)

        if self.analytics_client:
            self.analytics_client.record_metric(
                "schedule.duration_days",
                float(project_duration),
                {"schedule_id": schedule_id, "project_id": project_id},
            )
            self.analytics_client.record_metric(
                "schedule.critical_path_length",
                float(len(critical_path)),
                {"schedule_id": schedule_id, "project_id": project_id},
            )

        if self.cache_client:
            cache_key = self._schedule_cache_key(tenant_id, schedule_id)
            self.cache_client.set(cache_key, schedule, ttl_seconds=self.cache_ttl_seconds)

        await self._sync_external_tools(schedule)

        self.logger.info(f"Created schedule: {schedule_id}")

        return {
            "schedule_id": schedule_id,
            "project_duration_days": project_duration,
            "task_count": len(scheduled_tasks),
            "critical_path_tasks": len(critical_path),
            "milestones": milestones,
            "gantt_data": gantt_data,
            "next_steps": "Review schedule, then lock as baseline",
        }

    async def _estimate_duration(
        self, tasks: list[dict[str, Any]], project_context: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """
        Estimate task durations using AI and historical data.

        Returns duration estimates with confidence intervals.
        """
        self.logger.info("Estimating task durations")

        team_performance = float(project_context.get("team_performance", 1.0))
        if self.azure_ml_client and not self.duration_model_id:
            historical = await self._get_historical_durations("project", "medium")
            artifact = self.azure_ml_client.train_duration_model(
                historical,
                team_performance,
                {"project_id": project_context.get("project_id")},
            )
            self.duration_model_id = artifact.model_id

        duration_estimates = {}

        for task in tasks:
            task_id = task.get("task_id")
            task_name = task.get("name", "")
            complexity = task.get("complexity", "medium")

            # Query historical data for similar tasks
            # Future work: Integrate with Azure Synapse Analytics
            historical_data = await self._get_historical_durations(task_name, complexity)

            if self.azure_ml_client and self.duration_model_id:
                most_likely = self.azure_ml_client.predict_duration(self.duration_model_id, complexity)
                historical_data = historical_data or [most_likely]

            optimistic, most_likely, pessimistic = await self._calculate_pert_estimate(
                task, historical_data
            )

            # Calculate expected duration using PERT formula
            expected_duration = (optimistic + 4 * most_likely + pessimistic) / 6

            duration_estimates[task_id] = {
                "optimistic": optimistic,
                "most_likely": most_likely,
                "pessimistic": pessimistic,
                "expected": expected_duration,
                "confidence": 0.80,  # Future work: Calculate actual confidence
                "unit": "days",
            }

        return duration_estimates  # type: ignore

    async def _map_dependencies(
        self, schedule_id: str, dependencies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Map task dependencies.

        Returns dependency network diagram.
        """
        self.logger.info(f"Mapping dependencies for schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        # Validate dependencies
        validated_dependencies = await self._validate_dependencies(
            dependencies, schedule.get("tasks", [])
        )

        # Detect circular dependencies
        circular_deps = await self._detect_circular_dependencies(validated_dependencies)

        if circular_deps:
            raise ValueError(f"Circular dependencies detected: {circular_deps}")

        # Update schedule with dependencies
        schedule["dependencies"] = validated_dependencies
        self.dependencies[schedule_id] = validated_dependencies

        # Generate network diagram data
        network_diagram = await self._generate_network_diagram(
            schedule.get("tasks", []), validated_dependencies
        )

        # Future work: Store in database
        # Future work: Publish dependencies.mapped event

        return {
            "schedule_id": schedule_id,
            "dependencies": validated_dependencies,
            "dependency_count": len(validated_dependencies),
            "network_diagram": network_diagram,
            "circular_dependencies": circular_deps,
        }

    async def _calculate_critical_path(self, schedule_id: str) -> dict[str, Any]:
        """
        Calculate critical path using CPM.

        Returns critical path and total project duration.
        """
        self.logger.info(f"Calculating critical path for schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        tasks = schedule.get("tasks", [])
        dependencies = schedule.get("dependencies", [])

        # Perform forward pass (calculate early start/finish)
        tasks_with_early = await self._forward_pass(tasks, dependencies)

        # Perform backward pass (calculate late start/finish)
        tasks_with_late = await self._backward_pass(tasks_with_early, dependencies)

        # Calculate slack/float for each task
        tasks_with_slack = await self._calculate_slack(tasks_with_late)

        # Identify critical path (tasks with zero slack)
        critical_path_tasks = [task for task in tasks_with_slack if task.get("slack", 0) == 0]

        # Calculate total project duration
        project_duration = (
            max(task.get("late_finish", 0) for task in tasks_with_slack) if tasks_with_slack else 0
        )

        # Update schedule
        schedule["tasks"] = tasks_with_slack
        schedule["critical_path"] = [t["task_id"] for t in critical_path_tasks]
        schedule["project_duration_days"] = project_duration

        return {
            "schedule_id": schedule_id,
            "critical_path": critical_path_tasks,
            "project_duration_days": project_duration,
            "critical_path_task_count": len(critical_path_tasks),
            "total_slack_days": sum(t.get("slack", 0) for t in tasks_with_slack),
        }

    async def _resource_constrained_schedule(
        self, schedule_id: str, resources: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create resource-constrained schedule.

        Returns optimized schedule respecting resource availability.
        """
        self.logger.info(f"Creating resource-constrained schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        tasks = schedule.get("tasks", [])
        dependencies = schedule.get("dependencies", [])

        # Get resource availability from Resource Management Agent
        # Future work: Integrate with Agent 11
        resource_availability = await self._get_resource_availability(resources)

        # Apply resource leveling
        # Future work: Use optimization algorithm (RCPSP solver)
        leveled_schedule = await self._resource_leveling(tasks, dependencies, resource_availability)

        # Recalculate critical path with resource constraints
        resource_critical_path = await self._calculate_critical_path(schedule_id)

        # Calculate resource utilization
        utilization = await self._calculate_resource_utilization(
            leveled_schedule, resource_availability
        )

        return {
            "schedule_id": schedule_id,
            "leveled_schedule": leveled_schedule,
            "resource_critical_path": resource_critical_path,
            "resource_utilization": utilization,
            "schedule_extension_days": await self._calculate_schedule_extension(
                schedule.get("project_duration_days", 0), leveled_schedule
            ),
        }

    async def _run_monte_carlo(self, schedule_id: str, iterations: int = 1000) -> dict[str, Any]:
        """
        Run Monte Carlo simulation for schedule risk analysis.

        Returns probabilistic completion dates.
        """
        self.logger.info(f"Running Monte Carlo simulation for schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        tasks = schedule.get("tasks", [])
        dependencies = schedule.get("dependencies", [])

        task_samples: dict[str, list[float]] = {task["task_id"]: [] for task in tasks}
        rng = random.Random(self.simulation_seed)

        async def _sample_duration(_: int) -> float:
            sampled_tasks = await self._sample_task_durations(tasks, rng=rng)
            duration = await self._calculate_simulated_duration(sampled_tasks, dependencies)
            for task in sampled_tasks:
                task_samples[task["task_id"]].append(float(task.get("duration", 0)))
            return duration

        if self.databricks_client:
            def _databricks_sampler(index: int, rng_local: random.Random) -> float:
                sampled_tasks = [
                    dict(
                        task,
                        duration=rng_local.triangular(
                            float(task.get("optimistic_duration", task.get("duration", 0))),
                            float(task.get("pessimistic_duration", task.get("duration", 0))),
                            float(task.get("most_likely_duration", task.get("duration", 0))),
                        ),
                    )
                    for task in tasks
                ]
                forward = self._forward_pass_sync(sampled_tasks, dependencies)
                duration = max((task.get("early_finish", 0) for task in forward), default=0)
                for task in sampled_tasks:
                    task_samples[task["task_id"]].append(float(task.get("duration", 0)))
                return float(duration)

            monte_carlo = self.databricks_client.simulate(
                iterations=iterations,
                sampler=_databricks_sampler,
                percentiles=(50, 80, 90, 95),
                rng=rng,
            )
            simulation_results = monte_carlo.results
            p50 = monte_carlo.percentiles.get(50, 0)
            p80 = monte_carlo.percentiles.get(80, 0)
            p90 = monte_carlo.percentiles.get(90, 0)
            p95 = monte_carlo.percentiles.get(95, 0)
            distribution_stats = monte_carlo.statistics
        else:
            monte_carlo = await self.scenario_engine.run_monte_carlo(
                iterations=iterations,
                sampler=_sample_duration,
                percentiles=(50, 80, 90, 95),
            )
            simulation_results = monte_carlo.results
            p50 = monte_carlo.percentiles.get(50, 0)
            p80 = monte_carlo.percentiles.get(80, 0)
            p90 = monte_carlo.percentiles.get(90, 0)
            p95 = monte_carlo.percentiles.get(95, 0)
            distribution_stats = monte_carlo.statistics

        # Calculate risk metrics
        risk_score = await self._calculate_schedule_risk(
            simulation_results, schedule.get("project_duration_days", 0)
        )

        risk_drivers = await self._extract_risk_drivers(task_samples, simulation_results)

        if self.analytics_client:
            self.analytics_client.record_metric(
                "schedule.monte_carlo_p80",
                float(p80),
                {"schedule_id": schedule_id},
            )
            self.analytics_client.record_metric(
                "schedule.risk_score",
                float(risk_score),
                {"schedule_id": schedule_id},
            )

        return {
            "schedule_id": schedule_id,
            "iterations": iterations,
            "baseline_duration": schedule.get("project_duration_days", 0),
            "p50_duration": p50,
            "p80_duration": p80,
            "p90_duration": p90,
            "p95_duration": p95,
            "risk_score": risk_score,
            "risk_drivers": risk_drivers,
            "distribution": distribution_stats,
        }

    async def _track_milestones(self, schedule_id: str) -> dict[str, Any]:
        """
        Track milestones and upcoming deadlines.

        Returns milestone status and alerts.
        """
        self.logger.info(f"Tracking milestones for schedule: {schedule_id}")

        milestones = self.milestones.get(schedule_id, [])

        # Get current date
        current_date = datetime.utcnow()

        # Categorize milestones
        upcoming_milestones = []
        past_due_milestones = []
        completed_milestones = []

        for milestone in milestones:
            milestone_date = datetime.fromisoformat(milestone.get("date"))
            status = milestone.get("status", "pending")

            if status == "completed":
                completed_milestones.append(milestone)
            elif milestone_date < current_date:
                past_due_milestones.append(milestone)
            else:
                days_until = (milestone_date - current_date).days
                if days_until <= 30:  # Upcoming within 30 days
                    milestone["days_until"] = days_until
                    upcoming_milestones.append(milestone)

        return {
            "schedule_id": schedule_id,
            "total_milestones": len(milestones),
            "upcoming_milestones": upcoming_milestones,
            "past_due_milestones": past_due_milestones,
            "completed_milestones": completed_milestones,
            "completion_rate": len(completed_milestones) / len(milestones) if milestones else 0,
        }

    async def _optimize_schedule(self, schedule_id: str) -> dict[str, Any]:
        """
        Optimize schedule to minimize duration.

        Returns optimized schedule with recommendations.
        """
        self.logger.info(f"Optimizing schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        # Identify optimization opportunities
        opportunities = await self._identify_optimization_opportunities(schedule)

        # Apply optimizations
        optimized_schedule = await self._apply_optimizations(schedule, opportunities)

        # Calculate improvements
        improvements = await self._calculate_improvements(schedule, optimized_schedule)

        return {
            "schedule_id": schedule_id,
            "original_duration": schedule.get("project_duration_days", 0),
            "optimized_duration": optimized_schedule.get("project_duration_days", 0),
            "duration_reduction": improvements.get("duration_reduction", 0),
            "optimizations_applied": opportunities,
            "recommendations": await self._generate_optimization_recommendations(opportunities),
        }

    async def _what_if_analysis(
        self, schedule_id: str, what_if_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform what-if scenario analysis.

        Returns scenario comparison results.
        """
        self.logger.info(f"Running what-if analysis for schedule: {schedule_id}")

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        scenario_output = await self.scenario_engine.run_scenario(
            baseline=schedule,
            scenario_params=what_if_params,
            scenario_builder=self._create_scenario,
            metrics_builder=self._recalculate_schedule,
            comparison_builder=self._compare_schedules,
            recommendation_builder=self._generate_scenario_recommendation,
        )
        recalculated = scenario_output["scenario_metrics"]
        comparison = scenario_output["comparison"]

        return {
            "schedule_id": schedule_id,
            "scenario_params": what_if_params,
            "baseline_duration": schedule.get("project_duration_days", 0),
            "scenario_duration": recalculated.get("project_duration_days", 0),
            "duration_difference": comparison.get("duration_difference", 0),
            "cost_impact": comparison.get("cost_impact", 0),
            "resource_impact": comparison.get("resource_impact", {}),
            "recommendation": scenario_output.get("recommendation"),
        }

    async def _manage_baseline(
        self, schedule_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Lock schedule as baseline.

        Returns baseline ID and locked schedule.
        """
        self.logger.info(f"Creating baseline for schedule: {schedule_id}")

        schedule = await self._get_schedule_state(tenant_id, schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        # Generate baseline ID
        baseline_id = await self._generate_baseline_id(schedule_id)

        # Create baseline snapshot
        baseline = {
            "baseline_id": baseline_id,
            "schedule_id": schedule_id,
            "tasks": schedule.get("tasks", []),
            "dependencies": schedule.get("dependencies", []),
            "milestones": schedule.get("milestones", []),
            "project_duration_days": schedule.get("project_duration_days", 0),
            "start_date": schedule.get("start_date"),
            "end_date": schedule.get("end_date"),
            "locked_at": datetime.utcnow().isoformat(),
            "locked_by": "system",  # Future work: Get from user context
            "status": "Locked",
        }

        # Store baseline
        self.baselines[baseline_id] = baseline
        self.baseline_store.upsert(tenant_id, baseline_id, baseline)

        # Update schedule status
        schedule["status"] = "Baselined"
        schedule["baseline_id"] = baseline_id
        self.schedule_store.upsert(tenant_id, schedule_id, schedule)

        await self._publish_baseline_locked(
            schedule,
            baseline,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return {
            "baseline_id": baseline_id,
            "schedule_id": schedule_id,
            "locked_at": baseline["locked_at"],
            "task_count": len(baseline["tasks"]),
            "milestone_count": len(baseline["milestones"]),
        }

    async def _track_variance(
        self, schedule_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Track schedule variance against baseline.

        Returns variance analysis.
        """
        self.logger.info(f"Tracking variance for schedule: {schedule_id}")

        schedule = await self._get_schedule_state(tenant_id, schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        baseline_id = schedule.get("baseline_id")
        if not baseline_id:
            return {
                "error": "No baseline exists for this schedule",
                "recommendation": "Create a baseline first",
            }

        baseline = self.baselines.get(baseline_id) or self.baseline_store.get(
            tenant_id, baseline_id
        )
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")

        # Calculate schedule variance (SV)
        sv = await self._calculate_schedule_variance(schedule, baseline)
        baseline_duration = max(baseline.get("project_duration_days", 0), 1)
        schedule_variance_pct = sv / baseline_duration if baseline_duration else 0

        # Calculate schedule performance index (SPI)
        spi = await self._calculate_spi(schedule, baseline)

        # Identify delayed tasks
        delayed_tasks = await self._identify_delayed_tasks(schedule, baseline)

        # Identify critical path changes
        critical_path_changes = await self._identify_critical_path_changes(schedule, baseline)

        change_request = None
        delay_event = None
        external_updates = []
        if sv < 0:
            delay_event = await self._publish_schedule_delay(
                schedule,
                delay_days=abs(int(sv)),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        if abs(sv) >= self.baseline_approval_threshold * max(
            baseline.get("project_duration_days", 1), 1
        ):
            change_request = await self._submit_change_request(
                schedule,
                baseline,
                variance_days=sv,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        if self.external_sync_client and self.enable_external_sync:
            external_updates = [
                update.payload for update in self.external_sync_client.pull_updates(schedule_id)
            ]

        if self.analytics_client:
            self.analytics_client.record_metric(
                "schedule.baseline_duration_days",
                float(baseline.get("project_duration_days", 0) or 0),
                {"schedule_id": schedule_id},
            )
            self.analytics_client.record_metric(
                "schedule.actual_duration_days",
                float(schedule.get("project_duration_days", 0) or 0),
                {"schedule_id": schedule_id},
            )
            self.analytics_client.record_metric(
                "schedule.variance_days",
                float(sv),
                {"schedule_id": schedule_id},
            )

        return {
            "schedule_id": schedule_id,
            "baseline_id": baseline_id,
            "schedule_variance_days": sv,
            "schedule_variance_pct": schedule_variance_pct,
            "schedule_performance_index": spi,
            "variance_status": "Ahead" if sv > 0 else "Behind" if sv < 0 else "On Track",
            "delayed_tasks": delayed_tasks,
            "critical_path_changes": critical_path_changes,
            "forecast_completion": await self._forecast_completion_date(schedule, spi),
            "change_request": change_request,
            "delay_event": delay_event,
            "external_updates": external_updates,
        }

    async def _sprint_planning(
        self, project_id: str, sprint_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform sprint planning for Agile projects.

        Returns sprint backlog and capacity planning.
        """
        self.logger.info(f"Sprint planning for project: {project_id}")

        # Get team velocity and capacity
        team_velocity = sprint_data.get("team_velocity", 0)
        team_capacity = sprint_data.get("team_capacity", 0)
        backlog_items = sprint_data.get("backlog_items", [])

        # Recommend sprint backlog based on capacity
        recommended_items = await self._recommend_sprint_backlog(
            backlog_items, team_velocity, team_capacity
        )

        # Calculate story points for sprint
        total_story_points = sum(item.get("story_points", 0) for item in recommended_items)

        # Generate burndown forecast
        burndown_forecast = await self._generate_burndown_forecast(
            total_story_points, sprint_data.get("sprint_duration_days", 10)
        )

        return {
            "project_id": project_id,
            "sprint_backlog": recommended_items,
            "total_story_points": total_story_points,
            "team_velocity": team_velocity,
            "team_capacity": team_capacity,
            "capacity_utilization": total_story_points / team_capacity if team_capacity > 0 else 0,
            "burndown_forecast": burndown_forecast,
        }

    async def _get_schedule(self, schedule_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve schedule by ID."""
        schedule = await self._get_schedule_state(tenant_id, schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        return schedule  # type: ignore

    async def _get_schedule_state(self, tenant_id: str, schedule_id: str) -> dict[str, Any] | None:
        schedule = None
        if self.cache_client:
            cached = self.cache_client.get(self._schedule_cache_key(tenant_id, schedule_id))
            if cached:
                self.schedules[schedule_id] = cached
                return cached

        schedule = self.schedules.get(schedule_id)
        if not schedule:
            schedule = self.schedule_store.get(tenant_id, schedule_id)
            if schedule:
                self.schedules[schedule_id] = schedule
                if self.cache_client:
                    self.cache_client.set(
                        self._schedule_cache_key(tenant_id, schedule_id),
                        schedule,
                        ttl_seconds=self.cache_ttl_seconds,
                    )
        return schedule

    # Helper methods

    async def _generate_schedule_id(self, project_id: str) -> str:
        """Generate unique schedule ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{project_id}-SCH-{timestamp}"

    def _schedule_cache_key(self, tenant_id: str, schedule_id: str) -> str:
        return f"schedule:{tenant_id}:{schedule_id}"

    async def _generate_baseline_id(self, schedule_id: str) -> str:
        """Generate unique baseline ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{schedule_id}-BASELINE-{timestamp}"

    async def _publish_baseline_locked(
        self,
        schedule: dict[str, Any],
        baseline: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> None:
        event = ScheduleBaselineLockedEvent(
            event_name="schedule.baseline.locked",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "project_id": schedule.get("project_id", ""),
                "schedule_id": schedule.get("schedule_id", ""),
                "locked_at": datetime.fromisoformat(baseline.get("locked_at")),
                "baseline_version": baseline.get("baseline_id", ""),
            },
        )
        await self.event_bus.publish("schedule.baseline.locked", event.model_dump())

    async def _publish_schedule_delay(
        self,
        schedule: dict[str, Any],
        *,
        delay_days: int,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        event = ScheduleDelayEvent(
            event_name="schedule.delay",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "project_id": schedule.get("project_id", ""),
                "schedule_id": schedule.get("schedule_id", ""),
                "delay_days": delay_days,
                "reason": "Baseline variance detected",
                "detected_at": datetime.utcnow(),
            },
        )
        payload = event.model_dump()
        await self.event_bus.publish("schedule.delay", payload)
        return payload

    async def _publish_schedule_created(self, schedule: dict[str, Any]) -> None:
        if not self.integration_event_bus:
            return
        envelope = EventEnvelope(
            event_type="schedule.created",
            subject=f"schedule/{schedule.get('schedule_id')}",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "project_id": schedule.get("project_id"),
                "task_count": len(schedule.get("tasks", [])),
                "status": schedule.get("status"),
            },
        )
        self.integration_event_bus.publish_event(envelope)

    async def _publish_task_updated(
        self, schedule: dict[str, Any], task: dict[str, Any], event_type: str = "task.updated"
    ) -> None:
        if not self.integration_event_bus:
            return
        envelope = EventEnvelope(
            event_type=event_type,
            subject=f"schedule/{schedule.get('schedule_id')}/task/{task.get('task_id')}",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "task_id": task.get("task_id"),
                "duration": task.get("duration"),
                "status": task.get("status", "planned"),
            },
        )
        self.integration_event_bus.publish_event(envelope)

    async def _submit_change_request(
        self,
        schedule: dict[str, Any],
        baseline: dict[str, Any],
        *,
        variance_days: float,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not self.change_agent:
            return {"status": "skipped", "reason": "change_agent_not_configured"}
        return await self.change_agent.process(
            {
                "action": "submit_change_request",
                "change": {
                    "title": "Schedule variance exceeds threshold",
                    "description": "Baseline variance exceeded threshold; review schedule baseline.",
                    "requester": "schedule-planning-agent",
                    "project_id": schedule.get("project_id"),
                    "priority": "medium",
                    "impact_summary": {
                        "variance_days": variance_days,
                        "baseline_id": baseline.get("baseline_id"),
                    },
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )

    async def _persist_schedule(self, schedule: dict[str, Any]) -> None:
        if not self._sql_engine:
            return
        with Session(self._sql_engine) as session:
            repo = SqlRepository(session)
            schedule_row = repo.add_schedule(schedule.get("schedule_id", "schedule"), schedule.get("status", "draft"))
            for task in schedule.get("tasks", []):
                repo.add_task(
                    schedule_id=schedule_row.id,
                    task_key=task.get("task_id", ""),
                    name=task.get("name", ""),
                    duration_days=float(task.get("duration", 0) or 0),
                    status=task.get("status", "planned"),
                )
                await self._publish_task_updated(schedule, task)

            for dependency in schedule.get("dependencies", []):
                repo.add_dependency(
                    schedule_id=schedule_row.id,
                    predecessor_task_key=dependency.get("predecessor", ""),
                    successor_task_key=dependency.get("successor", ""),
                    dependency_type=dependency.get("type", "FS"),
                    lag_days=float(dependency.get("lag", 0) or 0),
                )

    async def _sync_external_tools(self, schedule: dict[str, Any]) -> None:
        if not self.external_sync_client:
            return
        if self.enable_external_sync:
            self.external_sync_client.push_schedule(
                schedule.get("schedule_id", ""),
                {
                    "tasks": schedule.get("tasks", []),
                    "dependencies": schedule.get("dependencies", []),
                    "milestones": schedule.get("milestones", []),
                },
            )
        if self.enable_calendar_sync:
            self.external_sync_client.sync_calendar(
                schedule.get("schedule_id", ""),
                schedule.get("milestones", []),
            )

    async def _wbs_to_tasks(self, wbs: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert WBS to flat task list."""
        tasks = []
        # Future work: Implement recursive WBS traversal
        # Baseline
        task_id = 1
        for key, value in wbs.items():
            tasks.append(
                {
                    "task_id": f"T{task_id:03d}",
                    "wbs_id": key,
                    "name": value.get("name", f"Task {task_id}"),
                    "complexity": "medium",
                }
            )
            task_id += 1
        return tasks

    async def _get_historical_durations(self, task_name: str, complexity: str) -> list[float]:
        """Query historical task durations."""
        # Future work: Query Azure Synapse Analytics
        return [5.0, 7.0, 6.0]  # Baseline

    async def _calculate_pert_estimate(
        self, task: dict[str, Any], historical_data: list[float]
    ) -> tuple[float, float, float]:
        """Calculate PERT estimates (optimistic, most likely, pessimistic)."""
        # Future work: Use ML model for better estimates
        if historical_data:
            avg = sum(historical_data) / len(historical_data)
            optimistic = avg * 0.8
            most_likely = avg
            pessimistic = avg * 1.3
        else:
            optimistic = 3.0
            most_likely = 5.0
            pessimistic = 8.0

        return optimistic, most_likely, pessimistic

    async def _apply_duration_estimates(
        self, tasks: list[dict[str, Any]], estimates: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply duration estimates to tasks."""
        for task in tasks:
            task_id = task.get("task_id")
            if task_id in estimates:
                task["duration"] = estimates[task_id]["expected"]
                task["duration_estimate"] = estimates[task_id]
                task["optimistic_duration"] = estimates[task_id]["optimistic"]
                task["most_likely_duration"] = estimates[task_id]["most_likely"]
                task["pessimistic_duration"] = estimates[task_id]["pessimistic"]
        return tasks

    async def _suggest_dependencies(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suggest dependencies between tasks."""
        if not tasks:
            return []

        def _priority(task: dict[str, Any]) -> int:
            name = (task.get("name") or "").lower()
            keywords = [
                ("init", 1),
                ("plan", 2),
                ("design", 3),
                ("build", 4),
                ("implement", 4),
                ("test", 5),
                ("deploy", 6),
                ("close", 7),
            ]
            for key, score in keywords:
                if key in name:
                    return score
            return 3

        ordered = sorted(tasks, key=_priority) if self.enable_dependency_ai else tasks
        dependencies: list[dict[str, Any]] = []
        for i in range(len(ordered) - 1):
            dependencies.append(
                {
                    "predecessor": ordered[i]["task_id"],
                    "successor": ordered[i + 1]["task_id"],
                    "type": "FS",
                    "lag": 0,
                }
            )
        return dependencies

    async def _calculate_cpm_dates(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Calculate CPM dates for tasks."""
        tasks_with_early = await self._forward_pass(tasks, dependencies)
        tasks_with_late = await self._backward_pass(tasks_with_early, dependencies)
        return await self._calculate_slack(tasks_with_late)

    async def _identify_critical_path(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> list[str]:
        """Identify critical path task IDs."""
        critical_tasks = [task for task in tasks if float(task.get("slack", 0)) == 0]
        return [task["task_id"] for task in critical_tasks]

    async def _calculate_project_duration(self, tasks: list[dict[str, Any]]) -> float:
        """Calculate total project duration."""
        if not tasks:
            return 0
        return max(
            float(task.get("resource_finish", task.get("late_finish", task.get("early_finish", 0))))
            for task in tasks
        )

    async def _generate_gantt_data(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate Gantt chart visualization data."""
        return {
            "tasks": tasks,
            "dependencies": dependencies,
            "timeline": {
                "start": await self._calculate_schedule_start(tasks),
                "end": await self._calculate_schedule_end(tasks),
            },
        }

    async def _identify_milestones(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify project milestones."""
        milestones = []
        for task in tasks:
            if task.get("is_milestone") or task.get("duration", 0) == 0:
                milestones.append(
                    {
                        "name": task.get("name"),
                        "date": task.get("early_finish"),
                        "status": "pending",
                    }
                )
        return milestones

    async def _calculate_schedule_start(self, tasks: list[dict[str, Any]]) -> str:
        """Calculate schedule start date."""
        return datetime.utcnow().isoformat()

    async def _calculate_schedule_end(self, tasks: list[dict[str, Any]]) -> str:
        """Calculate schedule end date."""
        duration = await self._calculate_project_duration(tasks)
        end_date = datetime.utcnow() + timedelta(days=duration)
        return end_date.isoformat()

    async def _validate_dependencies(
        self, dependencies: list[dict[str, Any]], tasks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate dependency definitions."""
        task_ids = {task["task_id"] for task in tasks}
        valid_dependencies = []

        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if pred in task_ids and succ in task_ids:
                valid_dependencies.append(dep)

        return valid_dependencies

    async def _detect_circular_dependencies(self, dependencies: list[dict[str, Any]]) -> list[str]:
        """Detect circular dependencies."""
        graph: dict[str, list[str]] = {}
        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if not pred or not succ:
                continue
            graph.setdefault(pred, []).append(succ)

        visiting: set[str] = set()
        visited: set[str] = set()
        cycles = []

        def visit(node: str, path: list[str]) -> None:
            if node in visiting:
                cycles.append(" -> ".join(path + [node]))
                return
            if node in visited:
                return
            visiting.add(node)
            for neighbor in graph.get(node, []):
                visit(neighbor, path + [node])
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node, [])

        return cycles

    async def _generate_network_diagram(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate network diagram data."""
        return {"nodes": tasks, "edges": dependencies}

    def _forward_pass_sync(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        task_map = {task["task_id"]: dict(task) for task in tasks}
        predecessors: dict[str, list[str]] = {task_id: [] for task_id in task_map}
        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if (
                isinstance(pred, str)
                and isinstance(succ, str)
                and pred in task_map
                and succ in task_map
            ):
                predecessors[succ].append(pred)

        in_degree = {task_id: len(preds) for task_id, preds in predecessors.items()}
        queue = [task_id for task_id, count in in_degree.items() if count == 0]
        ordered: list[str] = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for dep in dependencies:
                if dep.get("predecessor") == current:
                    succ = dep.get("successor")
                    if succ in in_degree:
                        in_degree[succ] -= 1
                        if in_degree[succ] == 0:
                            queue.append(succ)

        if len(ordered) != len(task_map):
            ordered = list(task_map.keys())

        for task_id in ordered:
            task = task_map[task_id]
            duration = float(task.get("duration", 0))
            if predecessors[task_id]:
                task["early_start"] = max(
                    task_map[pred].get("early_finish", 0) for pred in predecessors[task_id]
                )
            else:
                task["early_start"] = 0
            task["early_finish"] = task["early_start"] + duration

        return list(task_map.values())

    async def _forward_pass(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Perform CPM forward pass."""
        task_map = {task["task_id"]: task for task in tasks}
        predecessors: dict[str, list[str]] = {task["task_id"]: [] for task in tasks}
        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if (
                isinstance(pred, str)
                and isinstance(succ, str)
                and pred in task_map
                and succ in task_map
            ):
                predecessors[succ].append(pred)

        in_degree = {task_id: len(preds) for task_id, preds in predecessors.items()}
        queue = [task_id for task_id, count in in_degree.items() if count == 0]

        ordered = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for dep in dependencies:
                if dep.get("predecessor") == current:
                    succ = dep.get("successor")
                    if succ in in_degree:
                        in_degree[succ] -= 1
                        if in_degree[succ] == 0:
                            queue.append(succ)

        if len(ordered) != len(task_map):
            ordered = list(task_map.keys())

        for task_id in ordered:
            task = task_map[task_id]
            duration = float(task.get("duration", 0))
            if predecessors[task_id]:
                task["early_start"] = max(
                    task_map[pred].get("early_finish", 0) for pred in predecessors[task_id]
                )
            else:
                task["early_start"] = 0
            task["early_finish"] = task["early_start"] + duration

        return list(task_map.values())

    async def _backward_pass(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Perform CPM backward pass."""
        task_map = {task["task_id"]: task for task in tasks}
        successors: dict[str, list[str]] = {task["task_id"]: [] for task in tasks}
        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if (
                isinstance(pred, str)
                and isinstance(succ, str)
                and pred in task_map
                and succ in task_map
            ):
                successors[pred].append(succ)

        project_duration = max((t.get("early_finish", 0) for t in tasks), default=0)
        out_degree = {task_id: len(succs) for task_id, succs in successors.items()}
        queue = [task_id for task_id, count in out_degree.items() if count == 0]
        ordered = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for dep in dependencies:
                if dep.get("successor") == current:
                    pred = dep.get("predecessor")
                    if pred in out_degree:
                        out_degree[pred] -= 1
                        if out_degree[pred] == 0:
                            queue.append(pred)

        if len(ordered) != len(task_map):
            ordered = list(task_map.keys())

        for task_id in ordered:
            task = task_map[task_id]
            duration = float(task.get("duration", 0))
            if successors[task_id]:
                task["late_finish"] = min(
                    task_map[succ].get("late_start", project_duration)
                    for succ in successors[task_id]
                )
            else:
                task["late_finish"] = project_duration
            task["late_start"] = task["late_finish"] - duration

        return list(task_map.values())

    async def _calculate_slack(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Calculate slack/float for tasks."""
        for task in tasks:
            task["slack"] = task.get("late_start", 0) - task.get("early_start", 0)
        return tasks

    async def _get_resource_availability(self, resources: dict[str, Any]) -> dict[str, Any]:
        """Get resource availability from Resource Management Agent."""
        # Future work: Integrate with Agent 11
        return resources

    async def _resource_leveling(
        self,
        tasks: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        resource_availability: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply resource leveling to schedule."""
        leveled = await self._forward_pass(tasks, dependencies)
        capacities: dict[str, float] = {}
        for key, value in resource_availability.items():
            if isinstance(value, dict):
                capacities[key] = float(value.get("capacity", 1.0))
            else:
                capacities[key] = float(value)

        usage: dict[str, dict[int, float]] = {key: {} for key in capacities}
        ordered = sorted(leveled, key=lambda t: t.get("early_start", 0))

        for task in ordered:
            duration = max(1, int(math.ceil(float(task.get("duration", 0) or 0))))
            required_resources = task.get("resources", [{"id": "default", "units": 1.0}])
            start = int(task.get("early_start", 0))
            while True:
                if self._resources_available(usage, capacities, required_resources, start, duration):
                    self._allocate_resources(usage, required_resources, start, duration)
                    task["resource_start"] = start
                    task["resource_finish"] = start + duration
                    break
                start += 1

        return ordered

    async def _calculate_resource_utilization(
        self, schedule: list[dict[str, Any]], resource_availability: dict[str, Any]
    ) -> dict[str, float]:
        """Calculate resource utilization percentages."""
        utilization: dict[str, float] = {}
        capacities: dict[str, float] = {}
        for key, value in resource_availability.items():
            capacities[key] = float(value.get("capacity", 1.0)) if isinstance(value, dict) else float(value)

        total_usage: dict[str, float] = {key: 0.0 for key in capacities}
        for task in schedule:
            duration = float(task.get("duration", 0) or 0)
            for resource in task.get("resources", []):
                resource_id = resource.get("id")
                units = float(resource.get("units", 1.0))
                if resource_id in total_usage:
                    total_usage[resource_id] += units * duration

        for resource_id, used in total_usage.items():
            capacity = capacities.get(resource_id, 1.0)
            utilization[resource_id] = used / max(capacity, 1.0)

        return utilization

    async def _calculate_schedule_extension(
        self, original_duration: float, leveled_schedule: list[dict[str, Any]]
    ) -> float:
        """Calculate schedule extension from resource leveling."""
        new_duration = await self._calculate_project_duration(leveled_schedule)
        return new_duration - original_duration

    def _resources_available(
        self,
        usage: dict[str, dict[int, float]],
        capacities: dict[str, float],
        required: list[dict[str, Any]],
        start: int,
        duration: int,
    ) -> bool:
        for resource in required:
            resource_id = resource.get("id", "default")
            units = float(resource.get("units", 1.0))
            capacity = capacities.get(resource_id, 1.0)
            for day in range(start, start + duration):
                used = usage.get(resource_id, {}).get(day, 0.0)
                if used + units > capacity:
                    return False
        return True

    def _allocate_resources(
        self,
        usage: dict[str, dict[int, float]],
        required: list[dict[str, Any]],
        start: int,
        duration: int,
    ) -> None:
        for resource in required:
            resource_id = resource.get("id", "default")
            units = float(resource.get("units", 1.0))
            usage.setdefault(resource_id, {})
            for day in range(start, start + duration):
                usage[resource_id][day] = usage[resource_id].get(day, 0.0) + units

    async def _sample_task_durations(
        self, tasks: list[dict[str, Any]], rng: random.Random | None = None
    ) -> list[dict[str, Any]]:
        """Sample task durations from probability distributions."""
        rng = rng or random.Random(self.simulation_seed)
        sampled_tasks = []
        for task in tasks:
            optimistic = task.get("optimistic_duration", task.get("duration", 0))
            most_likely = task.get("most_likely_duration", task.get("duration", 0))
            pessimistic = task.get("pessimistic_duration", task.get("duration", 0))
            duration = rng.triangular(float(optimistic), float(pessimistic), float(most_likely))
            sampled = dict(task)
            sampled["duration"] = duration
            sampled_tasks.append(sampled)
        return sampled_tasks

    async def _calculate_simulated_duration(
        self, tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
    ) -> float:
        """Calculate project duration for simulated iteration."""
        forward = await self._forward_pass(tasks, dependencies)
        duration = max((task.get("early_finish", 0) for task in forward), default=0)
        return float(duration)

    async def _calculate_percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def _calculate_schedule_risk(
        self, simulation_results: list[float], baseline_duration: float
    ) -> float:
        """Calculate schedule risk score."""
        if not simulation_results or baseline_duration == 0:
            return 0.5

        exceeded_count = sum(1 for d in simulation_results if d > baseline_duration)
        risk_score = exceeded_count / len(simulation_results)
        return risk_score

    async def _calculate_std_dev(self, data: list[float]) -> float:
        """Calculate standard deviation."""
        if not data:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance**0.5  # type: ignore

    async def _extract_risk_drivers(
        self, task_samples: dict[str, list[float]], totals: list[float]
    ) -> list[dict[str, Any]]:
        """Identify tasks contributing most to schedule risk."""
        if not totals:
            return []

        total_mean = sum(totals) / len(totals)
        total_variance = sum((t - total_mean) ** 2 for t in totals)
        drivers = []

        for task_id, samples in task_samples.items():
            if not samples:
                continue
            sample_mean = sum(samples) / len(samples)
            covariance = sum((s - sample_mean) * (t - total_mean) for s, t in zip(samples, totals))
            correlation = covariance / (total_variance or 1)
            spread = max(samples) - min(samples)
            drivers.append(
                {
                    "task_id": task_id,
                    "correlation": round(correlation, 3),
                    "spread": round(spread, 2),
                }
            )

        def _driver_key(item: dict[str, Any]) -> tuple[float, float]:
            correlation = item.get("correlation")
            spread = item.get("spread")
            correlation_value = float(correlation) if correlation is not None else 0.0
            spread_value = float(spread) if spread is not None else 0.0
            return abs(correlation_value), spread_value

        drivers.sort(key=_driver_key, reverse=True)
        return drivers[:5]

    async def _identify_optimization_opportunities(
        self, schedule: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify schedule optimization opportunities."""
        return [
            {"type": "parallel_tasks", "description": "Parallelize tasks with no dependencies"},
            {"type": "fast_track", "description": "Fast-track critical path tasks"},
            {"type": "crash", "description": "Crash critical path by adding resources"},
        ]

    async def _apply_optimizations(
        self, schedule: dict[str, Any], opportunities: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply optimizations to schedule."""
        # Future work: Implement optimization logic
        return schedule

    async def _calculate_improvements(
        self, original: dict[str, Any], optimized: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate improvements from optimization."""
        return {
            "duration_reduction": original.get("project_duration_days", 0)
            - optimized.get("project_duration_days", 0)
        }

    async def _generate_optimization_recommendations(
        self, opportunities: list[dict[str, Any]]
    ) -> list[str]:
        """Generate optimization recommendations."""
        return [opp.get("description") for opp in opportunities]  # type: ignore

    async def _create_scenario(
        self, schedule: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        """Create scenario schedule with modified parameters."""
        # Future work: Apply scenario parameters
        return schedule.copy()

    async def _recalculate_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        """Recalculate schedule with changes."""
        # Future work: Recalculate CPM
        return schedule

    async def _compare_schedules(
        self, baseline: dict[str, Any], scenario: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare two schedules."""
        return {
            "duration_difference": scenario.get("project_duration_days", 0)
            - baseline.get("project_duration_days", 0),
            "cost_impact": 0,
            "resource_impact": {},
        }

    async def _generate_scenario_recommendation(self, comparison: dict[str, Any]) -> str:
        """Generate recommendation based on scenario comparison."""
        if comparison.get("duration_difference", 0) < 0:
            return "Scenario reduces project duration. Consider implementing."
        else:
            return "Scenario increases project duration. Not recommended."

    async def _calculate_schedule_variance(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> float:
        """Calculate schedule variance in days."""
        planned = baseline.get("project_duration_days", 0)
        actual = schedule.get("project_duration_days", 0)
        return planned - actual  # type: ignore

    async def _calculate_spi(self, schedule: dict[str, Any], baseline: dict[str, Any]) -> float:
        """Calculate Schedule Performance Index."""
        # Future work: Calculate actual SPI using earned value
        return 1.0  # Baseline

    async def _identify_delayed_tasks(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify delayed tasks."""
        # Future work: Compare task dates to baseline
        return []

    async def _identify_critical_path_changes(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> list[str]:
        """Identify changes to critical path."""
        # Future work: Compare critical paths
        return []

    async def _forecast_completion_date(self, schedule: dict[str, Any], spi: float) -> str:
        """Forecast completion date based on SPI."""
        # Future work: Calculate forecast using SPI
        return datetime.utcnow().isoformat()

    async def _recommend_sprint_backlog(
        self, backlog_items: list[dict[str, Any]], team_velocity: float, team_capacity: float
    ) -> list[dict[str, Any]]:
        """Recommend sprint backlog items."""
        # Sort by priority and select items that fit capacity
        sorted_items = sorted(backlog_items, key=lambda x: x.get("priority", 0), reverse=True)

        selected = []
        total_points = 0

        for item in sorted_items:
            points = item.get("story_points", 0)
            if total_points + points <= team_capacity:
                selected.append(item)
                total_points += points

        return selected

    async def _generate_burndown_forecast(
        self, total_story_points: float, sprint_duration_days: int
    ) -> list[dict[str, Any]]:
        """Generate burndown forecast."""
        burndown = []
        daily_velocity = (
            total_story_points / sprint_duration_days if sprint_duration_days > 0 else 0
        )

        for day in range(sprint_duration_days + 1):
            remaining = max(0, total_story_points - (daily_velocity * day))
            burndown.append({"day": day, "remaining_points": remaining})

        return burndown

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Schedule & Planning Agent...")
        # Future work: Close database connections
        # Future work: Close external API connections
        # Future work: Cancel pending monitoring tasks
        # Future work: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "schedule_creation",
            "wbs_conversion",
            "duration_estimation",
            "dependency_mapping",
            "critical_path_analysis",
            "resource_constrained_scheduling",
            "monte_carlo_simulation",
            "schedule_risk_analysis",
            "milestone_tracking",
            "schedule_optimization",
            "what_if_analysis",
            "baseline_management",
            "variance_tracking",
            "sprint_planning",
            "burndown_forecasting",
        ]
