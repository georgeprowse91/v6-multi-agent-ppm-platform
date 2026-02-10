"""
Tests for Base Agent functionality
"""

import pytest

from agents.runtime import AgentResponse, BaseAgent


class SampleAgent(BaseAgent):
    """Test agent implementation."""

    async def process(self, input_data: dict) -> dict:
        """Simple test processing."""
        return {"result": "processed", "input": input_data}


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization."""
    agent = SampleAgent(agent_id="test-agent", config={"test": "config"})

    assert agent.agent_id == "test-agent"
    assert agent.config == {"test": "config"}
    assert not agent.initialized

    await agent.initialize()

    assert agent.initialized


@pytest.mark.asyncio
async def test_agent_execute():
    """Test agent execute method."""
    agent = SampleAgent(agent_id="test-agent")

    result = await agent.execute({"data": "test"})
    validated = AgentResponse.model_validate(result)

    assert validated.success is True
    assert validated.data is not None
    assert validated.data.model_dump()["result"] == "processed"
    assert validated.metadata.agent_id == "test-agent"
    assert validated.metadata.catalog_id == "test-agent"
    assert validated.metadata.correlation_id
    assert validated.metadata.trace_id


@pytest.mark.asyncio
async def test_agent_validation():
    """Test agent input validation."""

    class ValidatingAgent(BaseAgent):
        async def validate_input(self, input_data: dict) -> bool:
            return "required_field" in input_data

        async def process(self, input_data: dict) -> dict:
            return {"result": "ok"}

    agent = ValidatingAgent(agent_id="validating-agent")

    # Should fail validation
    result = await agent.execute({})
    validated = AgentResponse.model_validate(result)
    assert validated.success is False
    assert "validation" in (validated.error or "").lower()

    # Should pass validation
    result = await agent.execute({"required_field": "value"})
    validated = AgentResponse.model_validate(result)
    assert validated.success is True


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling."""

    class ErrorAgent(BaseAgent):
        async def process(self, input_data: dict) -> dict:
            raise ValueError("Test error")

    agent = ErrorAgent(agent_id="error-agent")

    result = await agent.execute({"data": "test"})
    validated = AgentResponse.model_validate(result)

    assert validated.success is False
    assert "Test error" in (validated.error or "")
    assert validated.metadata.agent_id == "error-agent"


def test_agent_get_capabilities():
    """Test getting agent capabilities."""

    class CapableAgent(BaseAgent):
        async def process(self, input_data: dict) -> dict:
            return {}

        def get_capabilities(self) -> list:
            return ["capability1", "capability2"]

    agent = CapableAgent(agent_id="capable-agent")

    capabilities = agent.get_capabilities()
    assert "capability1" in capabilities
    assert "capability2" in capabilities


def test_agent_get_config():
    """Test getting configuration values."""
    agent = SampleAgent(agent_id="test-agent", config={"setting1": "value1", "setting2": 42})

    assert agent.get_config("setting1") == "value1"
    assert agent.get_config("setting2") == 42
    assert agent.get_config("nonexistent", "default") == "default"


@pytest.mark.asyncio
async def test_agent_rejects_invalid_payload_type():
    """Ensure agent responses always validate against the contract."""

    class BadPayloadAgent(BaseAgent):
        async def process(self, input_data: dict) -> list:
            return ["not", "a", "dict"]

    agent = BadPayloadAgent(agent_id="bad-payload")
    result = await agent.execute({"data": "test"})
    validated = AgentResponse.model_validate(result)
    assert validated.success is False
    assert validated.error is not None


class StubMemoryClient:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def save_context(self, key: str, data: dict) -> None:
        self.store[key] = dict(data)

    def load_context(self, key: str) -> dict | None:
        return self.store.get(key)

    def delete_context(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_agent_memory_helpers_use_scoped_keys():
    memory_client = StubMemoryClient()
    agent = SampleAgent(agent_id="memory-agent", memory_client=memory_client)

    agent.save_context("conversation-1", {"a": 1})

    assert memory_client.load_context("conversation-1:memory-agent") == {"a": 1}
    assert agent.load_context("conversation-1") == {"a": 1}
