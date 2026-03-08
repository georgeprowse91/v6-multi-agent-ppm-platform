"""Sandbox runner for testing custom agents in an isolated environment."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from agent_sdk.src.custom_agent import CustomAgent
from agent_sdk.src.manifest import AgentManifest, validate_manifest

logger = logging.getLogger(__name__)


class SandboxResult:
    """Result of a sandbox agent execution."""

    def __init__(
        self,
        *,
        success: bool,
        output: dict[str, Any] | None = None,
        error: str | None = None,
        execution_time_seconds: float = 0.0,
        validation_passed: bool = True,
        manifest_valid: bool = True,
        manifest_errors: list[str] | None = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time_seconds = execution_time_seconds
        self.validation_passed = validation_passed
        self.manifest_valid = manifest_valid
        self.manifest_errors = manifest_errors or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "validation_passed": self.validation_passed,
            "manifest_valid": self.manifest_valid,
            "manifest_errors": self.manifest_errors,
        }


class SandboxRunner:
    """Run custom agents in a controlled sandbox environment.

    The sandbox validates the agent manifest, enforces execution timeouts,
    and captures errors without affecting the host platform.

    Example::

        runner = SandboxRunner(timeout_seconds=30)
        result = await runner.run(my_agent, {"query": "test"})
        if result.success:
            print(result.output)
    """

    def __init__(self, *, timeout_seconds: int = 60, enforce_permissions: bool = True):
        self.timeout_seconds = timeout_seconds
        self.enforce_permissions = enforce_permissions

    async def validate_agent(self, agent: CustomAgent) -> SandboxResult:
        """Validate an agent's manifest and readiness without executing it."""
        try:
            manifest = agent.get_manifest()
        except Exception as exc:
            return SandboxResult(
                success=False,
                manifest_valid=False,
                manifest_errors=[f"get_manifest() failed: {exc}"],
            )

        manifest_data = manifest.model_dump() if isinstance(manifest, AgentManifest) else manifest
        is_valid, errors = validate_manifest(manifest_data)
        if not is_valid:
            return SandboxResult(
                success=False,
                manifest_valid=False,
                manifest_errors=errors,
            )

        return SandboxResult(success=True, manifest_valid=True)

    async def run(
        self,
        agent: CustomAgent,
        input_data: dict[str, Any],
    ) -> SandboxResult:
        """Execute an agent in the sandbox with timeout enforcement.

        Args:
            agent: The custom agent instance to run.
            input_data: Input data to pass to the agent.

        Returns:
            SandboxResult with execution outcome.
        """
        # Validate manifest first
        validation = await self.validate_agent(agent)
        if not validation.manifest_valid:
            return validation

        # Check timeout from manifest
        manifest = agent.get_manifest()
        timeout = self.timeout_seconds
        if isinstance(manifest, AgentManifest) and manifest.runtime:
            runtime = manifest.runtime
            if isinstance(runtime, dict):
                timeout = min(timeout, runtime.get("timeout_seconds", timeout))
            else:
                timeout = min(timeout, runtime.timeout_seconds)

        # Initialize if needed
        if not agent.initialized:
            try:
                await agent.initialize()
            except Exception as exc:
                return SandboxResult(
                    success=False,
                    error=f"Agent initialization failed: {exc}",
                )

        # Validate input
        try:
            validation_passed = await agent.validate_input(input_data)
            if not validation_passed:
                return SandboxResult(
                    success=False,
                    error="Input validation failed",
                    validation_passed=False,
                )
        except Exception as exc:
            return SandboxResult(
                success=False,
                error=f"Input validation error: {exc}",
                validation_passed=False,
            )

        # Execute with timeout
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                agent.process(input_data),
                timeout=timeout,
            )
            elapsed = time.monotonic() - start
            return SandboxResult(
                success=True,
                output=result,
                execution_time_seconds=round(elapsed, 3),
            )
        except TimeoutError:
            elapsed = time.monotonic() - start
            return SandboxResult(
                success=False,
                error=f"Agent execution timed out after {timeout}s",
                execution_time_seconds=round(elapsed, 3),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return SandboxResult(
                success=False,
                error=f"Agent execution error: {exc}",
                execution_time_seconds=round(elapsed, 3),
            )
