"""
Agent 2: Response Orchestration Agent

Purpose:
Coordinates multi-agent queries, manages parallel/sequential execution,
and aggregates responses into coherent outputs.

Specification: agents/core-orchestration/agent-02-response-orchestration/README.md
"""

import asyncio
from typing import Any, cast

import httpx

from agents.runtime import BaseAgent, InMemoryEventBus


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
        self.agent_endpoints = config.get("agent_endpoints", {}) if config else {}
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = InMemoryEventBus()
        self.http_client = config.get("http_client") if config else None

    async def initialize(self) -> None:
        """Initialize orchestration engine and cache."""
        await super().initialize()
        self.logger.info("Initializing orchestration engine...")
        # Future work: Initialize cache (Redis)
        # Future work: Load agent registry
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=self.agent_timeout)

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
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
        routing = input_data.get("routing", [])
        parameters = input_data.get("parameters", {})

        if not routing:
            return {
                "aggregated_response": "No agents to invoke",
                "agent_results": [],
                "execution_summary": {"total_agents": 0},
            }

        # Build dependency graph
        execution_plan = await self._build_execution_plan(routing)

        # Execute agents according to plan
        results = await self._execute_plan(execution_plan, parameters)

        # Aggregate responses
        aggregated = await self._aggregate_responses(results)

        return {
            "aggregated_response": aggregated,
            "agent_results": results,
            "execution_summary": {
                "total_agents": len(routing),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
            },
        }

    async def _build_execution_plan(self, routing: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build execution plan determining parallel vs sequential execution.

        Returns execution plan with dependency graph.
        """
        # Future work: Implement dependency analysis
        # For now, assume all agents can run in parallel
        return {
            "parallel_groups": [routing],
            "sequential_steps": [],
        }

    async def _execute_plan(
        self, execution_plan: dict[str, Any], parameters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Execute the plan, invoking agents in parallel or sequentially.

        Returns list of agent results.
        """
        results: list[dict[str, Any]] = []

        # Execute parallel groups
        for group in execution_plan.get("parallel_groups", []):
            group_results = await self._execute_parallel(group, parameters)
            results.extend(group_results)

        return results

    async def _execute_parallel(
        self, agents: list[dict[str, Any]], parameters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Execute multiple agents in parallel.

        Returns list of results from all agents.
        """
        tasks = []
        for agent_info in agents[: self.max_concurrency]:
            task = self._invoke_agent(agent_info, parameters)
            tasks.append(task)

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
        self, agent_info: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Invoke a single agent with timeout.

        Returns agent result or error.
        """
        assert self.http_client is not None
        assert self.event_bus is not None
        agent_id = agent_info["agent_id"]

        endpoint = agent_info.get("endpoint") or self.agent_endpoints.get(agent_id)
        payload = {"agent_id": agent_id, "parameters": parameters}

        try:
            if endpoint:
                self.logger.info(f"Invoking agent via HTTP: {agent_id} -> {endpoint}")
                response = await self.http_client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
            else:
                self.logger.info(f"Invoking agent via event bus: {agent_id}")
                data = {
                    "message": f"Event published for {agent_id}",
                    "parameters": parameters,
                }
                await self.event_bus.publish(
                    "agent.requested",
                    {"agent_id": agent_id, "payload": payload},
                )

            result = {"success": True, "agent_id": agent_id, "data": data}
            await self.event_bus.publish("agent.completed", result)
            return result

        except (httpx.TimeoutException, TimeoutError):
            self.logger.warning(f"Agent {agent_id} timed out")
            error_result = {"success": False, "agent_id": agent_id, "error": "Agent timeout"}
            await self.event_bus.publish("agent.failed", error_result)
            return error_result
        except Exception as e:
            self.logger.error(f"Error invoking agent {agent_id}: {str(e)}")
            error_result = {"success": False, "agent_id": agent_id, "error": str(e)}
            await self.event_bus.publish("agent.failed", error_result)
            return error_result

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
            message = data.get("message", "No response")
            responses.append(f"[{agent_id}]: {message}")

        return "\n".join(responses)

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
