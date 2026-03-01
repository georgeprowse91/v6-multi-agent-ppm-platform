"""
Agent 2: Response Orchestration Agent

Purpose:
Coordinates multi-agent queries, manages parallel/sequential execution,
and aggregates responses into coherent outputs.

Specification: agents/core-orchestration/agent-02-response-orchestration/README.md
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Union, cast

_COMMON_SRC = Path(__file__).resolve().parents[5] / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

import httpx  # noqa: E402
import yaml  # noqa: E402
from plan_schema import Plan, PlanTask  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field, ValidationError  # noqa: E402

from agents.common.web_search import (  # noqa: E402
    SearchPurpose,
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent, get_event_bus  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from observability.metrics import configure_metrics  # noqa: E402
from observability.tracing import get_trace_id, inject_trace_headers  # noqa: E402


class RoutingEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_id: str
    priority: float | None = Field(default=None, ge=0.0, le=1.0)
    intent: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    action: str | None = None


class OrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    routing: list[RoutingEntry]
    intents: list[dict[str, Any]] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    context: dict[str, Any] | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None
    prompt_id: str | None = None
    prompt_description: str | None = None
    prompt_tags: list[str] = Field(default_factory=list)
    plan_id: str | None = None
    approval_decision: str | None = None
    plan_updates: list[dict[str, Any]] | None = None
    approval_actor: str | None = None


class AgentInvocationResult(BaseModel):
    success: bool
    agent_id: str
    data: dict[str, Any] | None = None
    error: str | None = None
    cached: bool = False


class OrchestrationResponse(BaseModel):
    aggregated_response: Union[str, dict[str, Any]]
    status: str = "completed"
    agent_results: list[AgentInvocationResult]
    execution_summary: dict[str, Any]
    agent_activity: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] | None = None


class ValidationErrorPayload(BaseModel):
    error: str
    details: list[dict[str, Any]]


VENDOR_RESEARCH_PROMPTS = {"vendor_research", "vendor_evaluation"}
COMPLIANCE_RESEARCH_PROMPTS = {"compliance_updates", "compliance_checklist"}


class ResponseOrchestrationAgent(BaseAgent):
    """
    Response Orchestration Agent - Coordinates multi-agent workflows.

    Key Capabilities:
    - Multi-agent query planning
    - Parallel and sequential execution
    - Response aggregation
    - Timeout and fallback management
    - Result caching
    """

    def __init__(
        self, agent_id: str = "response-orchestration-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)
        self.max_concurrency = config.get("max_concurrency", 5) if config else 5
        self.agent_timeout = config.get("agent_timeout", 30) if config else 30
        self.cache_ttl = config.get("cache_ttl", 900) if config else 900  # 15 minutes
        self.cache_max_entries = config.get("cache_max_entries", 256) if config else 256
        self.agent_endpoints = config.get("agent_endpoints", {}) if config else {}
        self.max_retries = config.get("max_retries", 2) if config else 2
        self.require_approval = config.get("require_approval", False) if config else False
        self.retry_backoff_base = config.get("retry_backoff_base", 0.5) if config else 0.5
        self.retry_backoff_max = config.get("retry_backoff_max", 5.0) if config else 5.0
        self.circuit_breaker_threshold = config.get("circuit_breaker_threshold", 3) if config else 3
        self.event_bus = config.get("event_bus") if config else None
        self.cache_backend = config.get("cache_backend") if config else None
        self.agent_registry_loader = config.get("agent_registry_loader") if config else None
        self.agent_registry_path = config.get("agent_registry_path") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.http_client = config.get("http_client") if config else None
        self.agent_registry: dict[str, BaseAgent] = (
            config.get("agent_registry", {}) if config else {}
        )
        self._failure_counts: dict[str, int] = {}
        self._circuit_open_until: dict[str, float] = {}
        self._circuit_half_open_window = (
            config.get("circuit_half_open_window", 30.0) if config else 30.0
        )
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._last_validation_error: dict[str, Any] | None = None
        self.plans_dir = (
            Path(config.get("plans_dir"))
            if config and config.get("plans_dir")
            else Path(__file__).resolve().parents[4] / "ops" / "config" / "plans"
        )
        self._current_plan_context: dict[str, Any] = {}
        meter = configure_metrics("response-orchestration")
        self._cache_hits = meter.create_counter(
            name="orchestration_cache_hits_total",
            description="Number of orchestration cache hits",
            unit="1",
        )
        self._cache_misses = meter.create_counter(
            name="orchestration_cache_misses_total",
            description="Number of orchestration cache misses",
            unit="1",
        )
        self._agent_latency = meter.create_histogram(
            name="orchestration_agent_latency_seconds",
            description="Latency per agent invocation",
            unit="s",
        )
        self._agent_failures = meter.create_counter(
            name="orchestration_agent_failures_total",
            description="Number of agent invocation failures",
            unit="1",
        )

    async def initialize(self) -> None:
        """Initialize orchestration engine and cache."""
        await super().initialize()
        self.logger.info("Initializing orchestration engine...")
        self._initialize_cache_backend()
        self._load_agent_registry()
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=self.agent_timeout)
        self.plans_dir.mkdir(parents=True, exist_ok=True)

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        try:
            OrchestrationRequest.model_validate(input_data)
        except ValidationError as exc:
            self._last_validation_error = ValidationErrorPayload(
                error="validation_error", details=exc.errors()
            ).model_dump()
            return False
        self._last_validation_error = None
        return True

    def _build_prompt_payload(
        self, request: OrchestrationRequest, parameters: dict[str, Any]
    ) -> dict[str, Any] | None:
        provided_prompt = parameters.get("prompt")
        prompt_id = parameters.get("prompt_id") or request.prompt_id
        prompt_description = parameters.get("prompt_description") or request.prompt_description
        prompt_tags = parameters.get("prompt_tags") or request.prompt_tags

        if isinstance(provided_prompt, dict):
            prompt_id = provided_prompt.get("id") or prompt_id
            prompt_description = provided_prompt.get("description") or prompt_description
            prompt_tags = provided_prompt.get("tags") or prompt_tags

        if not prompt_id and not prompt_description:
            return None

        payload: dict[str, Any] = {}
        if prompt_id:
            payload["id"] = prompt_id
        if prompt_description:
            payload["description"] = prompt_description
        if prompt_tags:
            payload["tags"] = list(prompt_tags)
        return payload

    def _determine_research_purpose(self, prompt_payload: dict[str, Any]) -> SearchPurpose | None:
        prompt_id = prompt_payload.get("id")
        tags = {str(tag).lower() for tag in prompt_payload.get("tags", [])}
        if prompt_id in VENDOR_RESEARCH_PROMPTS or "vendor" in tags or "procurement" in tags:
            return "vendor"
        if prompt_id in COMPLIANCE_RESEARCH_PROMPTS or "compliance" in tags:
            return "compliance"
        return None

    async def _maybe_attach_external_research(
        self,
        prompt_payload: dict[str, Any],
        *,
        parameters: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        purpose = self._determine_research_purpose(prompt_payload)
        if not purpose:
            return None

        context_parts = [
            parameters.get("project_domain"),
            parameters.get("project_name"),
            context.get("project_id"),
            context.get("methodology"),
            prompt_payload.get("description"),
        ]
        search_context = " ".join(str(part) for part in context_parts if part)
        query = build_search_query(search_context, purpose)
        try:
            snippets = await search_web(query)
            summary = await summarize_snippets(snippets, purpose=purpose)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # pragma: no cover - defensive
            self.logger.warning("External research failed", extra={"error": str(exc)})
            return {
                "purpose": purpose,
                "query": query,
                "snippets": [],
                "summary": "",
                "used_external_research": False,
            }

        return {
            "purpose": purpose,
            "query": query,
            "snippets": snippets,
            "summary": summary,
            "used_external_research": bool(snippets),
        }

    async def process(self, input_data: dict[str, Any]) -> OrchestrationResponse:
        """
        Orchestrate multi-agent workflow.

        Args:
            input_data: {
                "routing": List of agents to invoke (from Intent Router),
                "parameters": Parameters for agents,
                "query": Original user query
            }

        Returns:
            {
                "aggregated_response": Combined response from all agents,
                "agent_results": Individual results from each agent,
                "execution_summary": Timing and status info
            }
        """
        request = OrchestrationRequest.model_validate(input_data)
        routing = [entry.model_dump() for entry in request.routing]
        parameters = dict(request.parameters)
        context = request.context or {}
        correlation_id = (
            context.get("correlation_id") or request.correlation_id or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or request.tenant_id or "unknown"

        prompt_payload = self._build_prompt_payload(request, parameters)
        if prompt_payload:
            parameters["prompt"] = prompt_payload
            external_research = await self._maybe_attach_external_research(
                prompt_payload, parameters=parameters, context=context
            )
            if external_research:
                parameters["external_research"] = external_research
                prompt_payload["external_research"] = external_research

        if not routing and not request.plan_id:
            return OrchestrationResponse(
                aggregated_response="No agents to invoke",
                agent_results=[],
                execution_summary={"total_agents": 0},
            )

        plan = await self._resolve_plan(request.plan_id, routing)
        self._current_plan_context = {
            "plan_id": plan.plan_id,
            "version": plan.version,
        }

        if request.plan_updates is not None:
            plan = self.update_pending_plan(
                plan.plan_id,
                request.plan_updates,
                actor=request.approval_actor or "orchestration-api",
            )

        if request.approval_decision == "reject":
            plan.status = "rejected"
            self._store_plan(plan)
            await self.event_bus.publish(
                "plan.rejected",
                {
                    "plan_id": plan.plan_id,
                    "version": plan.version,
                    "modifications": plan.modification_history,
                    "actor": request.approval_actor or "orchestration-api",
                },
            )
            return OrchestrationResponse(
                aggregated_response="Plan rejected. Execution cancelled.",
                status="rejected",
                agent_results=[],
                execution_summary={
                    "total_agents": len(plan.tasks),
                    "successful": 0,
                    "failed": 0,
                    "plan_id": plan.plan_id,
                    "version": plan.version,
                },
                plan=plan.model_dump(mode="json"),
            )

        if self.require_approval and request.approval_decision != "approve":
            plan.status = "pending_approval"
            self._store_plan(plan)
            return OrchestrationResponse(
                aggregated_response="Plan created and awaiting approval.",
                status="pending_approval",
                agent_results=[],
                execution_summary={
                    "total_agents": len(plan.tasks),
                    "successful": 0,
                    "failed": 0,
                    "plan_id": plan.plan_id,
                    "version": plan.version,
                },
                plan=plan.model_dump(mode="json"),
            )

        plan.status = "approved"
        self._store_plan(plan)
        await self.event_bus.publish(
            "plan.approved",
            {
                "plan_id": plan.plan_id,
                "version": plan.version,
                "modifications": plan.modification_history,
                "actor": request.approval_actor or "orchestration-api",
            },
        )

        # Build dependency graph
        execution_plan = await self._build_execution_plan(
            [
                {
                    "agent_id": task.agent_id,
                    "action": task.action,
                    "depends_on": task.dependencies,
                    **task.metadata,
                }
                for task in plan.tasks
            ]
        )

        # Execute agents according to plan
        execution_start = time.time()
        results = await self._execute_plan(
            execution_plan,
            parameters,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )

        # Aggregate responses
        aggregated = await self._aggregate_responses(results)
        agent_activity = self._build_agent_activity(results, execution_start)
        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="orchestration.aggregated",
            outcome="success",
            metadata={
                "agent_count": len(plan.tasks),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
                "plan_id": plan.plan_id,
                "version": plan.version,
            },
        )

        response = OrchestrationResponse(
            aggregated_response=aggregated,
            status="completed",
            agent_results=[AgentInvocationResult(**result) for result in results],
            execution_summary={
                "total_agents": len(plan.tasks),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
                "plan_id": plan.plan_id,
                "version": plan.version,
            },
            agent_activity=agent_activity,
            plan=plan.model_dump(mode="json"),
        )
        return response

    async def _resolve_plan(self, plan_id: str | None, routing: list[dict[str, Any]]) -> Plan:
        if plan_id:
            return self._load_plan(plan_id)

        new_plan = Plan(
            plan_id=f"plan-{uuid.uuid4()}",
            version=self._next_plan_version(),
            tasks=[
                PlanTask(
                    task_id=f"task-{index + 1}",
                    agent_id=item["agent_id"],
                    action=item.get("action"),
                    dependencies=list(item.get("depends_on") or []),
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key not in {"agent_id", "action", "depends_on"}
                    },
                )
                for index, item in enumerate(routing)
            ],
        )
        self._store_plan(new_plan)
        return new_plan

    def update_pending_plan(
        self, plan_id: str, tasks: list[dict[str, Any]], *, actor: str = "orchestration-api"
    ) -> Plan:
        plan = self._load_plan(plan_id)
        if plan.status != "pending_approval":
            raise ValueError(f"Plan {plan_id} is not pending approval")
        plan.apply_task_updates(tasks, actor=actor)
        self._store_plan(plan)
        return plan

    def _store_plan(self, plan: Plan) -> None:
        destination = self.plans_dir / f"{plan.plan_id}.yaml"
        destination.write_text(yaml.safe_dump(plan.model_dump(mode="json"), sort_keys=False))

    def _load_plan(self, plan_id: str) -> Plan:
        source = self.plans_dir / f"{plan_id}.yaml"
        if not source.exists():
            raise FileNotFoundError(f"Plan not found: {source}")
        payload = yaml.safe_load(source.read_text())
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid plan payload for {plan_id}")
        return Plan.model_validate(payload)

    def _next_plan_version(self) -> int:
        versions: list[int] = []
        for file_path in self.plans_dir.glob("*.yaml"):
            try:
                payload = yaml.safe_load(file_path.read_text())
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("version"), int):
                versions.append(payload["version"])
        return (max(versions) if versions else 0) + 1

    async def _build_execution_plan(self, routing: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build execution plan determining parallel vs sequential execution.

        Returns execution plan with dependency graph.
        """
        nodes: dict[str, dict[str, Any]] = {}
        nodes_by_agent: dict[str, list[str]] = {}
        for index, item in enumerate(routing):
            node_id = str(item.get("task_id") or f"{item['agent_id']}::{index}")
            nodes[node_id] = dict(item)
            nodes_by_agent.setdefault(item["agent_id"], []).append(node_id)

        dependencies: dict[str, set[str]] = {}
        for node_id, item in nodes.items():
            depends_on_nodes: set[str] = set()
            for dependency in item.get("depends_on") or []:
                for dependency_node in nodes_by_agent.get(dependency, []):
                    if dependency_node != node_id:
                        depends_on_nodes.add(dependency_node)
            dependencies[node_id] = depends_on_nodes

        plan: list[list[dict[str, Any]]] = []
        remaining = set(nodes.keys())
        while remaining:
            ready = sorted(node_id for node_id in remaining if not dependencies[node_id])
            if not ready:
                raise ValueError("Dependency cycle detected in routing plan")
            group = [nodes[node_id] for node_id in ready]
            plan.append(group)
            remaining -= set(ready)
            for node_id in remaining:
                dependencies[node_id] -= set(ready)

        return {
            "parallel_groups": plan,
        }

    async def _execute_plan(
        self,
        execution_plan: dict[str, Any],
        parameters: dict[str, Any],
        *,
        correlation_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """
        Execute the plan, invoking agents in parallel or sequentially.

        Returns list of agent results.
        """
        results: list[dict[str, Any]] = []

        # Execute parallel groups
        for group in execution_plan.get("parallel_groups", []):
            group_results = await self._execute_parallel(
                group,
                parameters,
                correlation_id=correlation_id,
                tenant_id=tenant_id,
            )
            results.extend(group_results)
            risk_data = self._extract_risk_data_from_results(group_results)
            if risk_data:
                parameters["risk_data"] = risk_data
                if isinstance(parameters.get("context"), dict):
                    parameters["context"]["risk_data"] = risk_data

        return results

    def _extract_risk_data_from_results(
        self, results: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        for result in results:
            if not result.get("success"):
                continue
            data = result.get("data")
            if not isinstance(data, dict):
                continue
            if isinstance(data.get("risk_data"), dict):
                return cast(dict[str, Any], data["risk_data"])
            if isinstance(data.get("risk_matrix"), dict):
                matrix = data["risk_matrix"].get("matrix_data", [])
                if isinstance(matrix, list):
                    return {
                        "project_id": data.get("project_id"),
                        "project_risk_level": (
                            "high"
                            if data.get("risk_summary", {}).get("high_risks", 0)
                            else (
                                "medium"
                                if data.get("risk_summary", {}).get("medium_risks", 0)
                                else "low"
                            )
                        ),
                        "task_risks": [
                            {
                                "task_id": item.get("task_id"),
                                "risk_id": item.get("risk_id"),
                                "risk_level": str(item.get("risk_level", "low")).lower(),
                                "score": item.get("score", 0),
                            }
                            for item in matrix
                            if isinstance(item, dict) and item.get("task_id")
                        ],
                    }
        return None

    async def _execute_parallel(
        self,
        agents: list[dict[str, Any]],
        parameters: dict[str, Any],
        *,
        correlation_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """
        Execute multiple agents in parallel.

        Returns list of results from all agents.
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _bounded_invoke(agent_info: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await self._invoke_agent(
                    agent_info,
                    parameters,
                    correlation_id=correlation_id,
                    tenant_id=tenant_id,
                )

        tasks = [_bounded_invoke(agent_info) for agent_info in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "success": False,
                        "agent_id": agents[i]["agent_id"],
                        "error": str(result),
                    }
                )
            else:

                processed_results.append(cast(dict[str, Any], result))

        return processed_results

    async def _invoke_agent(
        self,
        agent_info: dict[str, Any],
        parameters: dict[str, Any],
        *,
        correlation_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Invoke a single agent with timeout.

        Returns agent result or error.
        """
        assert self.http_client is not None
        assert self.event_bus is not None
        agent_id = agent_info["agent_id"]
        action = agent_info.get("action")
        cache_key = self._cache_key(agent_id, action, parameters, tenant_id)
        cached = self._get_cached_result(cache_key)
        if cached:
            self._cache_hits.add(1, {"agent_id": agent_id})
            self.logger.info("cache_hit", extra={"agent_id": agent_id})
            return {**cached, "cached": True}
        self._cache_misses.add(1, {"agent_id": agent_id})
        if self._is_circuit_open(agent_id):
            result = {
                "success": False,
                "agent_id": agent_id,
                "error": "Circuit breaker open",
            }
            await self.event_bus.publish("agent.failed", result)
            self._emit_audit_event(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                action="orchestration.agent.invoked",
                outcome="denied",
                metadata={"agent_id": agent_id, "reason": "circuit_breaker_open"},
            )
            return result

        endpoint = agent_info.get("endpoint") or self.agent_endpoints.get(agent_id)
        payload = {
            "agent_id": agent_id,
            "parameters": parameters,
            "correlation_id": correlation_id,
            "action": action,
        }
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._invoke_with_retries(
                    agent_id=agent_id,
                    endpoint=endpoint,
                    payload=payload,
                    correlation_id=correlation_id,
                    parameters=parameters,
                    tenant_id=tenant_id,
                    action=action,
                ),
                timeout=self.agent_timeout,
            )
        except TimeoutError:
            self._agent_failures.add(1, {"agent_id": agent_id, "reason": "timeout"})
            return {"success": False, "agent_id": agent_id, "error": "Agent timeout"}
        finally:
            elapsed = time.perf_counter() - start
            self._agent_latency.record(elapsed, {"agent_id": agent_id})

        if result.get("success"):
            self._set_cached_result(cache_key, result)
        else:
            self._agent_failures.add(
                1, {"agent_id": agent_id, "reason": result.get("error", "unknown")}
            )
        return result

    async def _invoke_with_retries(
        self,
        *,
        agent_id: str,
        endpoint: str | None,
        payload: dict[str, Any],
        correlation_id: str,
        parameters: dict[str, Any],
        tenant_id: str,
        action: str | None,
    ) -> dict[str, Any]:
        attempt = 0
        last_error: str | None = None
        request_start = time.perf_counter()
        while attempt <= self.max_retries:
            try:
                self._emit_audit_event(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    action="orchestration.agent.invoked",
                    outcome="success",
                    metadata={"agent_id": agent_id, "attempt": attempt + 1},
                )
                if endpoint:
                    self.logger.info(
                        "Invoking agent via HTTP: %s -> %s",
                        agent_id,
                        endpoint,
                        extra={"agent_id": agent_id, "endpoint": endpoint},
                    )
                    headers = inject_trace_headers({})
                    headers["X-Correlation-ID"] = correlation_id
                    response = await self.http_client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                elif agent_id in self.agent_registry:
                    agent_payload = {
                        "action": action,
                        **parameters,
                        "context": {
                            "tenant_id": tenant_id,
                            "correlation_id": correlation_id,
                        },
                    }
                    self.logger.info("Invoking agent locally", extra={"agent_id": agent_id})
                    data = await self.agent_registry[agent_id].execute(agent_payload)
                    if isinstance(data, dict) and data.get("success") is False:
                        raise RuntimeError(data.get("error") or "Local agent execution failed")
                else:
                    self.logger.info(
                        "Invoking agent via event bus: %s", agent_id, extra={"agent_id": agent_id}
                    )
                    data = {
                        "message": f"Event published for {agent_id}",
                        "parameters": parameters,
                        "correlation_id": correlation_id,
                    }
                    await self.event_bus.publish(
                        "agent.requested",
                        {
                            "agent_id": agent_id,
                            "payload": payload,
                            "correlation_id": correlation_id,
                        },
                    )

                result = {
                    "success": True,
                    "agent_id": agent_id,
                    "data": data,
                    "duration_seconds": time.perf_counter() - request_start,
                }
                await self.event_bus.publish("agent.completed", result)
                self._failure_counts[agent_id] = 0
                self._circuit_open_until.pop(agent_id, None)
                return result
            except (httpx.TimeoutException, TimeoutError):
                last_error = "Agent timeout"
                self.logger.warning("Agent %s timed out", agent_id, extra={"agent_id": agent_id})
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as e:
                last_error = str(e)
                self.logger.error(
                    "Error invoking agent %s: %s", agent_id, e, extra={"agent_id": agent_id}
                )

            attempt += 1
            if attempt <= self.max_retries:
                backoff = min(
                    self.retry_backoff_base * (2 ** (attempt - 1)), self.retry_backoff_max
                )
                if backoff > 0:
                    await asyncio.sleep(backoff)

        failure_count = self._failure_counts.get(agent_id, 0) + 1
        self._failure_counts[agent_id] = failure_count
        if failure_count >= self.circuit_breaker_threshold:
            self._circuit_open_until[agent_id] = time.time() + self._circuit_half_open_window
        error_result = {"success": False, "agent_id": agent_id, "error": last_error or "Error"}
        await self.event_bus.publish("agent.failed", error_result)
        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="orchestration.agent.invoked",
            outcome="failure",
            metadata={"agent_id": agent_id, "error": last_error},
        )
        return error_result

    def _is_circuit_open(self, agent_id: str) -> bool:
        if not self.circuit_breaker_threshold:
            return False
        if self._failure_counts.get(agent_id, 0) < self.circuit_breaker_threshold:
            return False
        open_until = self._circuit_open_until.get(agent_id, 0.0)
        if time.time() >= open_until:
            # Half-open: allow one probe request through to test recovery
            self._failure_counts[agent_id] = self.circuit_breaker_threshold - 1
            self.logger.info("circuit_breaker_half_open", extra={"agent_id": agent_id})
            return False
        return True

    def _emit_audit_event(
        self,
        *,
        tenant_id: str,
        correlation_id: str,
        action: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        merged_metadata = dict(metadata or {})
        for key in ("plan_id", "version"):
            if key in self._current_plan_context and key not in merged_metadata:
                merged_metadata[key] = self._current_plan_context[key]
        event = build_audit_event(
            tenant_id=tenant_id,
            action=action,
            outcome=outcome,
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=self.agent_id,
            resource_type="orchestration",
            metadata=merged_metadata,
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    def _build_agent_activity(
        self, results: list[dict[str, Any]], execution_start: float
    ) -> list[dict[str, Any]]:
        activity: list[dict[str, Any]] = []
        cursor = execution_start
        for result in results:
            duration_seconds = float(result.get("duration_seconds", 0.001) or 0.001)
            if duration_seconds <= 0:
                duration_seconds = 0.001
            started_at = cursor
            completed_at = started_at + duration_seconds
            cursor = completed_at
            activity.append(
                {
                    "agent_id": result.get("agent_id", "unknown"),
                    "started_at": (
                        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(started_at))
                        + f".{int((started_at % 1) * 1000):03d}Z"
                    ),
                    "completed_at": (
                        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(completed_at))
                        + f".{int((completed_at % 1) * 1000):03d}Z"
                    ),
                    "duration_ms": int(duration_seconds * 1000),
                    "status": "success" if result.get("success") else "failed",
                }
            )
        return activity

    async def _aggregate_responses(
        self, results: list[dict[str, Any]]
    ) -> Union[str, dict[str, Any]]:
        """
        Aggregate multiple agent responses into coherent output.

        Returns a dict keyed by agent_id containing each agent's raw response data,
        or an error string if all agents failed.
        """
        successful_results = [r for r in results if r.get("success")]

        if not successful_results:
            return "Unable to process request - all agents failed"

        return {
            r.get("agent_id", "unknown"): r.get("data") or {}
            for r in successful_results
        }

    def _initialize_cache_backend(self) -> None:
        if (
            self.cache_backend
            and hasattr(self.cache_backend, "get")
            and hasattr(self.cache_backend, "set")
        ):
            self.logger.info("Cache backend configured", extra={"backend": str(self.cache_backend)})
        else:
            self.cache_backend = None

    def _load_agent_registry(self) -> None:
        if self.agent_registry_loader:
            try:
                loaded = self.agent_registry_loader()
                if isinstance(loaded, dict):
                    self.agent_registry.update(loaded)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # pragma: no cover - defensive
                self.logger.warning("Agent registry loader failed", exc_info=exc)
        if self.agent_registry_path:
            try:
                registry_payload = json.loads(Path(self.agent_registry_path).read_text())
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # pragma: no cover - defensive
                self.logger.warning("Agent registry path could not be read", exc_info=exc)
                return
            if isinstance(registry_payload, dict):
                self.agent_endpoints.update(registry_payload.get("agent_endpoints", {}))

    def _cache_key(
        self, agent_id: str, action: str | None, parameters: dict[str, Any], tenant_id: str
    ) -> str:
        payload = {
            "agent_id": agent_id,
            "action": action,
            "parameters": parameters,
            "tenant_id": tenant_id,
        }
        return json.dumps(payload, sort_keys=True, default=str)

    def _get_cached_result(self, cache_key: str) -> dict[str, Any] | None:
        if self.cache_backend:
            try:
                cached = self.cache_backend.get(cache_key)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):  # pragma: no cover - defensive
                cached = None
            if cached:
                self._cache_hits.add(1)
                return cached
            self._cache_misses.add(1)
            return None
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        expires_at, result = cached
        if time.time() > expires_at:
            self._cache.pop(cache_key, None)
            return None
        return result

    def _set_cached_result(self, cache_key: str, result: dict[str, Any]) -> None:
        if self.cache_backend:
            try:
                self.cache_backend.set(cache_key, result, ttl=self.cache_ttl)
                return
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):  # pragma: no cover - defensive
                pass
        if self.cache_max_entries and len(self._cache) >= self.cache_max_entries:
            self._cache.pop(next(iter(self._cache)), None)
        self._cache[cache_key] = (time.time() + self.cache_ttl, result)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Response Orchestration Agent...")
        if self.http_client is not None:
            await self.http_client.aclose()

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities."""
        return [
            "multi_agent_orchestration",
            "parallel_execution",
            "sequential_execution",
            "response_aggregation",
            "timeout_management",
            "result_caching",
        ]
