"""
Resource & Capacity Management Agent

Purpose:
Manages both supply of resources (people, equipment, skills) and demand from projects
and programs. Provides real-time insights into availability, utilization and skill gaps.

Specification: agents/delivery-management/resource-management-agent/README.md
"""

import asyncio
import importlib.util
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

from data_quality.rules import evaluate_quality_rules  # noqa: E402

try:
    from events import ResourceAllocationCreatedEvent  # noqa: E402
except Exception:
    from packages.contracts.src.events import ResourceAllocationCreatedEvent  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402

# Action handlers
from resource_actions import (  # noqa: E402
    handle_add_resource,
    handle_allocate_resource,
    handle_approve_request,
    handle_delete_resource,
    handle_forecast_capacity,
    handle_get_availability,
    handle_get_resource_pool,
    handle_get_utilization,
    handle_identify_conflicts,
    handle_match_skills,
    handle_plan_capacity,
    handle_request_resource,
    handle_scenario_analysis,
    handle_search_resources,
    handle_update_resource,
    refresh_capacity_allocations,
    sync_hr_systems,
    sync_training_records,
)

# Internal helpers
from resource_actions.helpers import (  # noqa: E402
    adjust_capacity_forecast,
    adjust_demand_forecast,
    build_risk_capacity_recommendations,
    calculate_day_availability,
    forecast_capacity_for_scenario,
    get_performance_score,
    index_skills,
    load_risk_adjustments_config,
    merge_profiles,
)

# Re-export service classes and utils so existing imports keep working
from resource_models import (  # noqa: E402
    AIMLForecastClient,
    ApprovalWorkflowClient,
    AzureADClient,
    AzureSearchClient,
    EmbeddingClient,
    EventPublisher,
    LearningManagementClient,
    NotificationService,
    ResourceCapacityRepository,
    SimpleAnalyticsClient,
)
from resource_utils import (  # noqa: E402
    month_start,
)

from agents.common.connector_integration import (  # noqa: E402
    CalendarIntegrationService,
    DatabaseStorageService,
)
from agents.common.integration_services import ForecastingModel  # noqa: E402
from agents.common.scenario import ScenarioEngine  # noqa: E402
from agents.runtime import BaseAgent, get_event_bus  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402


class ResourceCapacityAgent(BaseAgent):
    """
    Resource & Capacity Management Agent.

    Manages centralized resource pool, demand intake, skill matching, capacity
    planning/forecasting, scenario analysis, and HR/timesheet integration.
    """

    def __init__(
        self,
        agent_id: str = "resource-management-agent",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        cfg = config or {}
        self.max_allocation_threshold = float(cfg.get("max_allocation_threshold", 1.0))
        self.skill_matching_threshold = float(cfg.get("skill_matching_threshold", 0.70))
        self.forecast_horizon_months = int(cfg.get("forecast_horizon_months", 12))
        self.utilization_target = float(cfg.get("utilization_target", 0.85))
        self.risk_adjustments_path = (
            Path(cfg["risk_adjustments_path"])
            if cfg.get("risk_adjustments_path")
            else Path(__file__).resolve().parents[4]
            / "ops"
            / "config"
            / "agents"
            / "risk_adjustments.yaml"
        )
        self.skill_match_weights: dict[str, Any] = cfg.get(
            "skill_match_weights",
            {"skills": 0.6, "availability": 0.2, "cost": 0.1, "performance": 0.1},
        )
        self.default_working_hours_per_day = int(cfg.get("working_hours_per_day", 8))
        self.default_working_days: list[int] = list(cfg.get("working_days", [0, 1, 2, 3, 4]))
        self.max_concurrent_allocations = int(cfg.get("max_concurrent_allocations", 3))
        self.enforce_allocation_constraints = bool(cfg.get("enforce_allocation_constraints", True))
        self.attrition_rate = float(cfg.get("attrition_rate", 0.0))
        self.seasonality_factors: dict[str, Any] = cfg.get("seasonality_factors", {})
        self.training_capacity_impact = float(cfg.get("training_capacity_impact", 0.1))
        self.skill_development_uplift = float(cfg.get("skill_development_uplift", 0.05))
        self.org_structure: dict[str, Any] = cfg.get("org_structure", {})
        self.approval_routing: dict[str, Any] = cfg.get("approval_routing", {})
        self.default_tenant_id: str = cfg.get("default_tenant_id", "system")
        self.hr_profile_provider = cfg.get("hr_profile_provider")

        self.resource_store = TenantStateStore(
            Path(cfg.get("resource_store_path", "data/resource_pool.json"))
        )
        self.allocation_store = TenantStateStore(
            Path(cfg.get("allocation_store_path", "data/resource_allocations.json"))
        )
        self.calendar_store = TenantStateStore(
            Path(cfg.get("calendar_store_path", "data/resource_calendars.json"))
        )

        # In-memory data stores
        self.resource_pool: dict[str, Any] = {}
        self.capacity_calendar: dict[str, Any] = {}
        self.allocations: dict[str, Any] = {}
        self.demand_requests: dict[str, Any] = {}
        self.utilization_metrics: dict[str, Any] = {}
        self.training_records: dict[str, dict[str, Any]] = {}
        self.performance_scores: dict[str, float] = {}

        self.event_bus = cfg.get("event_bus") or get_event_bus()
        self.db_service: DatabaseStorageService | None = None
        self.forecasting_model: ForecastingModel | None = None
        self.ml_forecast_client = cfg.get("ml_forecast_client") or AIMLForecastClient(
            os.getenv("AZURE_ML_ENDPOINT"), os.getenv("AZURE_ML_API_KEY")
        )
        self.repository = ResourceCapacityRepository(os.getenv("RESOURCE_CAPACITY_DATABASE_URL"))
        self.graph_client: AzureADClient | None = None
        self.calendar_service = CalendarIntegrationService(cfg.get("calendar"))
        self.embedding_client: EmbeddingClient | None = None
        self.search_client: AzureSearchClient | None = None
        self.event_publisher = EventPublisher(
            os.getenv("AZURE_SERVICEBUS_CONNECTION_STRING"),
            os.getenv("AZURE_SERVICEBUS_QUEUE_NAME"),
        )
        self.notification_service: NotificationService | None = None
        self.redis_client: Any | None = None
        self._skills_indexed = False

        self.analytics_client = cfg.get("analytics_client")
        if self.analytics_client is None:
            if importlib.util.find_spec("pydantic_settings") is None:
                self.analytics_client = SimpleAnalyticsClient()
            else:
                from integrations.services.integration.analytics import AnalyticsClient

                self.analytics_client = AnalyticsClient()

        self.training_client = cfg.get("training_client") or LearningManagementClient(
            os.getenv("MOODLE_LMS_ENDPOINT"),
            os.getenv("MOODLE_LMS_TOKEN"),
            os.getenv("COURSERA_BUSINESS_ENDPOINT"),
            os.getenv("COURSERA_BUSINESS_TOKEN"),
            training_records=cfg.get("training_records"),
        )
        self.approval_client = cfg.get("approval_client") or ApprovalWorkflowClient(
            cfg.get("approval_agent"), self.event_bus
        )
        environment = os.getenv("ENVIRONMENT", "dev")
        self.resource_optimization_enabled = cfg.get(
            "resource_optimization_enabled",
            is_feature_enabled("resource_optimization", environment=environment, default=False),
        )
        self.scenario_engine = ScenarioEngine()
        self.risk_adjustments = load_risk_adjustments_config(self)

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Resource & Capacity Management Agent...")

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.forecasting_model = ForecastingModel()

        azure_client_id = os.getenv("AZURE_CLIENT_ID")
        azure_tenant_id = os.getenv("AZURE_TENANT_ID")
        azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
        if azure_client_id and azure_tenant_id and azure_client_secret:
            self.graph_client = AzureADClient(azure_client_id, azure_tenant_id, azure_client_secret)
        self.embedding_client = EmbeddingClient(
            os.getenv("AZURE_OPENAI_ENDPOINT"),
            os.getenv("AZURE_OPENAI_API_KEY"),
            os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        )
        self.search_client = AzureSearchClient(
            os.getenv("AZURE_SEARCH_ENDPOINT"),
            os.getenv("AZURE_SEARCH_API_KEY"),
            os.getenv("AZURE_SEARCH_INDEX"),
        )
        self.notification_service = NotificationService(
            self.graph_client,
            acs_connection_string=os.getenv("AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING"),
            acs_sender=os.getenv("AZURE_COMMUNICATION_EMAIL_SENDER"),
        )
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            from redis import Redis

            self.redis_client = Redis.from_url(redis_url, decode_responses=True)

        await sync_hr_systems(self)
        await sync_training_records(self)
        await refresh_capacity_allocations(self)
        self.logger.info("Resource & Capacity Management Agent initialized")
        self._subscribe_to_events()

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        valid_actions = {
            "add_resource",
            "update_resource",
            "delete_resource",
            "request_resource",
            "approve_request",
            "search_resources",
            "match_skills",
            "forecast_capacity",
            "plan_capacity",
            "scenario_analysis",
            "allocate_resource",
            "get_availability",
            "get_utilization",
            "identify_conflicts",
            "get_resource_pool",
            "aggregate_portfolio_demand",
            "route_recommendation",
        }
        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False
        if action == "add_resource":
            resource_data = input_data.get("resource", {})
            for field in ["resource_id", "name", "role"]:
                if field not in resource_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "update_resource":
            if "resource_id" not in input_data.get("resource", {}):
                self.logger.warning("Missing required field: resource_id")
                return False
        elif action == "delete_resource":
            if not input_data.get("resource_id"):
                self.logger.warning("Missing required field: resource_id")
                return False
        elif action == "request_resource":
            request_data = input_data.get("request", {})
            for field in ["project_id", "required_skills", "start_date", "end_date"]:
                if field not in request_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Dispatch resource and capacity management actions to sub-module handlers."""
        action = input_data.get("action", "add_resource")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "add_resource":
            return await handle_add_resource(
                self, input_data.get("resource", {}), tenant_id=tenant_id
            )
        if action == "update_resource":
            return await handle_update_resource(
                self, input_data.get("resource", {}), tenant_id=tenant_id
            )
        if action == "delete_resource":
            return await handle_delete_resource(
                self, input_data.get("resource_id", ""), tenant_id=tenant_id
            )
        if action == "request_resource":
            return await handle_request_resource(
                self, input_data.get("request", {}), tenant_id=tenant_id
            )
        if action == "approve_request":
            return await handle_approve_request(
                self,
                input_data.get("request_id", ""),
                input_data.get("approval_decision", {}),
                tenant_id=tenant_id,
            )
        if action == "search_resources":
            return await handle_search_resources(self, input_data.get("search_criteria", {}))
        if action == "match_skills":
            return await handle_match_skills(
                self, input_data.get("skills_required", []), input_data.get("project_context", {})
            )
        if action == "forecast_capacity":
            return await handle_forecast_capacity(self, input_data.get("filters", {}))
        if action == "plan_capacity":
            return await handle_plan_capacity(self, input_data.get("planning_horizon", {}))
        if action == "scenario_analysis":
            return await handle_scenario_analysis(self, input_data.get("scenario_params", {}))
        if action == "allocate_resource":
            return await handle_allocate_resource(
                self,
                input_data.get("allocation", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        if action == "get_availability":
            return await handle_get_availability(
                self,
                input_data.get("resource_id", ""),
                input_data.get("date_range", {}),
                tenant_id=tenant_id,
            )
        if action == "get_utilization":
            return await handle_get_utilization(self, input_data.get("filters", {}))
        if action == "identify_conflicts":
            return await handle_identify_conflicts(self, input_data.get("filters", {}))
        if action == "get_resource_pool":
            return await handle_get_resource_pool(
                self, input_data.get("filters", {}), tenant_id=tenant_id
            )
        if action == "aggregate_portfolio_demand":
            return await self._aggregate_portfolio_demand(
                input_data.get("portfolio_id", ""),
                input_data.get("filters", {}),
                tenant_id=tenant_id,
            )
        if action == "route_recommendation":
            return await self._route_recommendation(
                input_data.get("recommendation", {}),
                tenant_id=tenant_id,
            )
        raise ValueError(f"Unknown action: {action}")

    # -------------------------------------------------------------------------
    # Infrastructure methods — called by sub-module action/helper functions
    # -------------------------------------------------------------------------

    async def _persist_resource_schedule(
        self,
        resource_id: str,
        schedule: dict[str, Any],
        *,
        tenant_id: str,
        availability: float | None = None,
    ) -> None:
        self.repository.upsert_resource_schedule(resource_id, schedule, availability)
        if self.db_service:
            await self.db_service.store(
                "resource_schedules",
                resource_id,
                {
                    "resource_id": resource_id,
                    "schedule": schedule,
                    "availability": availability,
                    "tenant_id": tenant_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if self.redis_client:
            self.redis_client.set(f"resource_schedule:{resource_id}", json.dumps(schedule), ex=3600)

    async def _generate_request_id(self) -> str:
        return f"REQ-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    async def _generate_allocation_id(self) -> str:
        return f"ALLOC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    async def _validate_resource_record(
        self, resource_profile: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        record = {
            "id": resource_profile.get("resource_id"),
            "tenant_id": tenant_id,
            "name": resource_profile.get("name"),
            "role": resource_profile.get("role"),
            "location": resource_profile.get("location"),
            "status": resource_profile.get("status"),
            "created_at": resource_profile.get("created_at"),
            "metadata": {
                "skills": resource_profile.get("skills"),
                "certifications": resource_profile.get("certifications"),
                "availability": resource_profile.get("availability"),
                "cost_rate": resource_profile.get("cost_rate"),
            },
        }
        report = evaluate_quality_rules("resource", record)
        return {"is_valid": report.is_valid, "issues": [issue.__dict__ for issue in report.issues]}

    async def _publish_allocation_event(
        self, allocation: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = ResourceAllocationCreatedEvent(
            event_name="resource.allocation.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "allocation_id": allocation.get("allocation_id", ""),
                "resource_id": allocation.get("resource_id", ""),
                "project_id": allocation.get("project_id", ""),
                "start_date": allocation.get("start_date", ""),
                "end_date": allocation.get("end_date", ""),
                "allocation_percentage": allocation.get("allocation_percentage", 0),
            },
        )
        await self.event_bus.publish("resource.allocation.created", event.model_dump(mode="json"))

    async def _publish_resource_event(self, event_name: str, payload: dict[str, Any]) -> None:
        await self.event_bus.publish(event_name, payload)
        try:
            self.event_publisher.publish(event_name, payload)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: E501
            self.logger.warning("Service bus publish failed", extra={"error": str(exc)})

    async def _notify_requester(self, request: dict[str, Any]) -> None:
        requester = request.get("requested_by")
        if not requester or not self.notification_service:
            return
        try:
            self.notification_service.send_email(
                requester,
                f"Resource request {request.get('request_id')} status update",
                f"Request status: {request.get('status')}",
            )
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: E501
            self.logger.warning("Failed to send requester notification", extra={"error": str(exc)})

    async def _notify_project_manager(self, request: dict[str, Any]) -> None:
        manager = request.get("project_manager")
        if not manager or not self.notification_service:
            return
        try:
            self.notification_service.send_email(
                manager,
                f"Resource request approved for project {request.get('project_id')}",
                f"Allocated resource: {request.get('allocated_resource')}",
            )
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: E501
            self.logger.warning("Failed to send manager notification", extra={"error": str(exc)})

    def _subscribe_to_events(self) -> None:
        if not self.event_bus or not hasattr(self.event_bus, "subscribe"):
            return

        def _handle_schedule_change(payload: dict[str, Any]) -> None:
            self.logger.info("Received schedule change event", extra={"payload": payload})

        def _handle_approval_decision(payload: dict[str, Any]) -> None:
            asyncio.create_task(self._process_approval_decision(payload))

        try:
            self.event_bus.subscribe("schedule.changed", _handle_schedule_change)
            self.event_bus.subscribe("approval.decision", _handle_approval_decision)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: E501
            self.logger.warning("Failed to subscribe to schedule events", extra={"error": str(exc)})

    async def _process_approval_decision(self, payload: dict[str, Any]) -> None:
        if not payload.get("approval_id") or not payload.get("request_id"):
            return
        if payload.get("decision") not in {"approved", "rejected"}:
            return
        await handle_approve_request(
            self,
            payload["request_id"],
            {
                "approved": payload.get("decision") == "approved",
                "selected_resource_id": payload.get("selected_resource_id"),
                "comments": payload.get("comments", ""),
                "approver_id": payload.get("approver_id", "unknown"),
            },
            tenant_id=payload.get("tenant_id", self.default_tenant_id),
        )

    async def _acquire_lock(self, key: str, ttl_seconds: int = 10) -> bool:
        if not self.redis_client:
            return True
        return bool(self.redis_client.set(key, "locked", nx=True, ex=ttl_seconds))

    async def _release_lock(self, key: str) -> None:
        if self.redis_client:
            self.redis_client.delete(key)

    def _load_allocations(self, resource_id: str) -> list[dict[str, Any]]:
        if self.redis_client:
            cached = self.redis_client.lrange(f"resource_allocations:{resource_id}", 0, -1)
            if cached:
                parsed = [json.loads(item) for item in cached if item]
                if parsed:
                    return parsed
        return self.allocations.get(resource_id, [])

    async def _deactivate_resource(self, resource_id: str, *, reason: str) -> None:
        resource = self.resource_pool.get(resource_id)
        if not resource or resource.get("status") == "Inactive":
            return
        resource["status"] = "Inactive"
        resource["deactivated_at"] = datetime.now(timezone.utc).isoformat()
        resource["deactivation_reason"] = reason
        self.resource_pool[resource_id] = resource
        self.resource_store.upsert(self.default_tenant_id, resource_id, resource)
        await self._publish_resource_event("resource.updated", resource)

    async def _deactivate_missing_resources(self, active_resource_ids: set[str]) -> None:
        if not active_resource_ids:
            return
        for resource_id, resource in list(self.resource_pool.items()):
            if resource_id not in active_resource_ids and resource.get("source_system") in {
                "azure_ad",
                "workday",
                "sap_successfactors",
            }:
                await self._deactivate_resource(resource_id, reason="missing_from_hr_sync")

    # -------------------------------------------------------------------------
    # Delegating wrappers — thin pass-throughs called by action/helper modules
    # -------------------------------------------------------------------------

    async def _sync_hr_systems(self) -> None:
        await sync_hr_systems(self)

    async def _sync_training_records(self) -> None:
        await sync_training_records(self)

    async def _index_skills(self) -> None:
        await index_skills(self)

    async def _get_performance_score(
        self, resource_id: str, project_context: dict[str, Any]
    ) -> float:
        return await get_performance_score(self, resource_id, project_context)

    def _merge_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return merge_profiles(profiles)

    @staticmethod
    def _month_start(base: datetime, offset: int) -> datetime:
        return month_start(base, offset)

    def _get_attrition_rate(self) -> float:
        return self.attrition_rate or 0.0

    def _adjust_capacity_forecast(self, forecast: list[float]) -> list[dict[str, Any]]:
        return adjust_capacity_forecast(self, forecast)

    def _adjust_demand_forecast(self, forecast: list[float]) -> list[dict[str, Any]]:
        return adjust_demand_forecast(self, forecast)

    def _build_risk_capacity_recommendations(self, risk_data: dict[str, Any] | None) -> list[str]:
        return build_risk_capacity_recommendations(risk_data)

    def _risk_load_factor(self, risk_level: str | None) -> float:
        level = str(risk_level or "default").lower()
        return float(
            self.risk_adjustments.get(level, self.risk_adjustments["default"]).get(
                "resource_load_factor", 1.0
            )
        )

    def _resolve_allocation_risk_level(
        self, allocation: dict[str, Any], risk_data: dict[str, Any] | None
    ) -> str:
        if not risk_data:
            return "default"
        project_risk = str(risk_data.get("project_risk_level", "default")).lower()
        project_id = allocation.get("project_id")
        task_id = allocation.get("task_id")
        for item in risk_data.get("task_risks", []):
            if not isinstance(item, dict):
                continue
            if task_id and item.get("task_id") == task_id:
                return str(item.get("risk_level", project_risk)).lower()
            if project_id and item.get("project_id") == project_id:
                return str(item.get("risk_level", project_risk)).lower()
        return project_risk

    async def _calculate_resource_utilization(
        self, resource_id: str, risk_data: dict[str, Any] | None = None
    ) -> float:
        allocations = self.allocations.get(resource_id, [])
        total = sum(
            float(alloc.get("allocation_percentage", 0) or 0)
            * self._risk_load_factor(self._resolve_allocation_risk_level(alloc, risk_data))
            for alloc in allocations
            if alloc.get("status") == "Active"
        )
        return cast(float, total / 100)  # type: ignore

    async def _get_utilization_status(self, utilization: float) -> str:
        if utilization > 1.0:
            return "Over-allocated"
        if utilization >= self.utilization_target:
            return "Optimal"
        if utilization >= 0.5:
            return "Under-utilized"
        return "Significantly Under-utilized"

    async def _check_availability(
        self, resource_id: str, start_date: str, end_date: str, effort: float
    ) -> dict[str, Any]:
        calendar = self.capacity_calendar.get(resource_id, {}) or {
            "available_hours_per_day": self.default_working_hours_per_day,
            "working_days": self.default_working_days,
            "planned_leave": [],
            "holidays": [],
        }
        allocations = self.allocations.get(resource_id, [])
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        required_hours = calendar.get("available_hours_per_day", 8) * effort
        windows = []
        is_available = True
        current_date = start
        while current_date <= end:
            day_avail = await calculate_day_availability(
                self, resource_id, current_date, calendar, allocations
            )
            if day_avail.get("available_hours", 0) >= required_hours:
                windows.append(
                    {
                        "start": current_date.isoformat(),
                        "end": current_date.isoformat(),
                        "capacity": effort,
                    }
                )
            else:
                is_available = False
            current_date += timedelta(days=1)
        return {"is_available": is_available, "windows": windows}

    async def _identify_capacity_bottlenecks(
        self, capacity: list[dict[str, Any]], demand: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {
                "month": i,
                "capacity": float(cap.get("capacity", 0)),
                "demand": float(dem.get("demand", 0)),
                "shortfall": float(dem.get("demand", 0)) - float(cap.get("capacity", 0)),
            }
            for i, (cap, dem) in enumerate(zip(capacity, demand))
            if float(dem.get("demand", 0)) > float(cap.get("capacity", 0))
        ]

    async def _generate_capacity_recommendations(
        self, bottlenecks: list[dict[str, Any]]
    ) -> list[str]:
        if not bottlenecks:
            return []
        return [
            f"Capacity shortfall identified in {len(bottlenecks)} periods",
            "Consider hiring additional resources or outsourcing",
            "Review project priorities and timelines",
        ]

    async def _identify_capacity_gaps(self, forecast: dict[str, Any]) -> list[dict[str, Any]]:
        return forecast.get("bottlenecks", [])  # type: ignore

    async def _generate_mitigation_strategies(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {"strategy": "Hire permanent staff", "timeline": "3-6 months"},
            {"strategy": "Engage contractors", "timeline": "1-2 months"},
            {"strategy": "Cross-train existing staff", "timeline": "2-3 months"},
        ]

    async def _generate_hiring_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {"role": "Software Developer", "count": 2, "priority": "high"},
            {"role": "Project Manager", "count": 1, "priority": "medium"},
        ]

    async def _generate_training_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {"skill": "Cloud Architecture", "target_count": 3, "priority": "high"},
            {"skill": "Adaptive Methodologies", "target_count": 5, "priority": "medium"},
        ]

    async def _apply_scenario_changes(
        self, baseline: dict[str, Any], changes: dict[str, Any]
    ) -> dict[str, Any]:
        added = changes.get("add_resources", [])
        removed = changes.get("remove_resources", [])
        scenario = dict(baseline)
        scenario["resource_count"] = max(
            0, baseline.get("resource_count", 0) + len(added) - len(removed)
        )
        scenario["capacity_multiplier"] = float(changes.get("capacity_multiplier", 1.0))
        scenario["scope_multiplier"] = float(changes.get("scope_multiplier", 1.0))
        scenario["added_resources"] = added
        scenario["removed_resources"] = removed
        return scenario

    async def _calculate_scenario_metrics(self, scenario: dict[str, Any]) -> dict[str, Any]:
        forecast = await forecast_capacity_for_scenario(self, scenario)
        avg_cap = sum(item["capacity"] for item in forecast["future_capacity"]) / max(
            len(forecast["future_capacity"]), 1
        )
        avg_dem = sum(item["demand"] for item in forecast["future_demand"]) / max(
            len(forecast["future_demand"]), 1
        )
        avg_util = avg_dem / avg_cap if avg_cap else 0.0
        return {
            "average_utilization": avg_util,
            "resource_count": scenario.get("resource_count", 0),
            "average_capacity": avg_cap,
            "average_demand": avg_dem,
            "forecast": forecast,
            "cost_impact": avg_dem * scenario.get("average_cost_rate", 0.0),
            "schedule_impact": max(0.0, avg_dem - avg_cap),
        }

    async def _compare_scenarios(
        self, baseline: dict[str, Any], scenario: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "utilization_difference": scenario.get("average_utilization", 0)
            - baseline.get("average_utilization", 0),
            "resource_count_difference": scenario.get("resource_count", 0)
            - baseline.get("resource_count", 0),
            "cost_difference": scenario.get("cost_impact", 0) - baseline.get("cost_impact", 0),
            "schedule_difference": scenario.get("schedule_impact", 0)
            - baseline.get("schedule_impact", 0),
        }

    async def _generate_scenario_recommendation(self, comparison: dict[str, Any]) -> str:
        util_diff = comparison.get("utilization_difference", 0)
        if util_diff > 0.1:
            return "Scenario improves utilization significantly. Recommended."
        if util_diff < -0.1:
            return "Scenario decreases utilization. Not recommended."
        return "Scenario has minimal impact on utilization."

    # -------------------------------------------------------------------------
    # Portfolio-level demand aggregation
    # -------------------------------------------------------------------------

    async def _aggregate_portfolio_demand(
        self,
        portfolio_id: str,
        filters: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Aggregate planned resource demand across all projects in a portfolio.

        Rolls up demand by skill and role, compares against current supply,
        and identifies gaps at the portfolio level.
        """
        self.logger.info(
            "Aggregating portfolio demand: portfolio_id=%s, tenant_id=%s",
            portfolio_id,
            tenant_id,
        )

        # Collect all demand requests across projects
        demand_by_skill: dict[str, dict[str, Any]] = {}
        demand_by_role: dict[str, dict[str, Any]] = {}
        total_demand_hours = 0.0
        project_demands: list[dict[str, Any]] = []

        for request_id, request in self.demand_requests.items():
            project_id = request.get("project_id", "")
            req_portfolio = request.get("portfolio_id", portfolio_id)
            if portfolio_id and req_portfolio != portfolio_id:
                continue
            if request.get("status") in ("cancelled", "rejected"):
                continue

            req_skills = request.get("required_skills", [])
            req_role = request.get("role", "")
            hours = float(request.get("effort_hours", 0) or request.get("hours_per_week", 40))
            headcount = float(request.get("headcount", 1))

            for skill in req_skills:
                skill_name = skill if isinstance(skill, str) else skill.get("name", "")
                if not skill_name:
                    continue
                entry = demand_by_skill.setdefault(
                    skill_name,
                    {
                        "skill": skill_name,
                        "total_headcount": 0.0,
                        "total_hours": 0.0,
                        "project_count": 0,
                        "projects": [],
                        "min_proficiency": 1,
                    },
                )
                entry["total_headcount"] += headcount
                entry["total_hours"] += hours
                entry["project_count"] += 1
                entry["projects"].append(project_id)
                if isinstance(skill, dict):
                    entry["min_proficiency"] = max(
                        entry["min_proficiency"],
                        int(skill.get("proficiency_level", 1)),
                    )

            if req_role:
                role_entry = demand_by_role.setdefault(
                    req_role,
                    {
                        "role": req_role,
                        "total_headcount": 0.0,
                        "total_hours": 0.0,
                        "project_count": 0,
                        "projects": [],
                    },
                )
                role_entry["total_headcount"] += headcount
                role_entry["total_hours"] += hours
                role_entry["project_count"] += 1
                role_entry["projects"].append(project_id)

            total_demand_hours += hours * headcount
            project_demands.append(
                {
                    "project_id": project_id,
                    "request_id": request_id,
                    "skills": req_skills,
                    "role": req_role,
                    "headcount": headcount,
                    "hours": hours,
                    "start_date": request.get("start_date"),
                    "end_date": request.get("end_date"),
                    "priority": request.get("priority", "medium"),
                }
            )

        # Calculate supply from current resource pool
        supply_by_skill: dict[str, dict[str, Any]] = {}
        supply_by_role: dict[str, dict[str, Any]] = {}
        total_supply_hours = 0.0

        for resource_id, resource in self.resource_pool.items():
            if resource.get("status") not in ("Active", "active", "allocated"):
                continue
            role = resource.get("role", "")
            capacity = float(resource.get("capacity_hours_per_week", 40))
            alloc = float(resource.get("allocation_pct", 0)) / 100.0
            available_hours = capacity * (1 - alloc)
            total_supply_hours += available_hours

            # Legacy free-text skills
            skills = resource.get("skills", [])
            for skill in skills:
                if not isinstance(skill, str):
                    continue
                entry = supply_by_skill.setdefault(
                    skill,
                    {
                        "skill": skill,
                        "available_count": 0,
                        "available_hours": 0.0,
                        "avg_proficiency": 0.0,
                        "_proficiency_sum": 0,
                    },
                )
                entry["available_count"] += 1
                entry["available_hours"] += available_hours

            # Structured skills
            structured_skills = resource.get("structured_skills", [])
            for ss in structured_skills:
                if not isinstance(ss, dict):
                    continue
                skill_name = ss.get("name", "")
                if not skill_name:
                    continue
                entry = supply_by_skill.setdefault(
                    skill_name,
                    {
                        "skill": skill_name,
                        "available_count": 0,
                        "available_hours": 0.0,
                        "avg_proficiency": 0.0,
                        "_proficiency_sum": 0,
                    },
                )
                entry["available_count"] += 1
                entry["available_hours"] += available_hours
                entry["_proficiency_sum"] += int(ss.get("proficiency_level", 2))
                entry["avg_proficiency"] = entry["_proficiency_sum"] / entry["available_count"]

            if role:
                role_entry = supply_by_role.setdefault(
                    role,
                    {
                        "role": role,
                        "available_count": 0,
                        "available_hours": 0.0,
                    },
                )
                role_entry["available_count"] += 1
                role_entry["available_hours"] += available_hours

        # Calculate gaps
        skill_gaps: list[dict[str, Any]] = []
        for skill_name, demand in demand_by_skill.items():
            supply = supply_by_skill.get(
                skill_name,
                {
                    "available_count": 0,
                    "available_hours": 0.0,
                    "avg_proficiency": 0.0,
                },
            )
            gap = demand["total_headcount"] - supply.get("available_count", 0)
            hours_gap = demand["total_hours"] - supply.get("available_hours", 0.0)
            if gap > 0 or hours_gap > 0:
                skill_gaps.append(
                    {
                        "skill": skill_name,
                        "demand_headcount": demand["total_headcount"],
                        "supply_count": supply.get("available_count", 0),
                        "headcount_gap": max(0, gap),
                        "demand_hours": demand["total_hours"],
                        "supply_hours": supply.get("available_hours", 0.0),
                        "hours_gap": max(0, hours_gap),
                        "avg_supply_proficiency": supply.get("avg_proficiency", 0.0),
                        "min_required_proficiency": demand.get("min_proficiency", 1),
                        "project_count": demand["project_count"],
                        "severity": "critical" if gap >= 3 else "high" if gap >= 1 else "medium",
                    }
                )

        role_gaps: list[dict[str, Any]] = []
        for role_name, demand in demand_by_role.items():
            supply = supply_by_role.get(role_name, {"available_count": 0, "available_hours": 0.0})
            gap = demand["total_headcount"] - supply.get("available_count", 0)
            if gap > 0:
                role_gaps.append(
                    {
                        "role": role_name,
                        "demand_headcount": demand["total_headcount"],
                        "supply_count": supply.get("available_count", 0),
                        "headcount_gap": max(0, gap),
                        "project_count": demand["project_count"],
                    }
                )

        # Cleanup internal counters
        for entry in supply_by_skill.values():
            entry.pop("_proficiency_sum", None)

        # Generate recommendations
        recommendations: list[dict[str, Any]] = []
        for gap in sorted(skill_gaps, key=lambda g: g["headcount_gap"], reverse=True)[:5]:
            if gap["headcount_gap"] >= 3:
                recommendations.append(
                    {
                        "type": "hire",
                        "skill": gap["skill"],
                        "count": int(gap["headcount_gap"]),
                        "priority": "high",
                        "rationale": f"{gap['project_count']} projects need {gap['skill']}",
                    }
                )
            elif gap["headcount_gap"] >= 1:
                recommendations.append(
                    {
                        "type": "train",
                        "skill": gap["skill"],
                        "count": int(gap["headcount_gap"]),
                        "priority": "medium",
                        "rationale": f"Cross-train existing resources in {gap['skill']}",
                    }
                )

        result = {
            "status": "success",
            "action": "aggregate_portfolio_demand",
            "portfolio_id": portfolio_id,
            "summary": {
                "total_demand_hours": total_demand_hours,
                "total_supply_hours": total_supply_hours,
                "capacity_ratio": (
                    total_supply_hours / total_demand_hours if total_demand_hours else 1.0
                ),
                "unique_skills_demanded": len(demand_by_skill),
                "unique_roles_demanded": len(demand_by_role),
                "total_skill_gaps": len(skill_gaps),
                "total_role_gaps": len(role_gaps),
                "critical_gaps": sum(1 for g in skill_gaps if g["severity"] == "critical"),
            },
            "demand_by_skill": list(demand_by_skill.values()),
            "demand_by_role": list(demand_by_role.values()),
            "supply_by_skill": list(supply_by_skill.values()),
            "supply_by_role": list(supply_by_role.values()),
            "skill_gaps": sorted(skill_gaps, key=lambda g: g["headcount_gap"], reverse=True),
            "role_gaps": sorted(role_gaps, key=lambda g: g["headcount_gap"], reverse=True),
            "recommendations": recommendations,
            "project_demands": project_demands,
        }

        await self._publish_resource_event(
            "resource.portfolio_demand.aggregated",
            {
                "portfolio_id": portfolio_id,
                "tenant_id": tenant_id,
                "total_demand_hours": total_demand_hours,
                "total_supply_hours": total_supply_hours,
                "skill_gaps_count": len(skill_gaps),
            },
        )

        return result

    # -------------------------------------------------------------------------
    # HR workflow recommendation routing
    # -------------------------------------------------------------------------

    async def _route_recommendation(
        self,
        recommendation: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Route a capacity recommendation (hire, train, reallocate) to the
        appropriate HR system or workflow.

        Connects to Workday or SAP SuccessFactors connectors to initiate
        hiring requisitions, training requests, or reallocation workflows.
        """
        rec_type = recommendation.get("type", "")
        skill = recommendation.get("skill", "")
        count = int(recommendation.get("count", 1))
        priority = recommendation.get("priority", "medium")

        self.logger.info(
            "Routing recommendation: type=%s, skill=%s, count=%d, priority=%s",
            rec_type,
            skill,
            count,
            priority,
        )

        routing_result: dict[str, Any] = {
            "recommendation_id": f"REC-{uuid.uuid4().hex[:8]}",
            "type": rec_type,
            "skill": skill,
            "count": count,
            "priority": priority,
            "status": "routed",
            "routed_to": [],
            "actions_created": [],
        }

        if rec_type == "hire":
            routing_result = await self._route_hiring_recommendation(
                routing_result,
                recommendation,
                tenant_id=tenant_id,
            )
        elif rec_type == "train":
            routing_result = await self._route_training_recommendation(
                routing_result,
                recommendation,
                tenant_id=tenant_id,
            )
        elif rec_type == "reallocate":
            routing_result = await self._route_reallocation_recommendation(
                routing_result,
                recommendation,
                tenant_id=tenant_id,
            )
        elif rec_type == "contract":
            routing_result["routed_to"].append("vendor_procurement_agent")
            routing_result["actions_created"].append(
                {
                    "action": "create_contractor_request",
                    "skill": skill,
                    "count": count,
                    "priority": priority,
                }
            )
        else:
            routing_result["status"] = "unrecognised_type"
            routing_result["message"] = f"Unknown recommendation type: {rec_type}"

        await self._publish_resource_event(
            "resource.recommendation.routed",
            {
                "recommendation_id": routing_result["recommendation_id"],
                "type": rec_type,
                "tenant_id": tenant_id,
                "status": routing_result["status"],
            },
        )

        return {
            "status": "success",
            "action": "route_recommendation",
            "result": routing_result,
        }

    async def _route_hiring_recommendation(
        self,
        result: dict[str, Any],
        recommendation: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Route hiring recommendation to HR system (Workday or SAP SF)."""
        skill = recommendation.get("skill", "")
        count = int(recommendation.get("count", 1))
        role = recommendation.get("role", skill)

        # Determine target HR system
        hr_system = self.hr_profile_provider or "workday"
        result["routed_to"].append(hr_system)

        requisition = {
            "action": "create_requisition",
            "job_title": f"{role} ({skill})",
            "department": recommendation.get("department", ""),
            "headcount": count,
            "skills_required": [skill],
            "priority": recommendation.get("priority", "medium"),
            "rationale": recommendation.get("rationale", ""),
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result["actions_created"].append(requisition)

        # Route to approval workflow
        if self.approval_client:
            try:
                approval_req = {
                    "request_type": "hiring_requisition",
                    "request_id": result["recommendation_id"],
                    "payload": requisition,
                    "tenant_id": tenant_id,
                }
                self.approval_client.submit_request(approval_req)
                result["routed_to"].append("approval_workflow")
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                self.logger.warning("Failed to route hiring requisition to approval workflow")

        return result

    async def _route_training_recommendation(
        self,
        result: dict[str, Any],
        recommendation: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Route training recommendation to LMS and/or HR system."""
        skill = recommendation.get("skill", "")
        count = int(recommendation.get("count", 1))
        target_resources = recommendation.get("target_resources", [])

        result["routed_to"].append("learning_management_system")

        training_request = {
            "action": "create_training_plan",
            "skill": skill,
            "target_count": count,
            "target_resources": target_resources,
            "priority": recommendation.get("priority", "medium"),
            "rationale": recommendation.get("rationale", ""),
            "estimated_duration_weeks": recommendation.get("duration_weeks", 4),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result["actions_created"].append(training_request)

        # Check if LMS has relevant courses
        if self.training_client:
            try:
                courses = self.training_client.search_courses(skill)
                if courses:
                    training_request["matched_courses"] = courses[:3]
                    training_request["status"] = "courses_identified"
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                self.logger.warning("Failed to search LMS courses for skill %s", skill)

        return result

    async def _route_reallocation_recommendation(
        self,
        result: dict[str, Any],
        recommendation: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Route reallocation recommendation to resource management."""
        skill = recommendation.get("skill", "")
        source_project = recommendation.get("source_project", "")
        target_project = recommendation.get("target_project", "")
        resource_ids = recommendation.get("resource_ids", [])

        result["routed_to"].append("resource_management")

        reallocation = {
            "action": "reallocate_resources",
            "skill": skill,
            "source_project": source_project,
            "target_project": target_project,
            "resource_ids": resource_ids,
            "priority": recommendation.get("priority", "medium"),
            "rationale": recommendation.get("rationale", ""),
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result["actions_created"].append(reallocation)

        # Route to approval workflow for manager sign-off
        if self.approval_client:
            try:
                approval_req = {
                    "request_type": "resource_reallocation",
                    "request_id": result["recommendation_id"],
                    "payload": reallocation,
                    "tenant_id": tenant_id,
                }
                self.approval_client.submit_request(approval_req)
                result["routed_to"].append("approval_workflow")
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                self.logger.warning("Failed to route reallocation to approval workflow")

        return result

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Resource & Capacity Management Agent...")
        if self.redis_client:
            try:
                self.redis_client.close()
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: E501
                self.logger.warning("Failed to close Redis client", extra={"error": str(exc)})
        if self.db_service:
            try:
                await self.db_service.store(
                    "agent_events",
                    f"resource-capacity-cleanup-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                    {"status": "cleanup", "timestamp": datetime.now(timezone.utc).isoformat()},
                )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: E501
                self.logger.warning("Failed to flush events", extra={"error": str(exc)})
        self.repository.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "resource_pool_management",
            "demand_intake",
            "skill_matching",
            "capacity_planning",
            "capacity_forecasting",
            "scenario_modeling",
            "resource_allocation",
            "availability_tracking",
            "utilization_monitoring",
            "conflict_identification",
            "approval_routing",
            "cross_project_management",
            "what_if_analysis",
            "portfolio_demand_aggregation",
            "hr_recommendation_routing",
            "structured_skills_taxonomy",
        ]
