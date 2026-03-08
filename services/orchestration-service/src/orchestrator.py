"""
Agent Orchestrator - Manages agent lifecycle and routing
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import httpx
from observability.metrics import (
    agent_request_count,
    agent_request_latency,
    build_business_workflow_metrics,
)
from observability.tracing import inject_trace_headers
from persistence import OrchestrationStateStore, WorkflowState, build_state_store, make_state_key
from pydantic import ValidationError
from workflow_client import WorkflowClient

from agents.runtime import AgentContext, AgentResponse, AgentResponseMetadata, BaseAgent
from agents.runtime.src.models import ReadinessReport, ReadinessSeverity
from tools.runtime_paths import bootstrap_runtime_paths

if TYPE_CHECKING:
    from response_orchestration_agent import ResponseOrchestrationAgent

logger = logging.getLogger(__name__)
MAX_AGENT_CONCURRENCY = int(os.getenv("MAX_AGENT_CONCURRENCY", "5"))
AGENT_CALL_TIMEOUT = float(os.getenv("AGENT_CALL_TIMEOUT", "30.0"))
DEMO_QUERY_TRIGGER = "full platform demo"
READINESS_FAILURE_MODE = (
    os.getenv("ORCHESTRATOR_READINESS_FAILURE_MODE", "quarantine").strip().lower()
)
DEFAULT_POLICY_BUNDLE_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "bundles" / "default-policy-bundle.yaml"
)


@dataclass
class AgentDependency:
    agent_id: str
    depends_on: list[str]


@dataclass
class AgentLifecycleState:
    agent_id: str
    status: str
    updated_at: str
    reason: str | None = None


class AgentOrchestrator:
    """
    Central orchestrator for all PPM agents.

    Manages agent lifecycle, routing, and coordination.
    """

    def __init__(self, workflow_client: WorkflowClient | None = None) -> None:
        self.agents: dict[str, BaseAgent] = {}
        self.catalog_agents: dict[str, BaseAgent] = {}
        self.initialized = False
        self.intent_router: BaseAgent | None = None
        self.response_orchestrator: BaseAgent | None = None
        self.policy_bundle_path = DEFAULT_POLICY_BUNDLE_PATH
        self.dependencies: dict[str, list[str]] = {}
        self.agent_states: dict[str, AgentLifecycleState] = {}
        self.agent_readiness: dict[str, ReadinessReport] = {}
        self.workflow_states: dict[str, WorkflowState] = {}
        self.workflow_client = workflow_client or WorkflowClient()
        state_path = Path(
            os.getenv(
                "ORCHESTRATION_STATE_PATH",
                "services/orchestration-service/storage/orchestration-state.json",
            )
        )
        self.state_store: OrchestrationStateStore = build_state_store(state_path)
        self._agent_semaphore = asyncio.Semaphore(MAX_AGENT_CONCURRENCY)
        self._orchestrator_business_metrics = build_business_workflow_metrics(
            "orchestration-service", "orchestrator"
        )

    async def initialize(self) -> None:
        """Initialize all 25 agents."""
        logger.info("Initializing Agent Orchestrator...")
        logger.info("Using policy bundle: %s", self.policy_bundle_path)
        self.workflow_states = await self.state_store.load()
        if self.workflow_states:
            logger.info("Loaded %s workflow states for resume", len(self.workflow_states))

        # Initialize core orchestration agents (Agents 1-2)
        bootstrap_runtime_paths()
        from intent_router_agent import IntentRouterAgent
        from response_orchestration_agent import ResponseOrchestrationAgent

        self.intent_router = IntentRouterAgent()
        intent_router = self.intent_router
        await self._initialize_and_register_agent(intent_router)

        self.response_orchestrator = ResponseOrchestrationAgent()
        response_orchestrator = self.response_orchestrator
        await self._initialize_and_register_agent(response_orchestrator)

        # Load all other agents
        await self._load_governance_agents()  # Agents 3, 16
        await self._load_portfolio_agents()  # Agents 4, 5, 6, 12
        await self._load_delivery_agents()  # Agents 7, 8, 9, 10, 11
        await self._load_operations_agents()  # Agents 13, 14, 15, 17, 21
        await self._load_platform_agents()  # Agents 18, 19, 20, 22, 23, 24, 25

        if self.response_orchestrator:
            response_orchestrator = cast("ResponseOrchestrationAgent", self.response_orchestrator)
            response_orchestrator.agent_registry = self.agents

        self.initialized = True
        logger.info(
            "Orchestrator initialized with %s agents",
            len(self.agents),
            extra={"agent_count": len(self.agents)},
        )

    async def _initialize_and_register_agent(self, agent: BaseAgent) -> None:
        await agent.initialize()
        readiness_report = await agent.readiness_check()
        self.agent_readiness[agent.agent_id] = readiness_report
        critical_failures = [
            check
            for check in readiness_report.checks
            if not check.passed and check.severity == ReadinessSeverity.critical
        ]
        if critical_failures:
            failure_reason = readiness_report.last_failure_reason or critical_failures[0].message
            self.set_agent_state(agent.agent_id, "quarantined", reason=failure_reason)
            logger.error(
                "Agent %s failed readiness checks and was quarantined",
                agent.agent_id,
                extra={"failures": [item.model_dump() for item in critical_failures]},
            )
            if READINESS_FAILURE_MODE == "fail_startup":
                raise RuntimeError(
                    f"Agent {agent.agent_id} failed readiness checks: {failure_reason}"
                )
            return

        self._register_agent(agent)
        self.set_agent_state(agent.agent_id, "running")

    def get_agent_readiness(self, agent_id: str) -> ReadinessReport | None:
        return self.agent_readiness.get(agent_id)

    def list_agent_readiness(self) -> list[ReadinessReport]:
        return list(self.agent_readiness.values())

    def register_dependency(self, agent_id: str, depends_on: list[str]) -> None:
        self.dependencies[agent_id] = depends_on

    def list_dependencies(self) -> list[AgentDependency]:
        return [
            AgentDependency(agent_id=agent_id, depends_on=deps)
            for agent_id, deps in self.dependencies.items()
        ]

    def set_agent_state(self, agent_id: str, status: str, reason: str | None = None) -> None:
        self.agent_states[agent_id] = AgentLifecycleState(
            agent_id=agent_id,
            status=status,
            updated_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        )

    def get_agent_state(self, agent_id: str) -> AgentLifecycleState | None:
        return self.agent_states.get(agent_id)

    def _dependencies_satisfied(self, agent_id: str) -> bool:
        deps = self.dependencies.get(agent_id, [])
        for dep in deps:
            state = self.agent_states.get(dep)
            if not state or state.status != "running":
                return False
        return True

    def dependencies_satisfied(self, agent_id: str) -> bool:
        return self._dependencies_satisfied(agent_id)

    async def enforce_policy(self, tenant_id: str, agent_id: str, roles: list[str]) -> None:
        policy_engine = os.getenv("POLICY_ENGINE_URL")
        if not policy_engine:
            return
        service_token = os.getenv("POLICY_ENGINE_SERVICE_TOKEN")
        if not service_token:
            raise RuntimeError("Policy engine token missing")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{policy_engine}/rbac/evaluate",
                json={
                    "tenant_id": tenant_id,
                    "roles": roles,
                    "permission": f"agent.execute.{agent_id}",
                },
                headers={"Authorization": f"Bearer {service_token}", "X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            if response.json().get("decision") != "allow":
                raise PermissionError("Policy denied agent execution")

    async def persist_workflow_state(
        self, tenant_id: str, run_id: str, status: str, checkpoint: str, payload: dict[str, Any]
    ) -> WorkflowState:
        key = make_state_key(tenant_id, run_id)
        existing_state = self.workflow_states.get(key)
        version = existing_state.version if existing_state else 0
        state = WorkflowState(
            run_id=run_id,
            tenant_id=tenant_id,
            status=status,
            last_checkpoint=checkpoint,
            payload=payload,
            version=version,
        )
        saved_state = await self.state_store.save(state)
        self.workflow_states[key] = saved_state
        return saved_state

    async def start_workflow(
        self,
        tenant_id: str,
        workflow_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        classification: str = "internal",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_payload = {
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "classification": classification,
            "payload": payload,
            "actor": actor,
        }
        workflow_headers = self._workflow_headers(tenant_id, headers)
        return await self.workflow_client.start_workflow(request_payload, workflow_headers)

    async def list_workflows(
        self, tenant_id: str, headers: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        workflow_headers = self._workflow_headers(tenant_id, headers)
        return await self.workflow_client.list_workflows(workflow_headers)

    async def get_workflow(
        self, tenant_id: str, run_id: str, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        workflow_headers = self._workflow_headers(tenant_id, headers)
        return await self.workflow_client.get_workflow(run_id, workflow_headers)

    async def resume_workflow(
        self, tenant_id: str, run_id: str, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        workflow_headers = self._workflow_headers(tenant_id, headers)
        return await self.workflow_client.resume_workflow(run_id, workflow_headers)

    def _workflow_headers(
        self, tenant_id: str, headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        workflow_headers = dict(headers or {})
        correlation_id = workflow_headers.get("X-Correlation-ID") or str(uuid4())
        workflow_headers.setdefault("X-Tenant-ID", tenant_id)
        workflow_headers["X-Correlation-ID"] = correlation_id
        workflow_headers = inject_trace_headers(workflow_headers, correlation_id=correlation_id)
        logger.info(
            "workflow_request_headers_prepared",
            extra={"correlation_id": correlation_id, "tenant_id": tenant_id},
        )
        return workflow_headers

    def resume_workflows(self, tenant_id: str) -> list[str]:
        return [
            state.run_id for state in self.workflow_states.values() if state.tenant_id == tenant_id
        ]

    def get_state(self, tenant_id: str, run_id: str) -> WorkflowState | None:
        return self.workflow_states.get(make_state_key(tenant_id, run_id))

    def list_states(self, tenant_id: str) -> list[WorkflowState]:
        return [state for state in self.workflow_states.values() if state.tenant_id == tenant_id]

    async def _execute_agent(
        self, agent: BaseAgent, context: dict[str, Any] | AgentContext
    ) -> AgentResponse:
        async with self._agent_semaphore:
            start = time.monotonic()
            outcome = "success"
            agent_name = getattr(agent, "name", None) or agent.agent_id
            try:
                payload = context
                if isinstance(context, AgentContext):
                    payload = {"context": context.model_dump()}
                result = await asyncio.wait_for(
                    agent.execute(cast(dict[str, Any], payload)),
                    timeout=AGENT_CALL_TIMEOUT,
                )
                return AgentResponse.model_validate(result)
            except ValidationError as exc:
                outcome = "error"
                duration = time.monotonic() - start
                logger.exception(
                    "Agent %s returned invalid response payload",
                    agent.agent_id,
                    extra={"duration": duration, "errors": exc.errors()},
                )
                correlation_id = self._resolve_correlation_id(context)
                return AgentResponse(
                    success=False,
                    error="Invalid agent response payload",
                    data=None,
                    metadata=AgentResponseMetadata(
                        agent_id=agent.agent_id,
                        catalog_id=agent.catalog_id or agent.agent_id,
                        timestamp=datetime.utcnow().isoformat(),
                        correlation_id=correlation_id or "unknown",
                        trace_id=None,
                        execution_time_seconds=duration,
                        policy_reasons=None,
                    ),
                )
            except TimeoutError:
                outcome = "error"
                duration = time.monotonic() - start
                logger.error(
                    "Agent %s timed out after %ss",
                    agent.agent_id,
                    AGENT_CALL_TIMEOUT,
                    extra={"duration": duration},
                )
                correlation_id = self._resolve_correlation_id(context)
                return AgentResponse(
                    success=False,
                    error="Agent timeout",
                    data=None,
                    metadata=AgentResponseMetadata(
                        agent_id=agent.agent_id,
                        catalog_id=agent.catalog_id or agent.agent_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        correlation_id=correlation_id or "unknown",
                        trace_id=None,
                        execution_time_seconds=duration,
                        policy_reasons=None,
                    ),
                )
            except Exception as exc:
                outcome = "error"
                duration = time.monotonic() - start
                logger.exception(
                    "Agent %s execution failed",
                    agent.agent_id,
                    extra={"duration": duration},
                )
                correlation_id = self._resolve_correlation_id(context)
                return AgentResponse(
                    success=False,
                    error=str(exc),
                    data=None,
                    metadata=AgentResponseMetadata(
                        agent_id=agent.agent_id,
                        catalog_id=agent.catalog_id or agent.agent_id,
                        timestamp=datetime.utcnow().isoformat(),
                        correlation_id=correlation_id or "unknown",
                        trace_id=None,
                        execution_time_seconds=duration,
                        policy_reasons=None,
                    ),
                )
            finally:
                duration = time.monotonic() - start
                agent_request_count.labels(agent_name, outcome).inc()
                agent_request_latency.labels(agent_name).observe(duration)

    @staticmethod
    def _resolve_correlation_id(context: dict[str, Any] | AgentContext) -> str | None:
        if isinstance(context, AgentContext):
            return context.correlation_id
        context_payload = context.get("context", {})
        if isinstance(context_payload, AgentContext):
            return context_payload.correlation_id
        return context_payload.get("correlation_id") or context.get("correlation_id")

    async def _load_governance_agents(self) -> None:
        """Initialize governance agents."""
        logger.info("Loading governance agents...")

        # Approval Workflow
        from approval_workflow_agent import ApprovalWorkflowAgent
        from compliance_regulatory_agent import ComplianceRegulatoryAgent

        approval_agent = ApprovalWorkflowAgent()

        await self._initialize_and_register_agent(approval_agent)

        # Compliance & Regulatory

        compliance_agent = ComplianceRegulatoryAgent()
        await self._initialize_and_register_agent(compliance_agent)

        logger.info("Governance agents loaded")

    async def _load_portfolio_agents(self) -> None:
        """Initialize portfolio management agents."""
        logger.info("Loading portfolio agents...")

        # Demand & Intake
        from business_case_investment_agent import BusinessCaseInvestmentAgent
        from demand_intake_agent import DemandIntakeAgent
        from financial_management_agent import FinancialManagementAgent
        from portfolio_strategy_agent import PortfolioStrategyAgent

        demand_agent = DemandIntakeAgent()
        await self._initialize_and_register_agent(demand_agent)

        # Business Case & Investment Analysis
        business_case_agent = BusinessCaseInvestmentAgent()
        await self._initialize_and_register_agent(business_case_agent)

        # Portfolio Strategy & Optimization
        portfolio_strategy_agent = PortfolioStrategyAgent()
        await self._initialize_and_register_agent(portfolio_strategy_agent)

        # Financial Management
        financial_agent = FinancialManagementAgent()
        await self._initialize_and_register_agent(financial_agent)

        logger.info("Portfolio agents loaded")

    async def _load_delivery_agents(self) -> None:
        """Initialize delivery agents."""
        logger.info("Loading delivery agents...")

        # Program Management
        from program_management_agent import ProgramManagementAgent
        from project_definition_agent import ProjectDefinitionAgent
        from project_lifecycle_agent import ProjectLifecycleAgent
        from resource_capacity_agent import ResourceCapacityAgent
        from schedule_planning_agent import SchedulePlanningAgent

        program_agent = ProgramManagementAgent()
        await self._initialize_and_register_agent(program_agent)

        # Project Definition & Scope
        project_definition_agent = ProjectDefinitionAgent()
        await self._initialize_and_register_agent(project_definition_agent)

        # Project Lifecycle & Governance
        lifecycle_agent = ProjectLifecycleAgent()
        await self._initialize_and_register_agent(lifecycle_agent)

        # Schedule & Planning
        schedule_agent = SchedulePlanningAgent()
        await self._initialize_and_register_agent(schedule_agent)

        # Resource & Capacity Management
        resource_agent = ResourceCapacityAgent()
        await self._initialize_and_register_agent(resource_agent)

        logger.info("Delivery agents loaded")

    async def _load_operations_agents(self) -> None:
        """Initialize operations agents."""
        logger.info("Loading operations agents...")

        # Vendor & Procurement Management
        from change_configuration_agent import ChangeConfigurationAgent
        from quality_management_agent import QualityManagementAgent
        from risk_management_agent import RiskManagementAgent
        from stakeholder_communications_agent import StakeholderCommunicationsAgent
        from vendor_procurement_agent import VendorProcurementAgent

        vendor_agent = VendorProcurementAgent()
        await self._initialize_and_register_agent(vendor_agent)

        # Quality Management
        quality_agent = QualityManagementAgent()
        await self._initialize_and_register_agent(quality_agent)

        # Risk Management
        risk_agent = RiskManagementAgent()
        await self._initialize_and_register_agent(risk_agent)

        # Change & Configuration Management
        change_agent = ChangeConfigurationAgent()
        await self._initialize_and_register_agent(change_agent)

        # Stakeholder & Communications Management
        stakeholder_agent = StakeholderCommunicationsAgent()
        await self._initialize_and_register_agent(stakeholder_agent)

        logger.info("Operations agents loaded")

    async def _load_platform_agents(self) -> None:
        """Initialize platform agents."""
        logger.info("Loading platform agents...")

        # Release & Deployment
        from analytics_insights_agent import AnalyticsInsightsAgent
        from data_sync_agent import DataSyncAgent
        from knowledge_management_agent import KnowledgeManagementAgent
        from process_mining_agent import ProcessMiningAgent
        from release_deployment_agent import ReleaseDeploymentAgent
        from system_health_agent import SystemHealthAgent

        release_agent = ReleaseDeploymentAgent()
        await self._initialize_and_register_agent(release_agent)

        # Knowledge & Document Management
        knowledge_agent = KnowledgeManagementAgent()
        await self._initialize_and_register_agent(knowledge_agent)

        # Continuous Improvement & Process Mining
        process_mining_agent = ProcessMiningAgent()
        await self._initialize_and_register_agent(process_mining_agent)

        # Analytics & Insights
        analytics_agent = AnalyticsInsightsAgent()
        await self._initialize_and_register_agent(analytics_agent)

        # Data Synchronization & Consistency
        data_sync_agent = DataSyncAgent()
        await self._initialize_and_register_agent(data_sync_agent)

        # System Health & Monitoring
        health_agent = SystemHealthAgent()
        await self._initialize_and_register_agent(health_agent)

        logger.info("Platform agents loaded")

    async def approve_plan(
        self,
        *,
        plan_id: str,
        decision: str,
        tasks: list[dict[str, Any]] | None = None,
        actor: str = "orchestration-api",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")

        assert self.response_orchestrator is not None, "Response orchestrator not initialized"
        request_context = context or {}
        return await self._execute_agent(
            self.response_orchestrator,
            {
                "routing": [],
                "parameters": {},
                "query": request_context.get("query") or "plan approval",
                "context": request_context,
                "plan_id": plan_id,
                "approval_decision": decision,
                "plan_updates": tasks,
                "approval_actor": actor,
            },
        ).model_dump()

    async def process_query(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        prompt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a user query through the full agent pipeline.

        Args:
            query: User's natural language query
            context: Optional context (user_id, session_id, etc.)

        Returns:
            Final aggregated response
        """
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")

        started = time.monotonic()
        outcome = "success"

        assert self.intent_router is not None, "Intent router not initialized"
        assert self.response_orchestrator is not None, "Response orchestrator not initialized"
        request_context = context or {}

        if self._is_full_demo_run_enabled(query=query, context=request_context):
            correlation_id = request_context.get("correlation_id")
            if not correlation_id:
                correlation_id = f"corr-{os.urandom(8).hex()}"

            orchestration_response = await self._execute_agent(
                self.response_orchestrator,
                {
                    "routing": self._build_full_demo_routing_plan(),
                    "parameters": {},
                    "query": query,
                    "context": {**request_context, "correlation_id": correlation_id},
                    "approval_decision": "approve",
                },
            )
            payload = orchestration_response.model_dump()
            self._record_orchestrator_business_metrics(
                query=query,
                tenant_id=request_context.get("tenant_id", "unknown"),
                correlation_id=correlation_id,
                started=started,
                outcome="success" if payload.get("success", True) else "error",
            )
            return payload

        # Step 1: Route the query
        correlation_id = request_context.get("correlation_id")
        if not correlation_id:
            correlation_id = f"corr-{os.urandom(8).hex()}"

        intent_response = await self._execute_agent(
            self.intent_router,
            {
                "query": query,
                "context": {**request_context, "correlation_id": correlation_id},
            },
        )

        if not intent_response.success:
            outcome = "error"
            payload = {
                "success": False,
                "error": "Failed to route query",
                "details": intent_response.model_dump(),
            }
            self._record_orchestrator_business_metrics(
                query=query,
                tenant_id=request_context.get("tenant_id", "unknown"),
                correlation_id=correlation_id,
                started=started,
                outcome=outcome,
            )
            return payload
        intent_payload = intent_response.data.model_dump() if intent_response.data else {}

        # Step 2: Orchestrate response
        parameters = intent_payload.get("parameters", {})
        if prompt:
            parameters = {**parameters, "prompt": prompt}

        orchestration_response = await self._execute_agent(
            self.response_orchestrator,
            {
                "routing": intent_payload.get("routing", []),
                "parameters": parameters,
                "query": query,
                "context": {**request_context, "correlation_id": correlation_id},
            },
        )
        payload = orchestration_response.model_dump()
        self._record_orchestrator_business_metrics(
            query=query,
            tenant_id=request_context.get("tenant_id", "unknown"),
            correlation_id=correlation_id,
            started=started,
            outcome="success" if payload.get("success", True) else "error",
        )
        return payload

    def _record_orchestrator_business_metrics(
        self,
        *,
        query: str,
        tenant_id: str,
        correlation_id: str,
        started: float,
        outcome: str,
    ) -> None:
        attributes = {
            "service.name": "orchestration-service",
            "tenant.id": tenant_id,
            "trace.id": correlation_id,
            "workflow": "orchestrator",
            "outcome": outcome,
            "query_type": "full_demo" if DEMO_QUERY_TRIGGER in query.lower() else "standard",
        }
        self._orchestrator_business_metrics.executions_total.add(1, attributes)
        self._orchestrator_business_metrics.execution_duration_seconds.record(
            time.monotonic() - started, attributes
        )

    def _is_full_demo_run_enabled(self, *, query: str, context: dict[str, Any]) -> bool:
        if not self._is_truthy_env_flag("DEMO_MODE") or not self._is_truthy_env_flag(
            "DEMO_MODE_FULL_RUN"
        ):
            return False

        full_demo_context_flag = context.get("full_demo")
        if isinstance(full_demo_context_flag, str):
            full_demo_context_flag = full_demo_context_flag.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        return bool(full_demo_context_flag) or DEMO_QUERY_TRIGGER in query.lower()

    @staticmethod
    def _is_truthy_env_flag(name: str) -> bool:
        return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}

    def _build_full_demo_routing_plan(self) -> list[dict[str, Any]]:
        return [
            {
                "agent_id": agent_id,
                "priority": 1.0,
                "intent": "full_platform_demo",
                "depends_on": [],
                "action": "demo_run",
            }
            for agent_id in sorted(self.agents.keys())
        ]

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """Get agent by ID."""
        agent = self.agents.get(agent_id)
        if agent:
            return agent
        return self.catalog_agents.get(agent_id)

    def get_agent_count(self) -> int:
        """Get total number of loaded agents (built-in + dynamic)."""
        from agents.runtime.src.agent_catalog import list_dynamic_entries

        return len(self.agents) + len(list_dynamic_entries())

    def list_agents(self) -> list[dict[str, Any]]:
        """List all loaded agents (built-in + marketplace)."""
        from agents.runtime.src.agent_catalog import list_dynamic_entries

        result = []
        for agent_id, agent in self.agents.items():
            entry: dict[str, Any] = {
                "agent_id": agent_id,
                "catalog_id": getattr(agent, "catalog_id", agent_id),
                "capabilities": agent.get_capabilities(),
                "source": "builtin",
            }
            if hasattr(agent, "get_metadata"):
                metadata = agent.get_metadata()
                entry["source"] = metadata.get("source", "builtin")
                entry["version"] = metadata.get("version")
                entry["description"] = metadata.get("description")
                entry["category"] = metadata.get("category")
            result.append(entry)

        # Include dynamically registered marketplace agents not yet loaded
        for dynamic_entry in list_dynamic_entries():
            if dynamic_entry.agent_id not in self.agents:
                result.append(
                    {
                        "agent_id": dynamic_entry.agent_id,
                        "catalog_id": dynamic_entry.catalog_id,
                        "capabilities": dynamic_entry.capabilities,
                        "source": dynamic_entry.source,
                        "version": dynamic_entry.version,
                        "description": dynamic_entry.description,
                        "category": dynamic_entry.category,
                        "display_name": dynamic_entry.display_name,
                        "tags": dynamic_entry.tags,
                        "icon": dynamic_entry.icon,
                        "installed": False,
                    }
                )

        return result

    async def register_dynamic_agent(self, agent: BaseAgent) -> None:
        """Register and initialize a dynamically loaded marketplace agent."""
        await self._initialize_and_register_agent(agent)
        logger.info("Dynamic agent %s registered in orchestrator", agent.agent_id)

    def _register_agent(self, agent: BaseAgent) -> None:
        catalog_id = getattr(agent, "catalog_id", None)
        if not catalog_id:
            from agents.runtime.src.agent_catalog import get_catalog_id

            catalog_id = get_catalog_id(agent.agent_id)
            if catalog_id:
                agent.catalog_id = catalog_id

        self.agents[agent.agent_id] = agent
        if catalog_id:
            self.catalog_agents[catalog_id] = agent

    async def cleanup(self) -> None:
        """Clean up all agents concurrently with graceful error isolation."""
        logger.info("Cleaning up orchestrator (%d agents)...", len(self.agents))

        # Persist workflow state before tearing down agents
        try:
            for state in self.workflow_states.values():
                await self.state_store.save(state)
        except Exception as exc:
            logger.error("Failed to persist workflow states during cleanup: %s", exc)

        # Clean up all agents concurrently for faster shutdown
        async def _cleanup_agent(agent_id: str, agent: BaseAgent) -> None:
            try:
                await asyncio.wait_for(agent.cleanup(), timeout=10.0)
            except TimeoutError:
                logger.warning("Agent %s cleanup timed out", agent_id)
            except Exception as e:
                logger.error("Error cleaning up agent %s: %s", agent_id, str(e))

        await asyncio.gather(
            *[_cleanup_agent(aid, agent) for aid, agent in self.agents.items()],
            return_exceptions=True,
        )

        self.agents.clear()
        self.catalog_agents.clear()
        self.agent_readiness.clear()
        self.initialized = False
        logger.info("Orchestrator cleanup complete")
