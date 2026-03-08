"""
Project Lifecycle & Governance Agent

Purpose:
Manages project progression through lifecycle stages, enforces methodology-specific
governance gates and continuously monitors project health.

Specification: agents/delivery-management/lifecycle-governance-agent/README.md
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any

from lifecycle_actions import (
    adjust_methodology,
    evaluate_gate,
    generate_health_report,
    get_gate_history,
    get_health_dashboard,
    get_health_history,
    get_project_status,
    get_readiness_scores,
    initiate_project,
    monitor_health,
    override_gate,
    recommend_methodology,
    score_readiness,
    train_readiness_model,
    transition_phase,
)
from lifecycle_persistence import LifecyclePersistence
from lifecycle_utils import (
    bootstrap_configuration,
    load_methodology_map,
    update_methodology_config,
)
from monitoring import AzureMonitorClient
from notifications import NotificationService
from orchestration import DurableWorkflowEngine
from readiness_model import ReadinessScoringModel
from summarization import CognitiveSummarizer, GateSummarizer
from sync_clients import ExternalSyncService

from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from integrations.services.integration.ai_models import AIModelService


class ProjectLifecycleAgent(BaseAgent):
    """
    Project Lifecycle & Governance Agent - Manages project phases and health monitoring.

    Key Capabilities:
    - Project phase management and transitions
    - Methodology selection and adaptation
    - Phase gate definition and enforcement
    - Project health scoring and monitoring
    - State transitions and approvals
    - Governance compliance monitoring
    - Dashboard generation
    - Health metric ingestion from domain agents
    """

    def __init__(
        self,
        agent_id: str = "lifecycle-governance-agent",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.gate_criteria = config.get("gate_criteria", {}) if config else {}
        self.health_score_weights = (
            config.get(
                "health_score_weights",
                {"schedule": 0.25, "cost": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15},
            )
            if config
            else {"schedule": 0.25, "cost": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15}
        )
        self.monitoring_frequency = (
            config.get("monitoring_frequency", "hourly") if config else "hourly"
        )
        self.methodology_rules = config.get("methodology_rules", {}) if config else {}
        self.methodology_maps = config.get("methodology_maps", {}) if config else {}
        self.metric_agents = config.get("metric_agents", {}) if config else {}

        lifecycle_store_path = (
            Path(config.get("lifecycle_store_path", "data/project_lifecycle.json"))
            if config
            else Path("data/project_lifecycle.json")
        )
        health_store_path = (
            Path(config.get("health_store_path", "data/project_health_history.json"))
            if config
            else Path("data/project_health_history.json")
        )
        self.lifecycle_store = TenantStateStore(lifecycle_store_path)
        self.health_store = TenantStateStore(health_store_path)

        # Data stores (will be replaced with database connections)
        self.projects = {}  # type: ignore
        self.lifecycle_states = {}  # type: ignore
        self.health_scores = {}  # type: ignore
        self.gate_evaluations = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            from approval_workflow_agent import ApprovalWorkflowAgent

            approval_config = config.get("approval_agent_config", {}) if config else {}
            self.approval_agent = ApprovalWorkflowAgent(config=approval_config)

        self.persistence = LifecyclePersistence.from_config(config or {})
        self.readiness_model = config.get("readiness_model") if config else None
        if self.readiness_model is None:
            self.readiness_model = ReadinessScoringModel()
        self.ai_model_service = config.get("ai_model_service") if config else None
        if self.ai_model_service is None:
            self.ai_model_service = AIModelService()
        self.external_sync = config.get("external_sync") if config else None
        if self.external_sync is None:
            self.external_sync = ExternalSyncService(logger=self.logger)
        self.notification_service = config.get("notification_service") if config else None
        if self.notification_service is None:
            self.notification_service = NotificationService()
        self.summarizer = config.get("summarizer") if config else None
        if self.summarizer is None:
            cognitive_client = (config or {}).get("cognitive_client")
            llm_client = (config or {}).get("llm_client")
            if cognitive_client or llm_client:
                client = cognitive_client or llm_client
                self.summarizer = GateSummarizer(CognitiveSummarizer(client).summarize_payload)
            else:
                self.summarizer = GateSummarizer()
        self.knowledge_agent = config.get("knowledge_agent") if config else None
        self.orchestrator_sleep = (config or {}).get("orchestrator_sleep", asyncio.sleep)
        self.monitor_client = config.get("monitor_client") if config else None
        if self.monitor_client is None:
            self.monitor_client = AzureMonitorClient(logger=self.logger)
        self.workflow_engine = DurableWorkflowEngine(
            sleep=self.orchestrator_sleep, monitor=self.monitor_client
        )
        self.cleanup_tasks: list[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Project Lifecycle & Governance Agent...")

        await bootstrap_configuration(self)
        self._register_event_handlers()
        self.logger.info("Project Lifecycle & Governance Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "initiate_project",
            "transition_phase",
            "evaluate_gate",
            "monitor_health",
            "generate_health_report",
            "recommend_methodology",
            "adjust_methodology",
            "get_project_status",
            "get_health_dashboard",
            "override_gate",
            "get_gate_history",
            "get_readiness_scores",
            "get_health_history",
            "train_readiness_model",
            "score_readiness",
            "update_methodology_config",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "initiate_project":
            project_data = input_data.get("project_data", {})
            required_fields = ["project_id", "name", "methodology"]
            for field in required_fields:
                if field not in project_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        elif action in [
            "transition_phase",
            "evaluate_gate",
            "override_gate",
            "monitor_health",
            "generate_health_report",
            "get_project_status",
            "get_health_dashboard",
            "get_gate_history",
            "get_readiness_scores",
            "get_health_history",
            "score_readiness",
        ]:
            if "project_id" not in input_data:
                self.logger.warning("Missing project_id")
                return False

        if action == "update_methodology_config":
            if not input_data.get("methodology") and not input_data.get("gate_name"):
                self.logger.warning("Missing methodology or gate_name for update")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process project lifecycle and governance requests.

        Dispatches ``input_data["action"]`` to the matching action handler.
        See individual action modules for detailed parameter/return docs.
        """
        action = input_data.get("action", "initiate_project")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "initiate_project":
            return await initiate_project(
                self,
                input_data.get("project_data", {}),
                tenant_id=tenant_id,
            )

        elif action == "transition_phase":
            return await transition_phase(
                self,
                input_data.get("project_id"),  # type: ignore
                input_data.get("target_phase"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "evaluate_gate":
            return await evaluate_gate(
                self,
                input_data.get("project_id"),
                input_data.get("gate_name"),
                tenant_id=tenant_id,  # type: ignore
            )

        elif action == "monitor_health":
            return await monitor_health(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "generate_health_report":
            return await generate_health_report(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "recommend_methodology":
            return await recommend_methodology(self, input_data.get("project_data", {}))

        elif action == "adjust_methodology":
            return await adjust_methodology(
                self,
                input_data.get("project_id"),
                input_data.get("new_methodology"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "train_readiness_model":
            return await train_readiness_model(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "score_readiness":
            return await score_readiness(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "get_project_status":
            return await get_project_status(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "get_health_dashboard":
            return await get_health_dashboard(
                self, input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "override_gate":
            return await override_gate(
                self,
                input_data.get("project_id"),  # type: ignore
                input_data.get("gate_name"),  # type: ignore
                input_data.get("override_reason", ""),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=actor_id,
            )

        elif action == "get_gate_history":
            return await get_gate_history(
                self, input_data.get("project_id"), input_data.get("gate_name"), tenant_id=tenant_id
            )

        elif action == "get_readiness_scores":
            return await get_readiness_scores(
                self, input_data.get("project_id"), tenant_id=tenant_id
            )

        elif action == "get_health_history":
            return await get_health_history(self, input_data.get("project_id"), tenant_id=tenant_id)

        elif action == "update_methodology_config":
            return await update_methodology_config(
                self,
                tenant_id=tenant_id,
                methodology=input_data.get("methodology"),
                methodology_map=input_data.get("methodology_map"),
                gate_name=input_data.get("gate_name"),
                gate_criteria=input_data.get("gate_criteria"),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _register_event_handlers(self) -> None:
        if not self.event_bus or not hasattr(self.event_bus, "subscribe"):
            return
        try:
            self.event_bus.subscribe("risk.updated", self._handle_risk_event)
            self.event_bus.subscribe("resource.updated", self._handle_resource_event)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Event bus subscription failed", extra={"error": str(exc)})

    async def _handle_risk_event(self, payload: dict[str, Any]) -> None:
        severity = payload.get("severity")
        project_id = payload.get("project_id")
        if severity in {"high", "critical"} and project_id:
            self.logger.info(
                "Risk event triggered health monitor", extra={"project_id": project_id}
            )
            await monitor_health(self, project_id, tenant_id=payload.get("tenant_id", "unknown"))

    async def _handle_resource_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        if project_id:
            await monitor_health(self, project_id, tenant_id=payload.get("tenant_id", "unknown"))

    # ------------------------------------------------------------------
    # Backward-compatible delegates (keep tests working unchanged)
    # ------------------------------------------------------------------

    async def _initiate_project(
        self, project_data: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        return await initiate_project(self, project_data, tenant_id=tenant_id)

    async def _transition_phase(
        self,
        project_id: str,
        target_phase: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        return await transition_phase(
            self,
            project_id,
            target_phase,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

    async def _evaluate_gate(
        self, project_id: str, gate_name: str, *, tenant_id: str
    ) -> dict[str, Any]:
        return await evaluate_gate(self, project_id, gate_name, tenant_id=tenant_id)

    async def _monitor_health(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        return await monitor_health(self, project_id, tenant_id=tenant_id)

    async def _override_gate(
        self,
        project_id: str,
        gate_name: str,
        override_reason: str,
        *,
        tenant_id: str,
        correlation_id: str,
        requester: str,
    ) -> dict[str, Any]:
        return await override_gate(
            self,
            project_id,
            gate_name,
            override_reason,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            requester=requester,
        )

    async def _load_methodology_map(
        self, methodology: str, *, tenant_id: str = "default"
    ) -> dict[str, Any]:
        return await load_methodology_map(self, methodology, tenant_id=tenant_id)

    async def _train_readiness_model(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        return await train_readiness_model(self, project_id, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Project Lifecycle & Governance Agent...")
        await self.workflow_engine.shutdown()
        for task in list(self.cleanup_tasks):
            if not task.done():
                task.cancel()
        if self.cleanup_tasks:
            await asyncio.gather(*self.cleanup_tasks, return_exceptions=True)
        self.persistence.close()
        self.external_sync.close()
        flush = getattr(self.event_bus, "flush", None)
        if callable(flush):
            await flush()
        close = getattr(self.event_bus, "close", None)
        if callable(close):
            await close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "project_initiation",
            "phase_management",
            "phase_transition",
            "gate_enforcement",
            "health_monitoring",
            "methodology_recommendation",
            "methodology_adaptation",
            "compliance_monitoring",
            "dashboard_generation",
            "early_warning_detection",
            "governance_reporting",
        ]
