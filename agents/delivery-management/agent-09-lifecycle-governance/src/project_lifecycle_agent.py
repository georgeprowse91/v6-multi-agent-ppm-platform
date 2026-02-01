"""
Agent 9: Project Lifecycle & Governance Agent

Purpose:
Manages project progression through lifecycle stages, enforces methodology-specific
governance gates and continuously monitors project health.

Specification: agents/delivery-management/agent-09-lifecycle-governance/README.md
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from events import (
    ProjectHealthReportGeneratedEvent,
    ProjectHealthUpdatedEvent,
    ProjectTransitionedEvent,
)
from observability.tracing import get_trace_id

from agents.common.health_recommendations import generate_recommendations, identify_health_concerns
from agents.common.metrics_catalog import get_metric_value, normalize_metric_value
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from notifications import NotificationService
from orchestration import (
    DurableTask,
    DurableWorkflow,
    DurableWorkflowEngine,
    OrchestrationContext,
    RetryPolicy,
)
from monitoring import AzureMonitorClient
from persistence import LifecyclePersistence
from readiness_model import ReadinessScoringModel
from services.integration.ai_models import AIModelService
from summarization import CognitiveSummarizer, GateSummarizer
from sync_clients import ExternalSyncService


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
        agent_id: str = "project-lifecycle-governance",
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

        # Future work: Initialize Azure Durable Functions for stateful workflows
        # Future work: Connect to Azure Cosmos DB for lifecycle state storage
        # Future work: Initialize Azure Machine Learning for readiness scoring models
        # Future work: Connect to Planview/Clarity PPM for lifecycle metadata sync
        # Future work: Initialize Jira/Azure DevOps integration for Agile sprint data
        # Future work: Set up Azure Service Bus/Event Grid for lifecycle event subscriptions
        # Future work: Connect to Azure Cognitive Services for dashboard summarization
        # Future work: Initialize Azure Monitor for health metrics collection

        await self._bootstrap_configuration()
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
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "initiate_project":
            project_data = input_data.get("project_data", {})
            required_fields = ["project_id", "name", "methodology"]
            for field in required_fields:
                if field not in project_data:
                    self.logger.warning(f"Missing required field: {field}")
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
        """
        Process project lifecycle and governance requests.

        Args:
            input_data: {
                "action": "initiate_project" | "transition_phase" | "evaluate_gate" |
                          "monitor_health" | "generate_health_report" | "recommend_methodology" |
                          "adjust_methodology" | "get_project_status" | "get_health_dashboard" |
                          "override_gate" | "get_gate_history" | "get_readiness_scores" |
                          "get_health_history" | "train_readiness_model" | "score_readiness" |
                          "update_methodology_config",
                "project_data": Project initialization data,
                "project_id": ID of existing project,
                "target_phase": Target phase for transition,
                "override_reason": Reason for gate override,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - initiate_project: Project ID, initial state, methodology map
            - transition_phase: Transition status, gate results, next steps
            - evaluate_gate: Gate criteria status, readiness score, gaps
            - monitor_health: Composite health score, metrics, alerts
            - generate_health_report: Standardized health report output
            - recommend_methodology: Recommended methodology with rationale
            - adjust_methodology: Updated methodology configuration
            - get_project_status: Current phase, health, pending gates
            - get_health_dashboard: Complete dashboard data
            - override_gate: Override confirmation, audit record
        """
        action = input_data.get("action", "initiate_project")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "initiate_project":
            return await self._initiate_project(
                input_data.get("project_data", {}),
                tenant_id=tenant_id,
            )

        elif action == "transition_phase":
            return await self._transition_phase(
                input_data.get("project_id"),  # type: ignore
                input_data.get("target_phase"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "evaluate_gate":
            return await self._evaluate_gate(
                input_data.get("project_id"), input_data.get("gate_name"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "monitor_health":
            return await self._monitor_health(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "generate_health_report":
            return await self._generate_health_report(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "recommend_methodology":
            return await self._recommend_methodology(input_data.get("project_data", {}))

        elif action == "adjust_methodology":
            return await self._adjust_methodology(
                input_data.get("project_id"),
                input_data.get("new_methodology"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "train_readiness_model":
            return await self._train_readiness_model(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "score_readiness":
            return await self._score_readiness(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "get_project_status":
            return await self._get_project_status(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "get_health_dashboard":
            return await self._get_health_dashboard(
                input_data.get("project_id"), tenant_id=tenant_id  # type: ignore
            )

        elif action == "override_gate":
            return await self._override_gate(
                input_data.get("project_id"),  # type: ignore
                input_data.get("gate_name"),  # type: ignore
                input_data.get("override_reason", ""),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=actor_id,
            )

        elif action == "get_gate_history":
            return await self._get_gate_history(
                input_data.get("project_id"), input_data.get("gate_name"), tenant_id=tenant_id
            )

        elif action == "get_readiness_scores":
            return await self._get_readiness_scores(
                input_data.get("project_id"), tenant_id=tenant_id
            )

        elif action == "get_health_history":
            return await self._get_health_history(
                input_data.get("project_id"), tenant_id=tenant_id
            )

        elif action == "update_methodology_config":
            return await self._update_methodology_config(
                tenant_id=tenant_id,
                methodology=input_data.get("methodology"),
                methodology_map=input_data.get("methodology_map"),
                gate_name=input_data.get("gate_name"),
                gate_criteria=input_data.get("gate_criteria"),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _initiate_project(
        self, project_data: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Initiate a new project and set initial lifecycle state.

        Returns project record and methodology map.
        """
        self.logger.info("Initiating project")

        project_id = project_data.get("project_id")
        workflow = DurableWorkflow(
            name="project_initiation",
            tasks=[
                DurableTask(
                    name="create_records",
                    action=self._create_project_record,
                    compensation=self._rollback_project_record,
                ),
                DurableTask(name="persist_methodology", action=self._persist_methodology_decision),
                DurableTask(
                    name="publish_project_initiated",
                    action=self._publish_project_initiated,
                    retry_policy=RetryPolicy(max_attempts=3),
                ),
                DurableTask(
                    name="sync_project_state",
                    action=self._sync_project_state,
                    retry_policy=RetryPolicy(max_attempts=3),
                ),
                DurableTask(name="notify_project_initiated", action=self._notify_project_initiated),
            ],
            sleep=self.orchestrator_sleep,
        )

        context = OrchestrationContext(
            workflow_id=f"initiate-{project_id}",
            tenant_id=tenant_id,
            project_id=project_id,
            correlation_id=str(uuid.uuid4()),
            payload={"project_data": project_data},
        )
        context = await self.workflow_engine.run(workflow, context)
        init_payload = context.results["create_records"]

        self.logger.info(f"Initiated project: {project_id}")

        return {
            "project_id": project_id,
            "current_phase": init_payload["methodology_map"]["initial_phase"],
            "methodology": init_payload["methodology"],
            "methodology_map": init_payload["methodology_map"],
            "next_steps": "Generate project charter and complete initiation activities",
        }

    async def _transition_phase(
        self,
        project_id: str,
        target_phase: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Transition project to a new phase.

        Returns transition status and gate evaluation results.
        """
        self.logger.info(f"Attempting phase transition for project: {project_id}")

        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        current_phase = lifecycle_state.get("current_phase")
        methodology_map = lifecycle_state.get("methodology_map", {})

        # Validate transition is allowed
        allowed_transitions = (
            methodology_map.get("phases", {}).get(current_phase, {}).get("next_phases", [])
        )
        if target_phase not in allowed_transitions:
            return {
                "success": False,
                "reason": f"Invalid transition from {current_phase} to {target_phase}",
                "allowed_transitions": allowed_transitions,
            }

        # Get gate name for this transition
        gate_name = await self._get_gate_name(current_phase, target_phase)

        # Evaluate gate criteria
        gate_evaluation = await self._evaluate_gate(project_id, gate_name, tenant_id=tenant_id)

        # Check if gate criteria are met
        if not gate_evaluation.get("criteria_met"):
            return {
                "success": False,
                "reason": "Gate criteria not met",
                "gate_evaluation": gate_evaluation,
                "missing_criteria": gate_evaluation.get("missing_criteria", []),
                "next_steps": "Complete missing activities or request override",
            }

        # Perform transition
        workflow = DurableWorkflow(
            name="phase_transition",
            tasks=[
                DurableTask(
                    name="apply_transition",
                    action=self._apply_phase_transition,
                    compensation=self._rollback_phase_transition,
                ),
                DurableTask(name="persist_lifecycle", action=self._persist_lifecycle_state),
                DurableTask(name="publish_phase_change", action=self._publish_phase_changed),
                DurableTask(
                    name="sync_project_state",
                    action=self._sync_project_state,
                    retry_policy=RetryPolicy(max_attempts=3),
                ),
            ],
            sleep=self.orchestrator_sleep,
        )
        context = OrchestrationContext(
            workflow_id=f"phase-{project_id}-{target_phase}",
            tenant_id=tenant_id,
            project_id=project_id,
            correlation_id=correlation_id,
            payload={
                "target_phase": target_phase,
                "gate_name": gate_name,
                "actor_id": actor_id,
            },
            metadata={"gate_evaluation": gate_evaluation},
        )
        context = await self.workflow_engine.run(workflow, context)
        transition_record = context.results["apply_transition"]

        self.logger.info(
            f"Transitioned project {project_id} from {current_phase} to {target_phase}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "previous_phase": current_phase,
            "current_phase": target_phase,
            "gate_evaluation": gate_evaluation,
            "transition_record": transition_record,
        }

    async def _evaluate_gate(
        self, project_id: str, gate_name: str, *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Evaluate phase gate criteria.

        Returns gate evaluation results and readiness score.
        """
        self.logger.info(f"Evaluating gate '{gate_name}' for project: {project_id}")

        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        workflow = DurableWorkflow(
            name="gate_evaluation",
            tasks=[
                DurableTask(name="evaluate_criteria", action=self._evaluate_gate_criteria),
                DurableTask(name="score_readiness", action=self._score_gate_readiness),
                DurableTask(name="persist_gate_evaluation", action=self._persist_gate_evaluation),
                DurableTask(name="publish_gate_event", action=self._publish_gate_event),
                DurableTask(name="sync_gate_event", action=self._sync_gate_decision),
                DurableTask(name="summarize_gate", action=self._summarize_gate),
            ],
            sleep=self.orchestrator_sleep,
        )
        context = OrchestrationContext(
            workflow_id=f"gate-{project_id}-{gate_name}",
            tenant_id=tenant_id,
            project_id=project_id,
            correlation_id=str(uuid.uuid4()),
            payload={"gate_name": gate_name},
        )
        context = await self.workflow_engine.run(workflow, context)
        evaluation = context.results["evaluate_criteria"]

        if project_id not in self.gate_evaluations:
            self.gate_evaluations[project_id] = []
        self.gate_evaluations[project_id].append(evaluation)

        return evaluation

    async def _monitor_health(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Monitor project health continuously.

        Returns composite health score and metrics from domain agents.
        """
        self.logger.info(f"Monitoring health for project: {project_id}")

        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        metric_context = {
            "tenant_id": tenant_id,
            "schedule_id": project.get("schedule_id"),
            "resource_filters": project.get("resource_filters", {}),
        }
        raw_schedule, raw_cost, raw_risk, raw_quality, raw_resource = await asyncio.gather(
            get_metric_value(
                "schedule_variance",
                project_id,
                tenant_id=tenant_id,
                context=metric_context,
                agent_clients=self.metric_agents,
                fallback=project,
            ),
            get_metric_value(
                "cost_variance",
                project_id,
                tenant_id=tenant_id,
                context=metric_context,
                agent_clients=self.metric_agents,
                fallback=project,
            ),
            get_metric_value(
                "risk_score",
                project_id,
                tenant_id=tenant_id,
                context=metric_context,
                agent_clients=self.metric_agents,
                fallback=project,
            ),
            get_metric_value(
                "quality_score",
                project_id,
                tenant_id=tenant_id,
                context=metric_context,
                agent_clients=self.metric_agents,
                fallback=project,
            ),
            get_metric_value(
                "resource_utilization",
                project_id,
                tenant_id=tenant_id,
                context=metric_context,
                agent_clients=self.metric_agents,
                fallback=project,
            ),
        )

        raw_metrics = {
            "schedule_variance": raw_schedule,
            "cost_variance": raw_cost,
            "risk_score": raw_risk,
            "quality_score": raw_quality,
            "resource_utilization": raw_resource,
        }

        schedule_health = normalize_metric_value("schedule_variance", raw_schedule)
        cost_health = normalize_metric_value("cost_variance", raw_cost)
        risk_health = normalize_metric_value("risk_score", raw_risk)
        quality_health = normalize_metric_value("quality_score", raw_quality)
        resource_health = normalize_metric_value("resource_utilization", raw_resource)

        # Calculate composite health score
        composite_score = (
            schedule_health * self.health_score_weights["schedule"]
            + cost_health * self.health_score_weights["cost"]
            + risk_health * self.health_score_weights["risk"]
            + quality_health * self.health_score_weights["quality"]
            + resource_health * self.health_score_weights["resource"]
        )

        # Determine health status
        health_status = await self._determine_health_status(composite_score)

        # Identify concerns and anomalies
        concerns = identify_health_concerns(
            {
                "schedule": schedule_health,
                "cost": cost_health,
                "risk": risk_health,
                "quality": quality_health,
                "resource": resource_health,
            }
        )

        # Detect early warning signals
        warnings = await self._detect_warnings(project_id, raw_metrics)

        # Generate recommendations
        recommendations = generate_recommendations(concerns)

        health_data = {
            "project_id": project_id,
            "composite_score": composite_score,
            "health_status": health_status,
            "metrics": {
                "schedule": {
                    "score": schedule_health,
                    "status": await self._get_metric_status(schedule_health),
                    "raw": raw_schedule,
                },
                "cost": {
                    "score": cost_health,
                    "status": await self._get_metric_status(cost_health),
                    "raw": raw_cost,
                },
                "risk": {
                    "score": risk_health,
                    "status": await self._get_metric_status(risk_health),
                    "raw": raw_risk,
                },
                "quality": {
                    "score": quality_health,
                    "status": await self._get_metric_status(quality_health),
                    "raw": raw_quality,
                },
                "resource": {
                    "score": resource_health,
                    "status": await self._get_metric_status(resource_health),
                    "raw": raw_resource,
                },
            },
            "raw_metrics": raw_metrics,
            "concerns": concerns,
            "warnings": warnings,
            "recommendations": recommendations,
            "monitored_at": datetime.utcnow().isoformat(),
        }

        workflow = DurableWorkflow(
            name="health_monitoring",
            tasks=[
                DurableTask(name="persist_health", action=self._persist_health_metrics),
                DurableTask(name="publish_health", action=self._publish_health_event),
                DurableTask(name="notify_health", action=self._notify_health_if_needed),
            ],
            sleep=self.orchestrator_sleep,
        )
        context = OrchestrationContext(
            workflow_id=f"health-{project_id}",
            tenant_id=tenant_id,
            project_id=project_id,
            correlation_id=str(uuid.uuid4()),
            payload={"health_data": health_data},
        )
        await self.workflow_engine.run(workflow, context)

        return health_data

    async def _generate_health_report(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Generate a standardized health report and publish it as an event.
        """
        health_data = await self._monitor_health(project_id, tenant_id=tenant_id)
        report_id = f"health-report-{project_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        summary = (
            f"Project health is {health_data.get('health_status')} with "
            f"composite score {health_data.get('composite_score', 0):.2f}."
        )
        report = {
            "report_id": report_id,
            "project_id": project_id,
            "summary": summary,
            "health_status": health_data.get("health_status"),
            "composite_score": health_data.get("composite_score"),
            "metrics": health_data.get("metrics", {}),
            "concerns": health_data.get("concerns", []),
            "warnings": health_data.get("warnings", []),
            "recommendations": health_data.get("recommendations", []),
            "generated_at": datetime.utcnow().isoformat(),
        }
        await self._publish_health_report_generated(report, tenant_id=tenant_id)
        return report

    async def _recommend_methodology(self, project_data: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend appropriate methodology based on project characteristics.

        Returns recommended methodology with rationale.
        """
        self.logger.info("Recommending methodology")

        # Extract project characteristics
        project_data.get("size", "medium")
        complexity = project_data.get("complexity", "medium")
        requirement_volatility = project_data.get("requirement_volatility", "medium")
        stakeholder_engagement = project_data.get("stakeholder_engagement", "medium")
        regulatory_requirements = project_data.get("regulatory_requirements", False)

        # Future work: Use ML model for methodology recommendation
        # Simplified rule-based logic
        if requirement_volatility == "high" and stakeholder_engagement == "high":
            methodology = "agile"
            rationale = (
                "High requirement volatility and stakeholder engagement favor Agile approach"
            )
        elif regulatory_requirements or complexity == "high":
            methodology = "waterfall"
            rationale = "Regulatory requirements and high complexity favor Waterfall approach"
        else:
            methodology = "hybrid"
            rationale = "Mixed characteristics suggest Hybrid approach for optimal flexibility"

        return {
            "methodology": methodology,
            "rationale": rationale,
            "confidence": 0.85,
            "alternatives": await self._get_alternative_methodologies(methodology),
            "decided_at": datetime.utcnow().isoformat(),
        }

    async def _adjust_methodology(
        self, project_id: str, new_methodology: str, *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Adjust project methodology.

        Returns updated methodology configuration.
        """
        self.logger.info(f"Adjusting methodology for project: {project_id}")

        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        old_methodology = self.projects[project_id].get("methodology")

        # Load new methodology map
        new_methodology_map = await self._load_methodology_map(new_methodology, tenant_id=tenant_id)

        # Map current phase to equivalent in new methodology
        current_phase = lifecycle_state.get("current_phase")
        new_phase = await self._map_phase_to_methodology(
            current_phase, old_methodology, new_methodology
        )

        # Update project and lifecycle state
        self.projects[project_id]["methodology"] = new_methodology
        lifecycle_state["methodology_map"] = new_methodology_map
        lifecycle_state["current_phase"] = new_phase

        update_payload = {
            "project_id": project_id,
            "old_methodology": old_methodology,
            "new_methodology": new_methodology,
            "current_phase": new_phase,
            "methodology_map": new_methodology_map,
            "adjusted_at": datetime.utcnow().isoformat(),
        }
        workflow = DurableWorkflow(
            name="methodology_adjustment",
            tasks=[
                DurableTask(name="persist_methodology", action=self._persist_methodology_decision),
                DurableTask(name="publish_methodology", action=self._publish_methodology_adjusted),
                DurableTask(name="sync_methodology", action=self._sync_project_state),
            ],
            sleep=self.orchestrator_sleep,
        )
        context = OrchestrationContext(
            workflow_id=f"methodology-{project_id}",
            tenant_id=tenant_id,
            project_id=project_id,
            correlation_id=str(uuid.uuid4()),
            payload={"project_data": update_payload},
        )
        await self.workflow_engine.run(workflow, context)

        return update_payload

    async def _get_project_status(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Get current project status."""
        project = self.projects.get(project_id)
        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)

        if not project or not lifecycle_state:
            raise ValueError(f"Project not found: {project_id}")

        # Get health data
        health_data = self.health_scores.get(project_id, {})

        # Get pending gates
        pending_gates = await self._get_pending_gates(project_id)

        return {
            "project_id": project_id,
            "name": project.get("name"),
            "current_phase": project.get("current_phase"),
            "methodology": project.get("methodology"),
            "status": project.get("status"),
            "health_status": health_data.get("health_status", "Unknown"),
            "composite_score": health_data.get("composite_score", 0),
            "pending_gates": pending_gates,
            "phase_start_date": lifecycle_state.get("phase_start_date"),
            "transitions_count": len(lifecycle_state.get("transitions", [])),
        }

    async def _get_health_dashboard(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Generate comprehensive health dashboard."""
        health_data = await self._monitor_health(project_id, tenant_id=tenant_id)
        project = self.projects.get(project_id, {})
        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)
        project_status = {
            "project_id": project_id,
            "name": project.get("name"),
            "current_phase": project.get("current_phase"),
            "methodology": project.get("methodology"),
            "status": project.get("status"),
            "health_status": health_data.get("health_status", "Unknown"),
            "composite_score": health_data.get("composite_score", 0),
            "phase_start_date": (
                lifecycle_state.get("phase_start_date") if lifecycle_state else None
            ),
            "transitions_count": (
                len(lifecycle_state.get("transitions", [])) if lifecycle_state else 0
            ),
        }

        # Generate trend data
        trends = await self._generate_health_trends(project_id, tenant_id=tenant_id)

        # Generate alerts
        alerts = await self._generate_alerts(health_data)

        return {
            "project_id": project_id,
            "project_status": project_status,
            "health_data": health_data,
            "trends": trends,
            "alerts": alerts,
            "generated_at": datetime.utcnow().isoformat(),
        }

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
        """
        Override a gate that doesn't meet criteria.

        Returns override confirmation and audit record.
        """
        self.logger.info(f"Overriding gate '{gate_name}' for project: {project_id}")

        # Evaluate gate first to document what's being overridden
        gate_evaluation = await self._evaluate_gate(project_id, gate_name, tenant_id=tenant_id)

        approval_response = await self._request_override_approval(
            project_id=project_id,
            gate_name=gate_name,
            override_reason=override_reason,
            gate_evaluation=gate_evaluation,
            requester=requester,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        # Create override record
        override_record = {
            "project_id": project_id,
            "gate_name": gate_name,
            "gate_evaluation": gate_evaluation,
            "override_reason": override_reason,
            "overridden_by": requester,
            "overridden_at": datetime.utcnow().isoformat(),
            "approval_id": approval_response.get("approval_id"),
            "approval_status": approval_response.get("status"),
        }

        # Mark gate as passed despite not meeting criteria
        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)
        if lifecycle_state and approval_response.get("status") == "approved":
            lifecycle_state["gates_passed"].append(f"{gate_name} (OVERRIDDEN)")
            self.lifecycle_store.upsert(tenant_id, project_id, lifecycle_state)

        await self.event_bus.publish("gate.overridden", override_record)
        await self.external_sync.sync_gate_decision(
            project_id, gate_name, {"override": True, **override_record}
        )
        await self.notification_service.notify_gate_decision(
            {"project_id": project_id, "gate_name": gate_name, "event": "gate.overridden"}
        )

        self.logger.warning(f"Gate override recorded for {project_id}: {gate_name}")

        return {
            "success": approval_response.get("status") == "approved",
            "override_record": override_record,
            "warning": "Gate criteria were not met. Override has been recorded for audit.",
            "approval": approval_response,
        }

    # Helper methods

    async def _load_methodology_map(self, methodology: str, *, tenant_id: str) -> dict[str, Any]:
        """Load methodology map with phases and gates."""
        stored_map = self.persistence.load_methodology_map(tenant_id, methodology)
        if stored_map:
            return stored_map
        if methodology in self.methodology_maps:
            return self.methodology_maps[methodology]

        if methodology == "agile":
            return {
                "initial_phase": "Sprint 0",
                "phases": {
                    "Sprint 0": {
                        "name": "Sprint 0",
                        "next_phases": ["Sprint 1"],
                        "gates": ["sprint_planning_complete"],
                    },
                    "Sprint 1": {
                        "name": "Sprint 1",
                        "next_phases": ["Sprint 2", "Release"],
                        "gates": ["sprint_review", "sprint_retrospective"],
                    },
                    "Release": {
                        "name": "Release",
                        "next_phases": [],
                        "gates": ["release_criteria_met"],
                    },
                },
            }
        if methodology == "waterfall":
            return {
                "initial_phase": "Initiate",
                "phases": {
                    "Initiate": {
                        "name": "Initiate",
                        "next_phases": ["Plan"],
                        "gates": ["charter_approved"],
                    },
                    "Plan": {
                        "name": "Plan",
                        "next_phases": ["Execute"],
                        "gates": ["baseline_approved"],
                    },
                    "Execute": {
                        "name": "Execute",
                        "next_phases": ["Monitor", "Close"],
                        "gates": ["deliverables_complete"],
                    },
                    "Monitor": {
                        "name": "Monitor",
                        "next_phases": ["Close"],
                        "gates": ["acceptance_complete"],
                    },
                    "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
                },
            }
        return {
            "initial_phase": "Initiate",
            "phases": {
                "Initiate": {
                    "name": "Initiate",
                    "next_phases": ["Plan"],
                    "gates": ["charter_approved"],
                },
                "Plan": {
                    "name": "Plan",
                    "next_phases": ["Iterate"],
                    "gates": ["baseline_approved"],
                },
                "Iterate": {
                    "name": "Iterate",
                    "next_phases": ["Release", "Iterate"],
                    "gates": ["iteration_complete"],
                },
                "Release": {
                    "name": "Release",
                    "next_phases": ["Close"],
                    "gates": ["release_approved"],
                },
                "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
            },
        }

    async def _get_gate_name(self, from_phase: str, to_phase: str) -> str:
        """Get gate name for phase transition."""
        return f"{from_phase}_to_{to_phase}_gate"

    async def _get_gate_criteria(self, gate_name: str, *, tenant_id: str) -> list[str]:
        """Get criteria for a specific gate."""
        stored = self.persistence.load_gate_criteria(tenant_id, gate_name)
        if stored:
            return stored
        if gate_name in self.gate_criteria:
            return self.gate_criteria[gate_name]
        if "charter" in gate_name.lower():
            return ["charter_document_complete", "charter_approved", "sponsor_assigned"]
        if "baseline" in gate_name.lower():
            return ["scope_baseline_approved", "schedule_baseline_approved", "budget_approved"]
        return ["deliverables_complete", "quality_criteria_met"]

    async def _check_criterion(self, project_id: str, criterion: str) -> bool:
        """Check if a specific criterion is met."""
        project = self.projects.get(project_id, {})
        artifacts = project.get("artifacts", {})
        approvals = project.get("approvals", {})
        metrics = project.get("metrics", {})

        criteria_map = {
            "charter_document_complete": artifacts.get("charter", {}).get("complete", False),
            "charter_approved": approvals.get("charter", False),
            "sponsor_assigned": bool(project.get("sponsor")),
            "scope_baseline_approved": approvals.get("scope_baseline", False),
            "schedule_baseline_approved": approvals.get("schedule_baseline", False),
            "budget_approved": approvals.get("budget", False),
            "deliverables_complete": artifacts.get("deliverables", {}).get("complete", False),
            "quality_criteria_met": metrics.get("quality_score", 0) >= 0.85,
        }

        return bool(criteria_map.get(criterion, False))

    async def _get_criterion_description(self, criterion: str) -> str:
        """Get description for a criterion."""
        descriptions = {
            "charter_document_complete": "Project charter document is complete with all sections filled",
            "charter_approved": "Project charter has been approved by sponsor",
            "sponsor_assigned": "Project sponsor has been assigned",
            "scope_baseline_approved": "Scope baseline has been approved",
            "schedule_baseline_approved": "Schedule baseline has been approved",
            "budget_approved": "Project budget has been approved",
            "deliverables_complete": "All phase deliverables are complete",
            "quality_criteria_met": "Quality criteria have been met",
        }
        return descriptions.get(criterion, criterion)

    async def _determine_health_status(self, composite_score: float) -> str:
        """Determine health status from composite score."""
        if composite_score >= 0.85:
            return "Healthy"
        elif composite_score >= 0.70:
            return "At Risk"
        else:
            return "Critical"

    async def _get_metric_status(self, score: float) -> str:
        """Get status for individual metric."""
        if score >= 0.85:
            return "green"
        elif score >= 0.70:
            return "yellow"
        else:
            return "red"

    async def _detect_warnings(
        self, project_id: str, raw_metrics: dict[str, float | None]
    ) -> list[dict[str, Any]]:
        """Detect early warning signals."""
        project = self.projects.get(project_id, {})
        warnings = []

        schedule_variance = raw_metrics.get("schedule_variance")
        if schedule_variance is not None and schedule_variance < -0.1:
            warnings.append(
                {
                    "type": "schedule_slip",
                    "message": "Schedule slipping beyond 10% threshold",
                }
            )

        cost_variance = raw_metrics.get("cost_variance")
        if cost_variance is not None and cost_variance > 0.1:
            warnings.append(
                {
                    "type": "cost_overrun",
                    "message": "Cost variance exceeds 10% threshold",
                }
            )

        risk = project.get("risk", {})
        if risk.get("open_risks", 0) >= 5:
            warnings.append(
                {
                    "type": "risk_backlog",
                    "message": "Risk backlog exceeds 5 open items",
                }
            )

        quality = project.get("quality", {})
        if quality.get("defects", 0) > 10:
            warnings.append(
                {
                    "type": "quality_issues",
                    "message": "High defect rate detected",
                }
            )

        resource_utilization = raw_metrics.get("resource_utilization")
        if resource_utilization is not None and resource_utilization > 0.95:
            warnings.append(
                {
                    "type": "resource_overload",
                    "message": "Resource utilization exceeds 95%",
                }
            )

        return warnings

    async def _get_alternative_methodologies(self, primary: str) -> list[str]:
        """Get alternative methodologies."""
        all_methodologies = ["agile", "waterfall", "hybrid"]
        return [m for m in all_methodologies if m != primary]

    async def _map_phase_to_methodology(
        self, current_phase: str, old_methodology: str, new_methodology: str
    ) -> str:
        """Map current phase to equivalent in new methodology."""
        # Future work: Implement intelligent phase mapping
        # Simplified mapping
        new_map = await self._load_methodology_map(new_methodology, tenant_id=tenant_id)
        return new_map["initial_phase"]  # type: ignore

    async def _get_pending_gates(self, project_id: str) -> list[str]:
        """Get list of pending gates."""
        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            return []

        current_phase = lifecycle_state.get("current_phase")
        methodology_map = lifecycle_state.get("methodology_map", {})

        phase_info = methodology_map.get("phases", {}).get(current_phase, {})
        return phase_info.get("gates", [])  # type: ignore

    async def _generate_health_trends(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Generate health trend data from historical health scores."""
        history = [
            record
            for record in self.health_store.list(tenant_id)
            if record.get("project_id") == project_id
        ]
        history = sorted(history, key=lambda record: record.get("monitored_at", ""))

        def _trend(values: list[float]) -> str:
            if len(values) < 2:
                return "stable"
            if values[-1] > values[0]:
                return "improving"
            if values[-1] < values[0]:
                return "declining"
            return "stable"

        schedule_values = [
            record.get("metrics", {}).get("schedule", {}).get("score", 0) for record in history
        ]
        cost_values = [
            record.get("metrics", {}).get("cost", {}).get("score", 0) for record in history
        ]
        risk_values = [
            record.get("metrics", {}).get("risk", {}).get("score", 0) for record in history
        ]
        quality_values = [
            record.get("metrics", {}).get("quality", {}).get("score", 0) for record in history
        ]
        resource_values = [
            record.get("metrics", {}).get("resource", {}).get("score", 0) for record in history
        ]

        return {
            "schedule_trend": _trend(schedule_values),
            "cost_trend": _trend(cost_values),
            "risk_trend": _trend(risk_values),
            "quality_trend": _trend(quality_values),
            "resource_trend": _trend(resource_values),
            "history": history[-10:],
        }

    async def _generate_alerts(self, health_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate alerts based on health data."""
        alerts = []
        if health_data.get("health_status") == "Critical":
            alerts.append(
                {
                    "severity": "high",
                    "message": "Project health is critical. Immediate action required.",
                    "recommended_action": "Escalate to PMO and steering committee",
                }
            )
        return alerts

    async def _bootstrap_configuration(self) -> None:
        for methodology, methodology_map in self.methodology_maps.items():
            if not self.persistence.load_methodology_map("default", methodology):
                self.persistence.store_methodology_map("default", methodology, methodology_map)
        for gate_name, criteria in self.gate_criteria.items():
            if not self.persistence.load_gate_criteria("default", gate_name):
                self.persistence.store_gate_criteria("default", gate_name, criteria)

    async def _update_methodology_config(
        self,
        *,
        tenant_id: str,
        methodology: str | None,
        methodology_map: dict[str, Any] | None,
        gate_name: str | None,
        gate_criteria: list[str] | None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if methodology and methodology_map:
            record = self.persistence.store_methodology_map(tenant_id, methodology, methodology_map)
            updates["methodology_map"] = record
        if gate_name and gate_criteria:
            record = self.persistence.store_gate_criteria(tenant_id, gate_name, gate_criteria)
            updates["gate_criteria"] = record
        return {"status": "updated", "updates": updates}

    async def _train_readiness_model(
        self, project_id: str, *, tenant_id: str
    ) -> dict[str, Any]:
        history = self.persistence.list_gate_outcomes(tenant_id, project_id)
        if not history:
            return {"status": "skipped", "reason": "no_gate_history"}
        samples = []
        ai_samples = []
        for record in history:
            payload = record["payload"]
            criteria_status = payload.get("criteria_status", [])
            health_snapshot = payload.get("health_snapshot", {})
            features = self.readiness_model.build_features(criteria_status, health_snapshot)
            label = 1.0 if payload.get("criteria_met") else 0.0
            samples.append({"features": features, "label": label})
            readiness_features = payload.get("readiness_features") or self.readiness_model.build_readiness_features(
                self.projects.get(project_id), health_snapshot, criteria_status
            )
            ai_samples.append({"features": readiness_features, "label": label})
        self.readiness_model.fit(samples)
        ai_result = self.readiness_model.train_with_ai_service(self.ai_model_service, ai_samples)
        return {
            "status": "trained",
            "samples": len(samples),
            "ai_model": ai_result,
        }

    async def _score_readiness(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        lifecycle_state = await self._get_lifecycle_state(tenant_id, project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")
        pending_gates = await self._get_pending_gates(project_id)
        gate_name = pending_gates[0] if pending_gates else "current_gate"
        evaluation = await self._evaluate_gate(project_id, gate_name, tenant_id=tenant_id)
        return {
            "project_id": project_id,
            "gate_name": gate_name,
            "readiness_score": evaluation.get("readiness_score"),
            "criteria_met": evaluation.get("criteria_met"),
            "readiness_model": evaluation.get("readiness_model"),
        }

    async def _get_gate_history(
        self, project_id: str, gate_name: str | None, *, tenant_id: str
    ) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "gate_name": gate_name,
            "history": self.persistence.list_gate_outcomes(tenant_id, project_id, gate_name),
        }

    async def _get_readiness_scores(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "readiness_scores": self.persistence.list_readiness_scores(tenant_id, project_id),
        }

    async def _get_health_history(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "health_history": self.persistence.list_health_metrics(tenant_id, project_id),
        }

    def _register_event_handlers(self) -> None:
        try:
            self.event_bus.subscribe("risk.updated", self._handle_risk_event)
            self.event_bus.subscribe("resource.updated", self._handle_resource_event)
        except Exception as exc:
            self.logger.warning("Event bus subscription failed", extra={"error": str(exc)})

    async def _handle_risk_event(self, payload: dict[str, Any]) -> None:
        severity = payload.get("severity")
        project_id = payload.get("project_id")
        if severity in {"high", "critical"} and project_id:
            self.logger.info("Risk event triggered health monitor", extra={"project_id": project_id})
            await self._monitor_health(project_id, tenant_id=payload.get("tenant_id", "unknown"))

    async def _handle_resource_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        if project_id:
            await self._monitor_health(project_id, tenant_id=payload.get("tenant_id", "unknown"))

    async def _create_project_record(self, context: OrchestrationContext) -> dict[str, Any]:
        project_data = context.payload.get("project_data", {})
        project_id = project_data.get("project_id")
        name = project_data.get("name")
        methodology = project_data.get("methodology", "hybrid")

        recommended_methodology = await self._recommend_methodology(project_data)
        if methodology != recommended_methodology.get("methodology"):
            self.logger.warning(
                "Provided methodology differs from recommended",
                extra={
                    "provided": methodology,
                    "recommended": recommended_methodology.get("methodology"),
                },
            )

        methodology_map = await self._load_methodology_map(methodology, tenant_id=context.tenant_id)
        project = {
            "project_id": project_id,
            "name": name,
            "methodology": methodology,
            "current_phase": methodology_map["initial_phase"],
            "phase_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "status": "Active",
        }
        lifecycle_state = {
            "project_id": project_id,
            "current_phase": methodology_map["initial_phase"],
            "phase_start_date": datetime.utcnow().isoformat(),
            "methodology_map": methodology_map,
            "transitions": [],
            "gates_passed": [],
            "gates_pending": [],
        }

        self.projects[project_id] = project
        self.lifecycle_states[project_id] = lifecycle_state
        self.lifecycle_store.upsert(context.tenant_id, project_id, lifecycle_state)
        self.persistence.store_lifecycle_state(context.tenant_id, project_id, lifecycle_state)

        context.results["methodology_decision"] = recommended_methodology
        return {
            "project_id": project_id,
            "project": project,
            "lifecycle_state": lifecycle_state,
            "methodology": methodology,
            "methodology_map": methodology_map,
        }

    async def _rollback_project_record(
        self, context: OrchestrationContext, _exc: Exception | None
    ) -> None:
        project_id = context.project_id
        self.projects.pop(project_id, None)
        self.lifecycle_states.pop(project_id, None)

    async def _persist_methodology_decision(self, context: OrchestrationContext) -> dict[str, Any]:
        decision = context.results.get("methodology_decision") or context.payload.get(
            "project_data", {}
        )
        return self.persistence.store_methodology_decision(
            context.tenant_id, context.project_id, decision
        )

    async def _publish_project_initiated(self, context: OrchestrationContext) -> dict[str, Any]:
        payload = {
            "project_id": context.project_id,
            "initiated_at": datetime.utcnow().isoformat(),
            "methodology": context.results.get("create_records", {}).get("methodology"),
        }
        await self.event_bus.publish("project.initiated", payload)
        return payload

    async def _sync_project_state(self, context: OrchestrationContext) -> dict[str, Any]:
        state = (
            context.results.get("create_records", {}).get("lifecycle_state")
            or context.payload.get("project_data")
            or context.payload
        )
        results = await self.external_sync.sync_project_state(context.project_id, state)
        return {"sync_results": [result.__dict__ for result in results]}

    async def _notify_project_initiated(self, context: OrchestrationContext) -> dict[str, Any]:
        payload = {
            "project_id": context.project_id,
            "event": "project.initiated",
            "methodology": context.results.get("create_records", {}).get("methodology"),
        }
        return await self.notification_service.notify_project_initiated(payload)

    async def _apply_phase_transition(self, context: OrchestrationContext) -> dict[str, Any]:
        project_id = context.project_id
        target_phase = context.payload.get("target_phase")
        gate_name = context.payload.get("gate_name")
        actor_id = context.payload.get("actor_id")
        lifecycle_state = await self._get_lifecycle_state(context.tenant_id, project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")
        current_phase = lifecycle_state.get("current_phase")
        transition_record = {
            "from_phase": current_phase,
            "to_phase": target_phase,
            "gate_name": gate_name,
            "transitioned_at": datetime.utcnow().isoformat(),
            "transitioned_by": actor_id,
        }
        lifecycle_state["current_phase"] = target_phase
        lifecycle_state["phase_start_date"] = datetime.utcnow().isoformat()
        lifecycle_state["transitions"].append(transition_record)
        lifecycle_state["gates_passed"].append(gate_name)
        self.projects[project_id]["current_phase"] = target_phase
        self.projects[project_id]["phase_history"].append(transition_record)
        self.lifecycle_store.upsert(context.tenant_id, project_id, lifecycle_state)
        context.metadata["previous_phase"] = current_phase
        return transition_record

    async def _rollback_phase_transition(
        self, context: OrchestrationContext, _exc: Exception | None
    ) -> None:
        project_id = context.project_id
        lifecycle_state = await self._get_lifecycle_state(context.tenant_id, project_id)
        if not lifecycle_state:
            return
        previous_phase = context.metadata.get("previous_phase")
        if previous_phase:
            lifecycle_state["current_phase"] = previous_phase
            lifecycle_state["phase_start_date"] = datetime.utcnow().isoformat()
            self.projects[project_id]["current_phase"] = previous_phase
            self.lifecycle_store.upsert(context.tenant_id, project_id, lifecycle_state)

    async def _persist_lifecycle_state(self, context: OrchestrationContext) -> dict[str, Any]:
        lifecycle_state = await self._get_lifecycle_state(context.tenant_id, context.project_id)
        if not lifecycle_state:
            raise ValueError("Lifecycle state not found for persistence")
        return self.persistence.store_lifecycle_state(
            context.tenant_id, context.project_id, lifecycle_state
        )

    async def _publish_phase_changed(self, context: OrchestrationContext) -> dict[str, Any]:
        transition_record = context.results.get("apply_transition", {})
        await self._publish_project_transitioned(
            context.project_id,
            transition_record.get("from_phase"),
            transition_record.get("to_phase"),
            transition_record.get("transitioned_by", "system"),
            tenant_id=context.tenant_id,
            correlation_id=context.correlation_id,
        )
        await self.event_bus.publish(
            "phase.changed",
            {
                "project_id": context.project_id,
                "from_phase": transition_record.get("from_phase"),
                "to_phase": transition_record.get("to_phase"),
                "gate_name": transition_record.get("gate_name"),
            },
        )
        return {"status": "published"}

    async def _evaluate_gate_criteria(self, context: OrchestrationContext) -> dict[str, Any]:
        gate_name = context.payload.get("gate_name")
        project_id = context.project_id
        gate_criteria_def = await self._get_gate_criteria(gate_name, tenant_id=context.tenant_id)
        criteria_status = []
        for criterion in gate_criteria_def:
            status = await self._check_criterion(project_id, criterion)
            criteria_status.append(
                {
                    "criterion": criterion,
                    "met": status,
                    "description": await self._get_criterion_description(criterion),
                }
            )
        readiness_score = (
            sum(1 for c in criteria_status if c["met"]) / len(criteria_status)
            if criteria_status
            else 0
        )
        missing_criteria = [c for c in criteria_status if not c["met"]]
        criteria_met = readiness_score >= 0.90
        evaluation = {
            "project_id": project_id,
            "gate_name": gate_name,
            "criteria_met": criteria_met,
            "gate_status": "passed" if criteria_met else "failed",
            "readiness_score": readiness_score,
            "criteria_status": criteria_status,
            "missing_criteria": missing_criteria,
            "evaluated_at": datetime.utcnow().isoformat(),
            "recommendation": "Proceed" if criteria_met else "Complete missing activities",
        }
        return evaluation

    async def _score_gate_readiness(self, context: OrchestrationContext) -> dict[str, Any]:
        evaluation = context.results["evaluate_criteria"]
        health_snapshot = self.health_scores.get(context.project_id)
        project_data = self.projects.get(context.project_id, {})
        features = self.readiness_model.build_features(
            evaluation.get("criteria_status", []), health_snapshot
        )
        ml_score = self.readiness_model.predict(features)
        readiness_features = self.readiness_model.build_readiness_features(
            project_data, health_snapshot, evaluation.get("criteria_status", [])
        )
        ai_score = self.readiness_model.predict_with_ai_service(
            self.ai_model_service, readiness_features
        )
        evaluation["readiness_score"] = max(
            evaluation["readiness_score"], ml_score, ai_score or 0.0
        )
        evaluation["health_snapshot"] = health_snapshot or {}
        evaluation["readiness_model"] = {
            "score": ml_score,
            "trained": self.readiness_model.trained,
            "ai_score": ai_score,
            "ai_model_id": self.readiness_model.ai_model_id,
        }
        evaluation["readiness_features"] = readiness_features
        return evaluation

    async def _persist_gate_evaluation(self, context: OrchestrationContext) -> dict[str, Any]:
        evaluation = context.results["evaluate_criteria"]
        return self.persistence.store_gate_evaluation(
            context.tenant_id, context.project_id, evaluation
        )

    async def _publish_gate_event(self, context: OrchestrationContext) -> dict[str, Any]:
        evaluation = context.results["evaluate_criteria"]
        topic = "gate.passed" if evaluation.get("criteria_met") else "gate.failed"
        await self.event_bus.publish(topic, evaluation)
        return {"topic": topic}

    async def _sync_gate_decision(self, context: OrchestrationContext) -> dict[str, Any]:
        evaluation = context.results["evaluate_criteria"]
        results = await self.external_sync.sync_gate_decision(
            context.project_id, evaluation.get("gate_name"), evaluation
        )
        return {"sync_results": [result.__dict__ for result in results]}

    async def _summarize_gate(self, context: OrchestrationContext) -> dict[str, Any]:
        evaluation = context.results["evaluate_criteria"]
        summary_payload = {"gate_name": evaluation.get("gate_name"), **evaluation}
        summary = await self.summarizer.summarize(summary_payload)
        record = {
            "project_id": context.project_id,
            "gate_name": evaluation.get("gate_name"),
            "summary": summary["summary"],
            "provider": summary["provider"],
            "created_at": datetime.utcnow().isoformat(),
        }
        await self._store_gate_summary(context.tenant_id, record)
        return record

    async def _store_gate_summary(self, tenant_id: str, record: dict[str, Any]) -> None:
        if self.knowledge_agent:
            await self.knowledge_agent.process(
                {
                    "action": "ingest_document",
                    "document": {
                        "document_id": f"gate-summary-{record['project_id']}-{record['gate_name']}",
                        "title": f"Gate Summary: {record['gate_name']}",
                        "content": record["summary"],
                        "metadata": record,
                    },
                    "tenant_id": tenant_id,
                }
            )
        else:
            self.persistence.store_summary(tenant_id, record["project_id"], record)

    async def _persist_health_metrics(self, context: OrchestrationContext) -> dict[str, Any]:
        health_data = context.payload["health_data"]
        project_id = context.project_id
        self.health_scores[project_id] = health_data
        record_id = f"{project_id}-{health_data['monitored_at']}"
        self.health_store.upsert(context.tenant_id, record_id, health_data.copy())
        self.monitor_client.record_metric(
            "lifecycle.health.composite",
            float(health_data.get("composite_score", 0.0)),
            metadata={"project_id": project_id, "tenant_id": context.tenant_id},
        )
        return self.persistence.store_health_metrics(context.tenant_id, project_id, health_data)

    async def _publish_health_event(self, context: OrchestrationContext) -> dict[str, Any]:
        health_data = context.payload["health_data"]
        await self._publish_health_updated(
            context.project_id,
            health_data,
            tenant_id=context.tenant_id,
        )
        return {"status": "published"}

    async def _notify_health_if_needed(self, context: OrchestrationContext) -> dict[str, Any]:
        health_data = context.payload["health_data"]
        if health_data.get("health_status") == "Critical":
            return await self.notification_service.notify_gate_decision(
                {
                    "project_id": context.project_id,
                    "event": "project.health.critical",
                    "health_data": health_data,
                }
            )
        return {"status": "skipped", "reason": "health_not_critical"}

    async def _publish_methodology_adjusted(self, context: OrchestrationContext) -> dict[str, Any]:
        payload = context.payload.get("project_data", {})
        await self.event_bus.publish("methodology.adjusted", payload)
        return payload

    async def _get_lifecycle_state(self, tenant_id: str, project_id: str) -> dict[str, Any] | None:
        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            lifecycle_state = self.lifecycle_store.get(tenant_id, project_id)
            if lifecycle_state:
                self.lifecycle_states[project_id] = lifecycle_state
        return lifecycle_state

    async def _publish_project_transitioned(
        self,
        project_id: str,
        from_stage: str,
        to_stage: str,
        actor_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> None:
        event = ProjectTransitionedEvent(
            event_name="project.transitioned",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "project_id": project_id,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "transitioned_at": datetime.utcnow(),
                "actor_id": actor_id,
            },
        )
        await self.event_bus.publish("project.transitioned", event.model_dump())

    async def _publish_health_updated(
        self,
        project_id: str,
        health_data: dict[str, Any],
        *,
        tenant_id: str,
    ) -> None:
        event = ProjectHealthUpdatedEvent(
            event_name="project.health.updated",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            trace_id=get_trace_id(),
            payload={
                "project_id": project_id,
                "health_data": health_data,
            },
        )
        await self.event_bus.publish("project.health.updated", event.model_dump())

    async def _publish_health_report_generated(
        self, report: dict[str, Any], *, tenant_id: str
    ) -> None:
        event = ProjectHealthReportGeneratedEvent(
            event_name="project.health.report.generated",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            trace_id=get_trace_id(),
            payload={"report": report},
        )
        await self.event_bus.publish("project.health.report.generated", event.model_dump())

    async def _request_override_approval(
        self,
        *,
        project_id: str,
        gate_name: str,
        override_reason: str,
        gate_evaluation: dict[str, Any],
        requester: str,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not self.approval_agent:
            return {"status": "skipped", "reason": "approval_agent_not_configured"}
        response = await self.approval_agent.process(
            {
                "request_type": "phase_gate",
                "request_id": f"{project_id}:{gate_name}:override",
                "requester": requester,
                "details": {
                    "project_id": project_id,
                    "gate_name": gate_name,
                    "override_reason": override_reason,
                    "gate_evaluation": gate_evaluation,
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )
        return response

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
