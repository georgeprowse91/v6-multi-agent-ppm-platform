from __future__ import annotations

import json

import pytest

from llm.client import LLMGateway, LLMProviderError, LLMResponse, LLMStreamChunk, ProviderAdapter


class StubAdapter(ProviderAdapter):
    def __init__(self, name: str, responses: list[object]) -> None:
        self.name = name
        self.responses = responses
        self.calls = 0

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls += 1
        item = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return LLMResponse(content=str(item), raw={"content": str(item)}, provider=self.name)

    async def stream(self, *, system_prompt: str, user_prompt: str):
        self.calls += 1
        yield LLMStreamChunk(index=0, delta=f"{self.name}-chunk", raw={}, done=False)
        yield LLMStreamChunk(index=1, delta="", raw={}, done=True)


@pytest.mark.anyio
async def test_failover_uses_ordered_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    gateway = LLMGateway(config={"provider_chain": ["mock", "openai"], "retry_policy": {"max_attempts": 1}})
    primary = StubAdapter("mock", [LLMProviderError("retry", retryable=True, provider="mock")])
    fallback = StubAdapter("openai", ["fallback-ok"])
    gateway.adapters = {"mock": primary, "openai": fallback}

    response = await gateway.complete("sys", "user")

    assert response.content == "fallback-ok"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.anyio
async def test_stream_yields_chunks() -> None:
    gateway = LLMGateway(config={"provider_chain": ["mock"]})
    gateway.adapters = {"mock": StubAdapter("mock", ["ignored"])}

    chunks = [chunk async for chunk in gateway.stream("sys", "user")]

    assert [chunk.delta for chunk in chunks] == ["mock-chunk", ""]
    assert chunks[-1].done is True


@pytest.mark.anyio
async def test_semantic_cache_hit_and_miss_hooks() -> None:
    events: list[tuple[str, str]] = []
    gateway = LLMGateway(
        config={
            "provider_chain": ["mock"],
            "semantic_cache": {
                "ttl_seconds": 60,
                "on_hit": lambda tenant, key: events.append(("hit", tenant)),
                "on_miss": lambda tenant, key: events.append(("miss", tenant)),
            },
        }
    )
    adapter = StubAdapter("mock", ["cached response"])
    gateway.adapters = {"mock": adapter}

    first = await gateway.complete("S y s", "User prompt", tenant_id="tenant-a")
    second = await gateway.complete("s   y s", "user  prompt", tenant_id="tenant-a")

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert adapter.calls == 1
    assert events[0] == ("miss", "tenant-a")
    assert events[-1] == ("hit", "tenant-a")


@pytest.mark.anyio
async def test_structured_output_retries_on_malformed_json() -> None:
    gateway = LLMGateway(config={"provider_chain": ["mock"]})
    adapter = StubAdapter("mock", ["not-json", json.dumps({"name": "ok"})])
    gateway.adapters = {"mock": adapter}

    payload = await gateway.complete_structured(
        system_prompt="sys",
        user_prompt="user",
        schema={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
    )

    assert payload == {"name": "ok"}
    assert adapter.calls == 2


@pytest.mark.anyio
async def test_token_budget_denial() -> None:
    gateway = LLMGateway(
        config={
            "provider_chain": ["mock"],
            "token_budgets": {"tenant-a": 2},
            "mock_response": "hello from mock",
        }
    )

    with pytest.raises(LLMProviderError, match="Token budget exceeded"):
        await gateway.complete("system prompt", "user prompt", tenant_id="tenant-a")
