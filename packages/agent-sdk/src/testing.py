"""Testing utilities for custom agent development."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent_sdk.src.context import AgentContext
from agent_sdk.src.custom_agent import CustomAgent
from agent_sdk.src.manifest import AgentManifest, validate_manifest
from agent_sdk.src.sandbox import SandboxResult, SandboxRunner

logger = logging.getLogger(__name__)


class AgentTestHarness:
    """Test harness for validating custom agents before marketplace submission.

    Runs a battery of checks including manifest validation, input/output
    contract verification, health checks, and sandboxed execution.

    Example::

        harness = AgentTestHarness(my_agent)
        report = await harness.run_all_checks(
            sample_inputs=[{"query": "test", "context": {"tenant_id": "t1"}}]
        )
        for check in report["checks"]:
            print(f"{check['name']}: {'PASS' if check['passed'] else 'FAIL'}")
    """

    def __init__(self, agent: CustomAgent, *, timeout_seconds: int = 30):
        self.agent = agent
        self.timeout_seconds = timeout_seconds
        self.sandbox = SandboxRunner(timeout_seconds=timeout_seconds)

    async def check_manifest(self) -> dict[str, Any]:
        """Validate the agent manifest."""
        try:
            manifest = self.agent.get_manifest()
        except Exception as exc:
            return {
                "name": "manifest_valid",
                "passed": False,
                "message": f"get_manifest() raised: {exc}",
            }

        if isinstance(manifest, AgentManifest):
            data = manifest.model_dump()
        else:
            data = manifest

        is_valid, errors = validate_manifest(data)
        return {
            "name": "manifest_valid",
            "passed": is_valid,
            "message": "Manifest is valid" if is_valid else f"Manifest errors: {errors}",
            "errors": errors,
        }

    async def check_capabilities(self) -> dict[str, Any]:
        """Verify capabilities are declared."""
        try:
            caps = self.agent.get_capabilities()
            has_caps = len(caps) > 0
            return {
                "name": "capabilities_declared",
                "passed": has_caps,
                "message": f"Agent declares {len(caps)} capabilities" if has_caps else "No capabilities declared",
                "capabilities": caps,
            }
        except Exception as exc:
            return {
                "name": "capabilities_declared",
                "passed": False,
                "message": f"get_capabilities() raised: {exc}",
            }

    async def check_initialization(self) -> dict[str, Any]:
        """Verify the agent can initialize successfully."""
        try:
            await self.agent.initialize()
            return {
                "name": "initialization",
                "passed": self.agent.initialized,
                "message": "Agent initialized successfully" if self.agent.initialized else "Agent did not set initialized=True",
            }
        except Exception as exc:
            return {
                "name": "initialization",
                "passed": False,
                "message": f"initialize() raised: {exc}",
            }

    async def check_health(self) -> dict[str, Any]:
        """Verify the agent health check works."""
        try:
            health = await self.agent.health_check()
            healthy = health.get("healthy", False)
            return {
                "name": "health_check",
                "passed": healthy,
                "message": "Health check passed" if healthy else "Health check reports unhealthy",
                "health": health,
            }
        except Exception as exc:
            return {
                "name": "health_check",
                "passed": False,
                "message": f"health_check() raised: {exc}",
            }

    async def check_execution(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the agent with sample input in the sandbox."""
        result = await self.sandbox.run(self.agent, input_data)
        return {
            "name": "sandbox_execution",
            "passed": result.success,
            "message": "Execution succeeded" if result.success else f"Execution failed: {result.error}",
            "execution_time_seconds": result.execution_time_seconds,
            "output": result.output,
        }

    async def check_cleanup(self) -> dict[str, Any]:
        """Verify cleanup runs without error."""
        try:
            await self.agent.cleanup()
            return {
                "name": "cleanup",
                "passed": True,
                "message": "Cleanup succeeded",
            }
        except Exception as exc:
            return {
                "name": "cleanup",
                "passed": False,
                "message": f"cleanup() raised: {exc}",
            }

    async def run_all_checks(
        self,
        sample_inputs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run all validation checks and return a full report.

        Args:
            sample_inputs: List of sample input dicts to test execution.
                If not provided, execution checks are skipped.

        Returns:
            Report dict with ``passed`` boolean and ``checks`` list.
        """
        checks: list[dict[str, Any]] = []

        checks.append(await self.check_manifest())
        checks.append(await self.check_capabilities())
        checks.append(await self.check_initialization())
        checks.append(await self.check_health())

        if sample_inputs:
            for i, input_data in enumerate(sample_inputs):
                result = await self.check_execution(input_data)
                result["name"] = f"sandbox_execution_{i}"
                checks.append(result)

        checks.append(await self.check_cleanup())

        all_passed = all(c["passed"] for c in checks)
        return {
            "agent_id": self.agent.agent_id,
            "passed": all_passed,
            "checks": checks,
            "total": len(checks),
            "passed_count": sum(1 for c in checks if c["passed"]),
            "failed_count": sum(1 for c in checks if not c["passed"]),
        }
