"""
PPM Agent SDK — Public SDK for building custom agents.

This package provides the base classes, manifest validation, and testing
utilities needed to build third-party agents for the PPM Agent Marketplace.

Quick start::

    from agent_sdk import CustomAgent, AgentManifest, AgentContext

    class MyAgent(CustomAgent):
        def get_manifest(self) -> AgentManifest:
            return AgentManifest(
                agent_id="my-custom-agent",
                display_name="My Custom Agent",
                version="1.0.0",
                description="Does something useful for project managers.",
                author={"name": "My Company"},
                category="custom",
                entry_point={"module": "my_agent", "class_name": "MyAgent"},
                capabilities=["my_capability"],
            )

        async def process(self, input_data: dict) -> dict:
            return {"message": "Hello from my agent", "status": "completed"}
"""

from agent_sdk.src.context import AgentContext
from agent_sdk.src.custom_agent import CustomAgent
from agent_sdk.src.manifest import AgentManifest, validate_manifest
from agent_sdk.src.sandbox import SandboxRunner
from agent_sdk.src.testing import AgentTestHarness

__all__ = [
    "CustomAgent",
    "AgentManifest",
    "AgentContext",
    "SandboxRunner",
    "AgentTestHarness",
    "validate_manifest",
]
