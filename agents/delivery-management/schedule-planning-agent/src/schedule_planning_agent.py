"""
Schedule & Planning Agent

Purpose:
Constructs and manages project timelines, transforms WBS into schedules, maps task dependencies
and performs critical path analysis. Supports both predictive and adaptive planning.

Specification: agents/delivery-management/schedule-planning-agent/README.md
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from change_configuration_agent import ChangeConfigurationAgent

# Action handlers
from schedule_actions import (
    calculate_critical_path as _act_critical_path,
)
from schedule_actions import (
    create_schedule as _act_create_schedule,
)
from schedule_actions import (
    estimate_duration as _act_estimate_duration,
)
from schedule_actions import (
    generate_schedule_variants as _act_gen_variants,
)
from schedule_actions import (
    get_schedule as _act_get_schedule,
)
from schedule_actions import (
    manage_baseline as _act_manage_baseline,
)
from schedule_actions import (
    map_dependencies as _act_map_deps,
)
from schedule_actions import (
    optimize_schedule as _act_optimize,
)
from schedule_actions import (
    resource_constrained_schedule as _act_resource_sched,
)
from schedule_actions import (
    run_monte_carlo as _act_monte_carlo,
)
from schedule_actions import (
    sprint_planning as _act_sprint,
)
from schedule_actions import (
    track_milestones as _act_milestones,
)
from schedule_actions import (
    track_variance as _act_variance,
)
from schedule_actions import (
    update_schedule as _act_update,
)
from schedule_actions import (
    what_if_analysis as _act_what_if,
)
from schedule_actions.resource_scheduling import (
    get_resource_availability as _act_get_resource_avail,
)
from schedule_actions.resource_scheduling import (
    resource_leveling as _act_resource_leveling,
)
from schedule_utils import (
    get_schedule_state as _get_schedule_state,
)
from schedule_utils import (
    load_schedule_from_db as _load_schedule_from_db,
)
from schedule_utils import (
    sync_external_tools as _sync_external_tools,
)

from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from integrations.services.integration import (
    AIModelService,
    AnalyticsClient,
    Base,
    CacheClient,
    CacheSettings,
    DatabricksMonteCarloClient,
    EventBusClient,
    ExternalSyncClient,
    ExternalSyncSettings,
    PersistenceSettings,
    create_sql_engine,
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

    def __init__(self, agent_id: str = "schedule-planning-agent", config: dict[str, Any] | None = None):
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
        self.enable_ai_model_service = (
            config.get("enable_ai_model_service", True) if config else True
        )
        self.enable_ml_simulation = config.get("enable_ml_simulation", True) if config else True
        self.cache_ttl_seconds = config.get("cache_ttl_seconds", 600) if config else 600
        self.risk_adjustments_path = (
            Path(config.get("risk_adjustments_path"))
            if config and config.get("risk_adjustments_path")
            else Path(__file__).resolve().parents[4]
            / "ops" / "config" / "agents" / "risk_adjustments.yaml"
        )
        self.risk_adjustments = self._load_risk_adjustments_config()

        schedule_store_path = (
            Path(config.get("schedule_store_path", "data/project_schedules.json"))
            if config else Path("data/project_schedules.json")
        )
        baseline_store_path = (
            Path(config.get("schedule_baseline_store_path", "data/schedule_baselines.json"))
            if config else Path("data/schedule_baselines.json")
        )
        self.schedule_store = TenantStateStore(schedule_store_path)
        self.baseline_store = TenantStateStore(baseline_store_path)

        # Data stores
        self.schedules = {}  # type: ignore
        self.baselines = {}  # type: ignore
        self.dependencies = {}  # type: ignore
        self.milestones = {}  # type: ignore
        self.task_actuals = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.integration_event_bus = (config.get("integration_event_bus") if config else None) or (
            EventBusClient() if self.enable_event_publishing else None
        )
        self.analytics_client = AnalyticsClient() if self.enable_analytics else None
        self.cache_client = (
            CacheClient(
                CacheSettings(
                    provider=config.get("cache_provider", "in_memory") if config else "in_memory",
                    redis_url=config.get("redis_url") if config else None,
                    default_ttl_seconds=self.cache_ttl_seconds,
                )
            )
            if self.enable_cache else None
        )
        self.azure_ml_client = AzureMLClient() if self.enable_azure_ml else None
        self.ai_model_service = AIModelService() if self.enable_ai_model_service else None
        self.databricks_client = (
            DatabricksMonteCarloClient(seed=self.simulation_seed)
            if self.enable_databricks else None
        )
        self.external_sync_client = (
            ExternalSyncClient(
                ExternalSyncSettings(
                    enable_ms_project=config.get("enable_ms_project", False) if config else False,
                    enable_jira=config.get("enable_jira", False) if config else False,
                    enable_azure_devops=config.get("enable_azure_devops", False) if config else False,
                    enable_smartsheet=config.get("enable_smartsheet", False) if config else False,
                    enable_outlook=config.get("enable_outlook", False) if config else False,
                    enable_google_calendar=config.get("enable_google_calendar", False) if config else False,
                )
            )
            if self.enable_external_sync or self.enable_calendar_sync else None
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
        self.resource_capacity_agent = config.get("resource_capacity_agent") if config else None
        self.financial_agent = config.get("financial_agent") if config else None
        self.program_agent = config.get("program_agent") if config else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Schedule & Planning Agent...")
        if self.event_bus and hasattr(self.event_bus, "subscribe"):
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
            "create_schedule", "estimate_duration", "map_dependencies",
            "calculate_critical_path", "resource_constrained_schedule",
            "run_monte_carlo", "track_milestones", "optimize_schedule",
            "what_if_analysis", "generate_schedule_variants",
            "manage_baseline", "track_variance", "sprint_planning",
            "update_schedule", "get_schedule",
        ]
        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "create_schedule":
            if "project_id" not in input_data or "wbs" not in input_data:
                self.logger.warning("Missing project_id or wbs")
                return False
        elif action in ["what_if_analysis", "optimize_schedule"]:
            if "schedule_id" not in input_data:
                self.logger.warning("Missing schedule_id")
                return False
        elif action == "generate_schedule_variants":
            if "schedule_id" not in input_data:
                self.logger.warning("Missing schedule_id")
                return False
            if not isinstance(input_data.get("scenarios"), list):
                self.logger.warning("Missing scenarios list")
                return False
        elif action == "update_schedule":
            if "schedule_id" not in input_data:
                self.logger.warning("Missing schedule_id")
                return False
            if not input_data.get("updates"):
                self.logger.warning("Missing updates payload")
                return False
        return True

    # ------------------------------------------------------------------
    # Process routing
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process schedule and planning requests by dispatching to action handlers."""
        action = input_data.get("action", "create_schedule")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        dispatch = {
            "create_schedule": lambda: self._create_schedule(
                input_data.get("project_id"), input_data.get("wbs", {}),
                input_data.get("methodology", "predictive"),
                risk_data=input_data.get("risk_data"),
                dependency_results=input_data.get("dependency_results", {}),
                context=context, tenant_id=tenant_id,
            ),
            "estimate_duration": lambda: self._estimate_duration(
                input_data.get("tasks", []), input_data.get("project_context", {}),
            ),
            "map_dependencies": lambda: self._map_dependencies(
                input_data.get("schedule_id"), input_data.get("dependencies", []),
            ),
            "calculate_critical_path": lambda: self._calculate_critical_path(
                input_data.get("schedule_id"),
                risk_data=input_data.get("risk_data"),
                dependency_results=input_data.get("dependency_results", {}),
                context=context,
            ),
            "resource_constrained_schedule": lambda: self._resource_constrained_schedule(
                input_data.get("schedule_id"), input_data.get("resources", {}),
                tenant_id=tenant_id, context=context,
            ),
            "run_monte_carlo": lambda: self._run_monte_carlo(
                input_data.get("schedule_id"), input_data.get("iterations", 1000),
            ),
            "track_milestones": lambda: self._track_milestones(input_data.get("schedule_id")),
            "optimize_schedule": lambda: self._optimize_schedule(input_data.get("schedule_id")),
            "what_if_analysis": lambda: self._what_if_analysis(
                input_data.get("schedule_id"), input_data.get("what_if_params", {}),
            ),
            "generate_schedule_variants": lambda: self._generate_schedule_variants(
                input_data.get("schedule_id"), input_data.get("scenarios", []),
            ),
            "manage_baseline": lambda: self._manage_baseline(
                input_data.get("schedule_id"),
                tenant_id=tenant_id, correlation_id=correlation_id,
            ),
            "track_variance": lambda: self._track_variance(
                input_data.get("schedule_id"),
                tenant_id=tenant_id, correlation_id=correlation_id,
            ),
            "sprint_planning": lambda: self._sprint_planning(
                input_data.get("project_id"), input_data.get("sprint_data", {}),
            ),
            "update_schedule": lambda: self._update_schedule(
                input_data.get("schedule_id"), input_data.get("updates", {}),
                tenant_id=tenant_id, correlation_id=correlation_id,
            ),
            "get_schedule": lambda: self._get_schedule(
                input_data.get("schedule_id"), tenant_id=tenant_id,
            ),
        }

        handler = dispatch.get(action)
        if handler is None:
            raise ValueError(f"Unknown action: {action}")
        return await handler()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Schedule & Planning Agent...")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "schedule_creation", "wbs_conversion", "duration_estimation",
            "dependency_mapping", "critical_path_analysis",
            "resource_constrained_scheduling", "monte_carlo_simulation",
            "schedule_risk_analysis", "milestone_tracking",
            "schedule_optimization", "what_if_analysis",
            "baseline_management", "variance_tracking",
            "sprint_planning", "burndown_forecasting",
        ]

    # ------------------------------------------------------------------
    # Delegation wrappers -- preserve original method signatures
    # ------------------------------------------------------------------

    async def _create_schedule(self, project_id, wbs, methodology="predictive",
                               risk_data=None, dependency_results=None, context=None, *, tenant_id):
        return await _act_create_schedule(self, project_id, wbs, methodology,
            risk_data=risk_data, dependency_results=dependency_results,
            context=context, tenant_id=tenant_id)

    async def _estimate_duration(self, tasks, project_context):
        return await _act_estimate_duration(self, tasks, project_context)

    async def _map_dependencies(self, schedule_id, dependencies):
        return await _act_map_deps(self, schedule_id, dependencies)

    async def _calculate_critical_path(self, schedule_id, risk_data=None,
                                       dependency_results=None, context=None):
        return await _act_critical_path(self, schedule_id, risk_data=risk_data,
            dependency_results=dependency_results, context=context)

    async def _resource_constrained_schedule(self, schedule_id, resources, *,
                                             tenant_id="unknown", context=None):
        return await _act_resource_sched(self, schedule_id, resources,
            tenant_id=tenant_id, context=context)

    async def _run_monte_carlo(self, schedule_id, iterations=1000):
        return await _act_monte_carlo(self, schedule_id, iterations)

    async def _track_milestones(self, schedule_id):
        return await _act_milestones(self, schedule_id)

    async def _optimize_schedule(self, schedule_id):
        return await _act_optimize(self, schedule_id)

    async def _what_if_analysis(self, schedule_id, what_if_params):
        return await _act_what_if(self, schedule_id, what_if_params)

    async def _generate_schedule_variants(self, schedule_id, scenarios):
        return await _act_gen_variants(self, schedule_id, scenarios)

    async def _manage_baseline(self, schedule_id, *, tenant_id, correlation_id):
        return await _act_manage_baseline(self, schedule_id,
            tenant_id=tenant_id, correlation_id=correlation_id)

    async def _track_variance(self, schedule_id, *, tenant_id, correlation_id):
        return await _act_variance(self, schedule_id,
            tenant_id=tenant_id, correlation_id=correlation_id)

    async def _sprint_planning(self, project_id, sprint_data):
        return await _act_sprint(self, project_id, sprint_data)

    async def _update_schedule(self, schedule_id, updates, *, tenant_id, correlation_id):
        return await _act_update(self, schedule_id, updates,
            tenant_id=tenant_id, correlation_id=correlation_id)

    async def _get_schedule(self, schedule_id, *, tenant_id):
        return await _act_get_schedule(self, schedule_id, tenant_id=tenant_id)

    # CPM pass wrappers used by tests
    async def _forward_pass(self, tasks, dependencies):
        from schedule_actions.critical_path import forward_pass
        return await forward_pass(tasks, dependencies)

    async def _backward_pass(self, tasks, dependencies):
        from schedule_actions.critical_path import backward_pass
        return await backward_pass(tasks, dependencies)

    # Risk adjustment wrapper used by tests
    def _apply_risk_adjustments_to_tasks(self, tasks, risk_data):
        from schedule_utils import apply_risk_adjustments_to_tasks
        return apply_risk_adjustments_to_tasks(self, tasks, risk_data)

    # Utility wrappers used by tests
    async def _get_schedule_state(self, tenant_id, schedule_id):
        return await _get_schedule_state(self, tenant_id, schedule_id)

    async def _load_schedule_from_db(self, schedule_id):
        return await _load_schedule_from_db(self, schedule_id)

    async def _sync_external_tools(self, schedule):
        return await _sync_external_tools(self, schedule)

    async def _get_resource_availability(self, resources, *, context=None):
        return await _act_get_resource_avail(self, resources, context=context)

    async def _resource_leveling(self, tasks, dependencies, resource_availability):
        return await _act_resource_leveling(self, tasks, dependencies, resource_availability)

    # ------------------------------------------------------------------
    # Event handlers (registered as callbacks)
    # ------------------------------------------------------------------

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
                schedule["risk_adjusted_at"] = datetime.now(timezone.utc).isoformat()

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

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_risk_adjustments_config(self) -> dict[str, dict[str, float]]:
        defaults = {
            "high": {"schedule_buffer_pct": 0.2, "resource_load_factor": 1.25},
            "medium": {"schedule_buffer_pct": 0.1, "resource_load_factor": 1.1},
            "low": {"schedule_buffer_pct": 0.05, "resource_load_factor": 1.0},
            "default": {"schedule_buffer_pct": 0.0, "resource_load_factor": 1.0},
        }
        if not self.risk_adjustments_path.exists():
            return defaults
        try:
            payload = yaml.safe_load(self.risk_adjustments_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError, ValueError):
            return defaults
        configured = payload.get("risk_adjustments", {}) if isinstance(payload, dict) else {}
        normalized: dict[str, dict[str, float]] = {}
        for level, values in configured.items():
            if not isinstance(values, dict):
                continue
            normalized[str(level).lower()] = {
                "schedule_buffer_pct": float(values.get("schedule_buffer_pct", 0.0) or 0.0),
                "resource_load_factor": float(values.get("resource_load_factor", 1.0) or 1.0),
            }
        return {**defaults, **normalized}
