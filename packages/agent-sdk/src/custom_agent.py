"""CustomAgent — public base class for third-party marketplace agents."""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from agent_sdk.src.context import AgentContext
from agent_sdk.src.manifest import AgentManifest

logger = logging.getLogger(__name__)


class CustomAgent:
    """Base class for custom marketplace agents.

    Third-party developers extend this class to create agents that can be
    published to and installed from the PPM Agent Marketplace.

    Subclasses **must** implement:
        - ``get_manifest()`` — return the agent's manifest metadata
        - ``process(input_data)`` — perform the agent's core logic

    Optionally override:
        - ``initialize()`` — one-time setup (DB connections, model loading)
        - ``validate_input(input_data)`` — input validation
        - ``cleanup()`` — release resources on shutdown
        - ``get_capabilities()`` — declare runtime capabilities
        - ``health_check()`` — report agent health

    Example::

        class MyAgent(CustomAgent):
            def get_manifest(self) -> AgentManifest:
                return AgentManifest(...)

            async def process(self, input_data: dict) -> dict:
                ctx = AgentContext.from_input_data(input_data)
                return {"result": "done", "tenant": ctx.tenant_id}
    """

    def __init__(self, agent_id: str, config: dict[str, Any] | None = None) -> None:
        self.agent_id = agent_id
        self.config = config or {}
        self.initialized = False
        self.logger = logging.getLogger(f"agent.custom.{agent_id}")

    @abstractmethod
    def get_manifest(self) -> AgentManifest:
        """Return the agent manifest describing this agent's metadata."""
        ...

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's core logic.

        Args:
            input_data: Input data dict. Use ``AgentContext.from_input_data()``
                to extract the runtime context.

        Returns:
            Result dictionary. Must be JSON-serializable.
        """
        ...

    async def initialize(self) -> None:
        """One-time initialization hook. Called before first ``process()``."""
        self.initialized = True

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input before processing. Return False to reject.

        Default implementation always returns True.
        """
        return True

    async def cleanup(self) -> None:
        """Cleanup hook called on agent shutdown."""
        pass

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides."""
        manifest = self.get_manifest()
        return list(manifest.capabilities)

    async def health_check(self) -> dict[str, Any]:
        """Return agent health status.

        Returns:
            Dict with at least ``{"healthy": bool}``.
        """
        return {"healthy": self.initialized, "agent_id": self.agent_id}

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def build_context(self, input_data: dict[str, Any]) -> AgentContext:
        """Convenience method to build an AgentContext from input data."""
        return AgentContext.from_input_data(input_data)
