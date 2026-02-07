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
from integrations.services.integration import (
    AIModelService,
    AnalyticsClient,
    CacheClient,
    CacheSettings,
    DatabricksMonteCarloClient,
    EventBusClient,
    EventEnvelope,
    ExternalSyncClient,
    ExternalSyncSettings,
    ModelTask,
    PersistenceSettings,
    SqlRepository,
    create_sql_engine,
    Base,
)
from integrations.services.integration.ml import AzureMLClient


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
        self.enable_ai_model_service = config.get("enable_ai_model_service", True) if config else True
        self.enable_ml_simulation = config.get("enable_ml_simulation", True) if config else True
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
        self.integration_event_bus = (
            config.get("integration_event_bus") if config else None
        ) or (EventBusClient() if self.enable_event_publishing else None)
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
        self.ai_model_service = AIModelService() if self.enable_ai_model_service else None
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
        self.ai_duration_model_id: str | None = None
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
        self.financial_agent = config.get("financial_agent") if config else None
        self.program_agent = config.get("program_agent") if config else None

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Schedule & Planning Agent...")


        if self.event_bus:
            self.event_bus.subscribe("risk.updated", self._handle_risk_event)
            self.event_bus.subscribe("resource.updated", self._handle_resource_event)

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
        dependencies = await self._suggest_dependencies(tasks_with_durations)
        for dependency in dependencies:
            await self._publish_dependency_added({"schedule_id": schedule_id}, dependency)

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
        cached = await self._get_cached_duration_estimates(project_context, tasks)
        if cached:
            return cached

        team_performance = float(project_context.get("team_performance", 1.0))
        if self.azure_ml_client and not self.duration_model_id:
            historical = await self._get_historical_durations("project", "medium")
            artifact = self.azure_ml_client.train_duration_model(
                historical,
                team_performance,
                {"project_id": project_context.get("project_id")},
            )
            self.duration_model_id = artifact.model_id

        if self.ai_model_service and not self.ai_duration_model_id:
            historical = await self._get_historical_durations("project", "medium")
            training = self.ai_model_service.train_model(ModelTask.SCHEDULE_ESTIMATION, historical)
            self.ai_duration_model_id = training.record.model_id
            self.ai_model_service.deploy_model(self.ai_duration_model_id)

        duration_estimates: dict[str, dict[str, Any]] = {}

        for task in tasks:
            task_id = task.get("task_id")
            if not task_id:
                continue
            task_name = task.get("name", "")
            complexity = task.get("complexity", "medium")

            historical_data = await self._get_historical_durations(task_name, complexity)

            ml_estimate = None
            if self.ai_model_service and self.ai_duration_model_id:
                features = self._build_duration_features(task, project_context)
                ml_estimate = self.ai_model_service.predict(self.ai_duration_model_id, features)

            azure_estimate = None
            if self.azure_ml_client and self.duration_model_id:
                azure_estimate = self.azure_ml_client.predict_duration(self.duration_model_id, complexity)

            base_estimate = await self._combine_duration_estimates(
                historical_data, ml_estimate, azure_estimate
            )

            optimistic, most_likely, pessimistic = await self._calculate_pert_estimate(
                task, historical_data, base_estimate
            )

            expected_duration = (optimistic + 4 * most_likely + pessimistic) / 6

            duration_estimates[task_id] = {
                "optimistic": optimistic,
                "most_likely": most_likely,
                "pessimistic": pessimistic,
                "expected": expected_duration,
                "confidence": await self._estimate_confidence(historical_data),
                "unit": "days",
            }

        await self._cache_duration_estimates(project_context, tasks, duration_estimates)
        return duration_estimates

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

        if self.enable_persistence and self._sql_engine:
            await self._persist_schedule(schedule)

        for dependency in validated_dependencies:
            await self._publish_dependency_added(schedule, dependency)

        # Generate network diagram data
        network_diagram = await self._generate_network_diagram(
            schedule.get("tasks", []), validated_dependencies
        )

        await self._publish_schedule_updated(schedule, "dependencies.updated")

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

        previous_path = schedule.get("critical_path", [])
        schedule["tasks"] = tasks_with_slack
        schedule["critical_path"] = [t["task_id"] for t in critical_path_tasks]
        schedule["project_duration_days"] = project_duration

        if self.enable_persistence and self._sql_engine:
            await self._persist_schedule(schedule)

        if previous_path != schedule["critical_path"]:
            await self._publish_critical_path_changed(schedule, previous_path, schedule["critical_path"])

        await self._publish_schedule_updated(schedule, "schedule.updated")

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
        resource_availability = await self._get_resource_availability(resources)

        # Apply resource leveling
        leveled_schedule = await self._resource_leveling(tasks, dependencies, resource_availability)

        # Recalculate critical path with resource constraints
        resource_critical_path = await self._calculate_critical_path(schedule_id)

        # Calculate resource utilization
        utilization = await self._calculate_resource_utilization(
            leveled_schedule, resource_availability
        )

        schedule["tasks"] = leveled_schedule
        schedule["resource_leveled_at"] = datetime.utcnow().isoformat()
        if self.enable_persistence and self._sql_engine:
            await self._persist_schedule(schedule)
        await self._publish_schedule_updated(schedule, "schedule.resource_leveled")

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

        if self.cache_client:
            cached = self.cache_client.get(self._simulation_cache_key(schedule_id))
            if cached and cached.get("iterations") == iterations:
                return {"schedule_id": schedule_id, **cached}

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
        elif self.ai_model_service and self.enable_ml_simulation:
            simulation_results = await self._run_ml_simulation(tasks, dependencies, iterations)
            p50 = await self._calculate_percentile(simulation_results, 50)
            p80 = await self._calculate_percentile(simulation_results, 80)
            p90 = await self._calculate_percentile(simulation_results, 90)
            p95 = await self._calculate_percentile(simulation_results, 95)
            distribution_stats = {
                "min": min(simulation_results) if simulation_results else 0,
                "max": max(simulation_results) if simulation_results else 0,
                "mean": sum(simulation_results) / len(simulation_results) if simulation_results else 0,
            }
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

        schedule["simulation"] = {
            "iterations": iterations,
            "p50_duration": p50,
            "p80_duration": p80,
            "p90_duration": p90,
            "p95_duration": p95,
            "risk_score": risk_score,
            "distribution": distribution_stats,
        }
        if self.enable_persistence and self._sql_engine:
            await self._persist_simulation(schedule, iterations, p50, p80, p90, p95, risk_score, distribution_stats)

        await self._publish_schedule_simulated(schedule, iterations, p50, p80, p90, p95, risk_score)

        response = {
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

        if self.cache_client:
            cache_key = self._simulation_cache_key(schedule_id)
            self.cache_client.set(cache_key, response, ttl_seconds=self.cache_ttl_seconds)

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

        return response

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
            "locked_by": "system",
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
        earned_value = await self._calculate_earned_value(schedule, baseline, tenant_id=tenant_id)
        spi = earned_value.get("schedule_performance_index", 1.0)

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
            "earned_value": earned_value,
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
        if not schedule and self.enable_persistence and self._sql_engine:
            schedule = await self._load_schedule_from_db(schedule_id)
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

    def _simulation_cache_key(self, schedule_id: str) -> str:
        return f"schedule:simulation:{schedule_id}"

    def _duration_cache_key(self, project_id: str, task_signature: str) -> str:
        return f"schedule:duration:{project_id}:{task_signature}"

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

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
        if not self.integration_event_bus and not self.event_bus:
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
        if self.event_bus:
            await self.event_bus.publish("schedule.created", envelope.to_payload())

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

    async def _publish_schedule_updated(self, schedule: dict[str, Any], event_type: str) -> None:
        if not self.integration_event_bus and not self.event_bus:
            return
        envelope = EventEnvelope(
            event_type=event_type,
            subject=f"schedule/{schedule.get('schedule_id')}",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "project_id": schedule.get("project_id"),
                "status": schedule.get("status"),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        if self.integration_event_bus:
            self.integration_event_bus.publish_event(envelope)
        if self.event_bus:
            await self.event_bus.publish(event_type, envelope.to_payload())

    async def _publish_dependency_added(
        self, schedule: dict[str, Any], dependency: dict[str, Any]
    ) -> None:
        if not self.integration_event_bus and not self.event_bus:
            return
        envelope = EventEnvelope(
            event_type="dependency.added",
            subject=f"schedule/{schedule.get('schedule_id')}/dependency/{dependency.get('predecessor')}-{dependency.get('successor')}",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "predecessor": dependency.get("predecessor"),
                "successor": dependency.get("successor"),
                "type": dependency.get("type"),
                "lag": dependency.get("lag"),
            },
        )
        if self.integration_event_bus:
            self.integration_event_bus.publish_event(envelope)
        if self.event_bus:
            await self.event_bus.publish("dependency.added", envelope.to_payload())

    async def _publish_critical_path_changed(
        self, schedule: dict[str, Any], previous: list[str], current: list[str]
    ) -> None:
        if not self.integration_event_bus and not self.event_bus:
            return
        envelope = EventEnvelope(
            event_type="critical_path.changed",
            subject=f"schedule/{schedule.get('schedule_id')}/critical-path",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "previous": previous,
                "current": current,
            },
        )
        if self.integration_event_bus:
            self.integration_event_bus.publish_event(envelope)
        if self.event_bus:
            await self.event_bus.publish("critical_path.changed", envelope.to_payload())

    async def _publish_schedule_simulated(
        self,
        schedule: dict[str, Any],
        iterations: int,
        p50: float,
        p80: float,
        p90: float,
        p95: float,
        risk_score: float,
    ) -> None:
        if not self.integration_event_bus and not self.event_bus:
            return
        envelope = EventEnvelope(
            event_type="schedule.simulated",
            subject=f"schedule/{schedule.get('schedule_id')}/simulation",
            data={
                "schedule_id": schedule.get("schedule_id"),
                "iterations": iterations,
                "p50_duration": p50,
                "p80_duration": p80,
                "p90_duration": p90,
                "p95_duration": p95,
                "risk_score": risk_score,
            },
        )
        if self.integration_event_bus:
            self.integration_event_bus.publish_event(envelope)
        if self.event_bus:
            await self.event_bus.publish("schedule.simulated", envelope.to_payload())

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
            start_date = self._parse_datetime(schedule.get("start_date"))
            end_date = self._parse_datetime(schedule.get("end_date"))
            schedule_row = repo.upsert_schedule(
                schedule_key=schedule.get("schedule_id", "schedule"),
                name=schedule.get("schedule_id", "schedule"),
                status=schedule.get("status", "draft"),
                project_id=schedule.get("project_id", ""),
                start_date=start_date,
                end_date=end_date,
            )

            repo.clear_schedule_children(schedule_row.id)

            for task in schedule.get("tasks", []):
                repo.add_task(
                    schedule_id=schedule_row.id,
                    task_key=task.get("task_id", ""),
                    name=task.get("name", ""),
                    duration_days=float(task.get("duration", 0) or 0),
                    status=task.get("status", "planned"),
                )
                await self._publish_task_updated(schedule, task)
                for resource in task.get("resources", []):
                    repo.add_resource_allocation(
                        schedule_id=schedule_row.id,
                        task_key=task.get("task_id", ""),
                        resource_id=resource.get("id", "default"),
                        skill=resource.get("skill", ""),
                        units=float(resource.get("units", 1.0)),
                        performance_score=float(resource.get("performance", 1.0)),
                    )

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
            await self._pull_external_updates(schedule)
        if self.enable_calendar_sync:
            self.external_sync_client.sync_calendar(
                schedule.get("schedule_id", ""),
                schedule.get("milestones", []),
            )

    async def _pull_external_updates(self, schedule: dict[str, Any]) -> None:
        if not self.external_sync_client:
            return
        updates = self.external_sync_client.pull_updates(schedule.get("schedule_id", ""))
        if not updates:
            return
        conflicts: list[dict[str, Any]] = []
        for update in updates:
            payload = update.payload
            conflicts.extend(self._apply_external_update(schedule, payload, update.timestamp.isoformat()))

        schedule.setdefault("external_sync", {})
        schedule["external_sync"]["last_synced_at"] = datetime.utcnow().isoformat()
        schedule["external_sync"]["conflicts"] = conflicts

        if self.enable_persistence and self._sql_engine:
            await self._persist_schedule(schedule)

        if conflicts:
            await self._publish_schedule_updated(schedule, "schedule.sync.conflict")
        else:
            await self._publish_schedule_updated(schedule, "schedule.synced")

    def _apply_external_update(
        self, schedule: dict[str, Any], payload: dict[str, Any], timestamp: str
    ) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        tasks = schedule.get("tasks", [])
        task_map = {task.get("task_id"): task for task in tasks}
        for incoming in payload.get("tasks", []):
            task_id = incoming.get("task_id")
            if not task_id:
                continue
            existing = task_map.get(task_id)
            if not existing:
                tasks.append(incoming)
                continue
            if existing.get("duration") != incoming.get("duration"):
                conflicts.append(
                    {
                        "task_id": task_id,
                        "field": "duration",
                        "local": existing.get("duration"),
                        "external": incoming.get("duration"),
                        "resolved_at": timestamp,
                        "resolution": "external",
                    }
                )
            existing.update(incoming)
        schedule["tasks"] = tasks
        for milestone in payload.get("milestones", []):
            schedule.setdefault("milestones", [])
            schedule["milestones"].append(milestone)
        return conflicts

    async def _wbs_to_tasks(self, wbs: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert WBS to flat task list."""
        tasks = []
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
        return [5.0, 7.0, 6.0]  # Baseline

    async def _get_cached_duration_estimates(
        self, project_context: dict[str, Any], tasks: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]] | None:
        if not self.cache_client:
            return None
        project_id = project_context.get("project_id", "default")
        signature = ",".join(sorted(task.get("task_id", "") for task in tasks))
        cache_key = self._duration_cache_key(project_id, signature)
        cached = self.cache_client.get(cache_key)
        return cached  # type: ignore

    async def _cache_duration_estimates(
        self,
        project_context: dict[str, Any],
        tasks: list[dict[str, Any]],
        estimates: dict[str, dict[str, Any]],
    ) -> None:
        if not self.cache_client:
            return
        project_id = project_context.get("project_id", "default")
        signature = ",".join(sorted(task.get("task_id", "") for task in tasks))
        cache_key = self._duration_cache_key(project_id, signature)
        self.cache_client.set(cache_key, estimates, ttl_seconds=self.cache_ttl_seconds)

    def _build_duration_features(
        self, task: dict[str, Any], project_context: dict[str, Any]
    ) -> dict[str, Any]:
        complexity = task.get("complexity", "medium")
        complexity_factor = {"low": 0.8, "medium": 1.0, "high": 1.3}.get(complexity, 1.0)
        resources = task.get("resources", []) or project_context.get("resources", [])
        skill_factor = self._calculate_skill_factor(resources)
        performance_factor = self._calculate_performance_factor(resources, project_context)
        return {
            "weight": skill_factor * performance_factor,
            "complexity": complexity_factor,
        }

    def _calculate_skill_factor(self, resources: list[dict[str, Any]]) -> float:
        if not resources:
            return 1.0
        scores = [float(resource.get("skill_level", 1.0)) for resource in resources]
        return max(0.5, min(1.5, sum(scores) / len(scores)))

    def _calculate_performance_factor(
        self, resources: list[dict[str, Any]], project_context: dict[str, Any]
    ) -> float:
        team_performance = float(project_context.get("team_performance", 1.0))
        resource_scores = [
            float(resource.get("performance", team_performance)) for resource in resources
        ] or [team_performance]
        avg = sum(resource_scores) / len(resource_scores)
        return max(0.5, min(1.5, 1 / avg if avg > 0 else 1.0))

    async def _combine_duration_estimates(
        self,
        historical_data: list[float],
        ml_estimate: float | None,
        azure_estimate: float | None,
    ) -> float:
        candidates = [value for value in [ml_estimate, azure_estimate] if value]
        if historical_data:
            candidates.append(sum(historical_data) / len(historical_data))
        if not candidates:
            return 5.0
        return sum(candidates) / len(candidates)

    async def _estimate_confidence(self, historical_data: list[float]) -> float:
        if len(historical_data) < 2:
            return 0.7
        avg = sum(historical_data) / len(historical_data)
        variance = sum((value - avg) ** 2 for value in historical_data) / len(historical_data)
        spread = variance**0.5
        confidence = 1.0 - min(0.5, spread / max(avg, 1.0))
        return max(0.5, min(0.95, confidence))

    async def _calculate_pert_estimate(
        self, task: dict[str, Any], historical_data: list[float], base_estimate: float
    ) -> tuple[float, float, float]:
        """Calculate PERT estimates (optimistic, most likely, pessimistic)."""
        if historical_data:
            avg = sum(historical_data) / len(historical_data)
            variance = sum((value - avg) ** 2 for value in historical_data) / len(historical_data)
            spread = max(0.5, variance**0.5)
        else:
            avg = base_estimate or 5.0
            spread = max(1.0, avg * 0.25)

        base = base_estimate or avg
        complexity = task.get("complexity", "medium")
        complexity_factor = {"low": 0.9, "medium": 1.0, "high": 1.2}.get(complexity, 1.0)
        base *= complexity_factor

        optimistic = max(0.5, base - spread)
        most_likely = max(0.5, base)
        pessimistic = max(optimistic + 0.5, base + spread * 1.3)

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

        def _priority(task: dict[str, Any]) -> float:
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
            base = 3.0
            for key, score in keywords:
                if key in name:
                    base = float(score)
                    break
            if self.ai_model_service and self.enable_dependency_ai and self.ai_duration_model_id:
                features = {"weight": len(name) / 10 if name else 1.0, "complexity": base / 3}
                ai_score = self.ai_model_service.predict(self.ai_duration_model_id, features)
                return base + ai_score / 10
            return base

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
        return resources

    async def _resource_leveling(
        self,
        tasks: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        resource_availability: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply resource leveling using a simple RCPSP serial schedule generation scheme."""
        forward = await self._forward_pass(tasks, dependencies)
        capacities: dict[str, float] = {}
        for key, value in resource_availability.items():
            if isinstance(value, dict):
                capacities[key] = float(value.get("capacity", 1.0))
            else:
                capacities[key] = float(value)

        usage: dict[str, dict[int, float]] = {key: {} for key in capacities}
        task_map = {task["task_id"]: dict(task) for task in forward}
        predecessors: dict[str, list[str]] = {task["task_id"]: [] for task in forward}
        for dep in dependencies:
            pred = dep.get("predecessor")
            succ = dep.get("successor")
            if pred in predecessors and succ in task_map:
                predecessors[succ].append(pred)

        remaining = set(task_map.keys())
        scheduled: list[dict[str, Any]] = []
        time_cursor = 0

        def ready_tasks(current_time: int) -> list[dict[str, Any]]:
            ready = []
            for task_id in remaining:
                preds = predecessors.get(task_id, [])
                if all(task_map[p].get("resource_finish", 0) <= current_time for p in preds):
                    ready.append(task_map[task_id])
            return ready

        while remaining:
            available = ready_tasks(time_cursor)
            if not available:
                time_cursor += 1
                continue

            available.sort(key=lambda t: (t.get("early_finish", 0), t.get("duration", 0)))
            for task in available:
                duration = max(1, int(math.ceil(float(task.get("duration", 0) or 0))))
                required_resources = task.get("resources", [{"id": "default", "units": 1.0}])
                start = max(time_cursor, int(task.get("early_start", 0)))
                while True:
                    if self._resources_available(usage, capacities, required_resources, start, duration):
                        self._allocate_resources(usage, required_resources, start, duration)
                        task["resource_start"] = start
                        task["resource_finish"] = start + duration
                        scheduled.append(task)
                        remaining.remove(task["task_id"])
                        break
                    start += 1
            time_cursor += 1

        return scheduled

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

    async def _run_ml_simulation(
        self,
        tasks: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        iterations: int,
    ) -> list[float]:
        rng = random.Random(self.simulation_seed)
        results: list[float] = []
        for _ in range(iterations):
            sampled = []
            for task in tasks:
                base = float(task.get("duration", 0) or 0)
                variance = float(task.get("duration_estimate", {}).get("pessimistic", base)) - base
                variance = max(0.5, variance)
                duration = max(0.5, rng.gauss(base, variance / 2))
                sampled.append(dict(task, duration=duration))
            duration_total = await self._calculate_simulated_duration(sampled, dependencies)
            results.append(duration_total)
        return results

    async def _persist_simulation(
        self,
        schedule: dict[str, Any],
        iterations: int,
        p50: float,
        p80: float,
        p90: float,
        p95: float,
        risk_score: float,
        distribution: dict[str, Any],
    ) -> None:
        if not self._sql_engine:
            return
        with Session(self._sql_engine) as session:
            repo = SqlRepository(session)
            schedule_row = repo.get_schedule_by_key(schedule.get("schedule_id", "schedule"))
            if not schedule_row:
                return
            repo.add_simulation_record(
                schedule_id=schedule_row.id,
                iterations=iterations,
                p50=p50,
                p80=p80,
                p90=p90,
                p95=p95,
                risk_score=risk_score,
                distribution=distribution,
            )

    async def _load_schedule_from_db(self, schedule_id: str) -> dict[str, Any] | None:
        if not self._sql_engine:
            return None
        with Session(self._sql_engine) as session:
            repo = SqlRepository(session)
            schedule_row = repo.get_schedule_by_key(schedule_id)
            if not schedule_row:
                return None
            tasks = [
                {
                    "task_id": record.task_key,
                    "name": record.name,
                    "duration": record.duration_days,
                    "status": record.status,
                }
                for record in repo.get_tasks(schedule_row.id)
            ]
            dependencies = [
                {
                    "predecessor": dep.predecessor_task_key,
                    "successor": dep.successor_task_key,
                    "type": dep.dependency_type,
                    "lag": dep.lag_days,
                }
                for dep in repo.get_dependencies(schedule_row.id)
            ]
            allocations: dict[str, list[dict[str, Any]]] = {}
            for allocation in repo.get_resource_allocations(schedule_row.id):
                allocations.setdefault(allocation.task_key, []).append(
                    {
                        "id": allocation.resource_id,
                        "skill": allocation.skill,
                        "units": allocation.units,
                        "performance": allocation.performance_score,
                    }
                )
            for task in tasks:
                task["resources"] = allocations.get(task["task_id"], [])

            return {
                "schedule_id": schedule_row.schedule_key,
                "project_id": schedule_row.project_id,
                "status": schedule_row.status,
                "tasks": tasks,
                "dependencies": dependencies,
                "start_date": schedule_row.start_date.isoformat()
                if schedule_row.start_date
                else None,
                "end_date": schedule_row.end_date.isoformat() if schedule_row.end_date else None,
                "loaded_from_db": True,
            }

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
        return schedule.copy()

    async def _recalculate_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        """Recalculate schedule with changes."""
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

    async def _calculate_earned_value(
        self, schedule: dict[str, Any], baseline: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        project_id = schedule.get("project_id", "")
        financials = await self._fetch_financial_actuals(project_id, tenant_id=tenant_id)
        progress = await self._fetch_schedule_progress(schedule, baseline)

        budget_at_completion = float(financials.get("budget_at_completion", 0))
        actual_cost = float(financials.get("actual_cost", 0))
        planned_value = budget_at_completion * float(progress.get("planned_percent", 0))
        earned_value = budget_at_completion * float(progress.get("percent_complete", 0))

        cpi = earned_value / actual_cost if actual_cost > 0 else 1.0
        spi = earned_value / planned_value if planned_value > 0 else 1.0

        result = {
            "budget_at_completion": budget_at_completion,
            "actual_cost": actual_cost,
            "planned_value": planned_value,
            "earned_value": earned_value,
            "percent_complete": progress.get("percent_complete", 0),
            "planned_percent": progress.get("planned_percent", 0),
            "cost_performance_index": cpi,
            "schedule_performance_index": spi,
            "calculated_at": datetime.utcnow().isoformat(),
        }

        if self.enable_persistence and self._sql_engine:
            await self._persist_earned_value(schedule, result)
        return result

    async def _fetch_financial_actuals(
        self, project_id: str, *, tenant_id: str
    ) -> dict[str, Any]:
        if self.financial_agent:
            response = await self.financial_agent.process(
                {
                    "action": "calculate_evm",
                    "project_id": project_id,
                    "tenant_id": tenant_id,
                    "context": {"tenant_id": tenant_id},
                }
            )
            return {
                "budget_at_completion": response.get("budget_at_completion", 0),
                "actual_cost": response.get("actual_cost", 0),
            }
        return {"budget_at_completion": 0.0, "actual_cost": 0.0}

    async def _fetch_schedule_progress(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> dict[str, float]:
        tasks = schedule.get("tasks", [])
        if not tasks:
            return {"percent_complete": 0.0, "planned_percent": 0.0}
        complete = sum(1 for task in tasks if task.get("status") in {"done", "completed"})
        percent_complete = complete / len(tasks)
        planned_duration = baseline.get("project_duration_days", 0) or 1
        actual_duration = schedule.get("project_duration_days", 0) or 1
        planned_percent = min(1.0, actual_duration / planned_duration)
        return {
            "percent_complete": percent_complete,
            "planned_percent": planned_percent,
        }

    async def _persist_earned_value(self, schedule: dict[str, Any], earned_value: dict[str, Any]) -> None:
        if not self._sql_engine:
            return
        with Session(self._sql_engine) as session:
            repo = SqlRepository(session)
            schedule_row = repo.get_schedule_by_key(schedule.get("schedule_id", "schedule"))
            if not schedule_row:
                return
            repo.add_earned_value_record(
                schedule_id=schedule_row.id,
                planned_value=float(earned_value.get("planned_value", 0)),
                earned_value=float(earned_value.get("earned_value", 0)),
                actual_cost=float(earned_value.get("actual_cost", 0)),
                spi=float(earned_value.get("schedule_performance_index", 1.0)),
                cpi=float(earned_value.get("cost_performance_index", 1.0)),
            )

    async def _identify_delayed_tasks(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify delayed tasks."""
        return []

    async def _identify_critical_path_changes(
        self, schedule: dict[str, Any], baseline: dict[str, Any]
    ) -> list[str]:
        """Identify changes to critical path."""
        return []

    async def _forecast_completion_date(self, schedule: dict[str, Any], spi: float) -> str:
        """Forecast completion date based on SPI."""
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

    def _handle_risk_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        severity = payload.get("severity") or payload.get("impact")
        if not project_id:
            return
        for schedule in self.schedules.values():
            if schedule.get("project_id") != project_id:
                continue
            if severity in {"high", "critical"}:
                for task in schedule.get("tasks", []):
                    task["duration"] = float(task.get("duration", 0) or 0) * 1.1
                schedule["risk_adjusted_at"] = datetime.utcnow().isoformat()

    def _handle_resource_event(self, payload: dict[str, Any]) -> None:
        resource_id = payload.get("resource_id")
        allocation = payload.get("allocation")
        if not resource_id or allocation is None:
            return
        for schedule in self.schedules.values():
            for task in schedule.get("tasks", []):
                for resource in task.get("resources", []):
                    if resource.get("id") == resource_id:
                        resource["units"] = float(allocation)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Schedule & Planning Agent...")

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
