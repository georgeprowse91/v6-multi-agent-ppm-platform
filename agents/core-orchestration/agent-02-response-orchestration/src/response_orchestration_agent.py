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
from typing import Any, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agents.common.web_search import (
    SearchPurpose,
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent, InMemoryEventBus
from agents.runtime.src.audit import build_audit_event, emit_audit_event

OBSERVABILITY_ROOT = Path(__file__).resolve().parents[5] / "packages" / "observability" / "src"
if str(OBSERVABILITY_ROOT) not in sys.path:
    sys.path.insert(0, str(OBSERVABILITY_ROOT))

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
    parameters: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    context: dict[str, Any] | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None
    prompt_id: str | None = None
    prompt_description: str | None = None
    prompt_tags: list[str] = Field(default_factory=list)


class AgentInvocationResult(BaseModel):
    success: bool
    agent_id: str
    data: dict[str, Any] | None = None
    error: str | None = None
    cached: bool = False


class OrchestrationResponse(BaseModel):
    aggregated_response: str
    agent_results: list[AgentInvocationResult]
    execution_summary: dict[str, Any]


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
        self, agent_id: str = "response-orchestration", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)
        self.max_concurrency = config.get("max_concurrency", 5) if config else 5
        self.agent_timeout = config.get("agent_timeout", 30) if config else 30
        self.cache_ttl = config.get("cache_ttl", 900) if config else 900  # 15 minutes
        self.cache_max_entries = config.get("cache_max_entries", 256) if config else 256
        self.agent_endpoints = config.get("agent_endpoints", {}) if config else {}
        self.max_retries = config.get("max_retries", 2) if config else 2
        self.retry_backoff_base = config.get("retry_backoff_base", 0.5) if config else 0.5
        self.retry_backoff_max = config.get("retry_backoff_max", 5.0) if config else 5.0
        self.circuit_breaker_threshold = config.get("circuit_breaker_threshold", 3) if config else 3
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = InMemoryEventBus()
        self.http_client = config.get("http_client") if config else None
        self.agent_registry: dict[str, BaseAgent] = (
            config.get("agent_registry", {}) if config else {}
        )
        self._failure_counts: dict[str, int] = {}
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._last_validation_error: dict[str, Any] | None = None
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
        # Future work: Initialize cache (Redis)
        # Future work: Load agent registry
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=self.agent_timeout)

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
        except Exception as exc:  # pragma: no cover - defensive
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

        if not routing:
            return OrchestrationResponse(
                aggregated_response="No agents to invoke",
                agent_results=[],
                execution_summary={"total_agents": 0},
            )

        # Build dependency graph
        execution_plan = await self._build_execution_plan(routing)

        # Execute agents according to plan
        results = await self._execute_plan(
            execution_plan,
            parameters,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )

        # Aggregate responses
        aggregated = await self._aggregate_responses(results)
        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="orchestration.aggregated",
            outcome="success",
            metadata={
                "agent_count": len(routing),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
            },
        )

        response = OrchestrationResponse(
            aggregated_response=aggregated,
            agent_results=[AgentInvocationResult(**result) for result in results],
            execution_summary={
                "total_agents": len(routing),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
            },
        )
        return response

    async def _build_execution_plan(self, routing: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build execution plan determining parallel vs sequential execution.

        Returns execution plan with dependency graph.
        """
        nodes = {item["agent_id"]: dict(item) for item in routing}
        dependencies = {
            agent_id: set(item.get("depends_on") or []) for agent_id, item in nodes.items()
        }
        for agent_id, deps in dependencies.items():
            dependencies[agent_id] = {dep for dep in deps if dep in nodes and dep != agent_id}

        plan: list[list[dict[str, Any]]] = []
        remaining = set(nodes.keys())
        while remaining:
            ready = sorted(agent_id for agent_id in remaining if not dependencies[agent_id])
            if not ready:
                raise ValueError("Dependency cycle detected in routing plan")
            group = [nodes[agent_id] for agent_id in ready]
            plan.append(group)
            remaining -= set(ready)
            for agent_id in remaining:
                dependencies[agent_id] -= set(ready)

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

        return results

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
                    self.logger.info(f"Invoking agent via HTTP: {agent_id} -> {endpoint}")
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
                    self.logger.info(f"Invoking agent via event bus: {agent_id}")
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

                result = {"success": True, "agent_id": agent_id, "data": data}
                await self.event_bus.publish("agent.completed", result)
                self._failure_counts[agent_id] = 0
                return result
            except (httpx.TimeoutException, TimeoutError):
                last_error = "Agent timeout"
                self.logger.warning(f"Agent {agent_id} timed out")
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Error invoking agent {agent_id}: {str(e)}")

            attempt += 1
            if attempt <= self.max_retries:
                backoff = min(
                    self.retry_backoff_base * (2 ** (attempt - 1)), self.retry_backoff_max
                )
                if backoff > 0:
                    await asyncio.sleep(backoff)

        self._failure_counts[agent_id] = self._failure_counts.get(agent_id, 0) + 1
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
        return self._failure_counts.get(agent_id, 0) >= self.circuit_breaker_threshold

    def _emit_audit_event(
        self,
        *,
        tenant_id: str,
        correlation_id: str,
        action: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = build_audit_event(
            tenant_id=tenant_id,
            action=action,
            outcome=outcome,
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=self.agent_id,
            resource_type="orchestration",
            metadata=metadata or {},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    async def _aggregate_responses(self, results: list[dict[str, Any]]) -> str:
        """
        Aggregate multiple agent responses into coherent output.

        Returns aggregated response string.
        """
        # Future work: Use Azure OpenAI for intelligent summarization
        successful_results = [r for r in results if r.get("success")]

        if not successful_results:
            return "Unable to process request - all agents failed"

        # Simple concatenation for now
        responses = []
        for result in successful_results:
            agent_id = result.get("agent_id", "unknown")
            data = result.get("data", {})
            if isinstance(data, dict):
                message = data.get("message")
                if message is None and "data" in data:
                    message = json.dumps(data.get("data"), default=str)
            else:
                message = str(data)
            if not message:
                message = "No response"
            responses.append(f"[{agent_id}]: {message}")

        return "\n".join(responses)

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
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        expires_at, result = cached
        if time.time() > expires_at:
            self._cache.pop(cache_key, None)
            return None
        return result

    def _set_cached_result(self, cache_key: str, result: dict[str, Any]) -> None:
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
