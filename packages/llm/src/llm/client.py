from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

import httpx


@dataclass
class LLMResponse:
    content: str
    raw: dict[str, Any]
    provider: str = "unknown"
    cache_hit: bool = False


@dataclass
class LLMStreamChunk:
    index: int
    delta: str
    raw: dict[str, Any]
    done: bool = False


@dataclass
class RetryPolicy:
    max_attempts: int = 2
    retryable_status_codes: tuple[int, ...] = (408, 409, 425, 429, 500, 502, 503, 504)


class LLMProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, provider: str | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class SemanticCache:
    def __init__(
        self,
        *,
        ttl_seconds: int = 300,
        embedder: Callable[[str], str] | None = None,
        on_hit: Callable[[str, str], None] | None = None,
        on_miss: Callable[[str, str], None] | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.embedder = embedder
        self.on_hit = on_hit
        self.on_miss = on_miss
        self._store: dict[str, tuple[float, LLMResponse]] = {}

    @staticmethod
    def normalize_query(text: str) -> str:
        text = text.lower().strip()
        return re.sub(r"\s+", " ", text)

    def _key(self, *, tenant_id: str, system_prompt: str, user_prompt: str) -> str:
        normalized = "\n".join(
            [
                self.normalize_query(system_prompt),
                self.normalize_query(user_prompt),
            ]
        )
        semantic_fingerprint = self.embedder(normalized) if self.embedder else normalized
        key_material = f"{tenant_id}:{semantic_fingerprint}".encode("utf-8")
        return sha256(key_material).hexdigest()

    def get(self, *, tenant_id: str, system_prompt: str, user_prompt: str) -> LLMResponse | None:
        key = self._key(tenant_id=tenant_id, system_prompt=system_prompt, user_prompt=user_prompt)
        entry = self._store.get(key)
        now = time.time()
        if entry is None:
            if self.on_miss:
                self.on_miss(tenant_id, key)
            return None
        expires_at, response = entry
        if expires_at < now:
            self._store.pop(key, None)
            if self.on_miss:
                self.on_miss(tenant_id, key)
            return None
        if self.on_hit:
            self.on_hit(tenant_id, key)
        return LLMResponse(content=response.content, raw=dict(response.raw), provider=response.provider, cache_hit=True)

    def put(self, *, tenant_id: str, system_prompt: str, user_prompt: str, response: LLMResponse) -> None:
        key = self._key(tenant_id=tenant_id, system_prompt=system_prompt, user_prompt=user_prompt)
        self._store[key] = (time.time() + self.ttl_seconds, response)


class TokenBudgetManager:
    def __init__(self, per_tenant_limits: dict[str, int] | None = None) -> None:
        self.per_tenant_limits = per_tenant_limits or {}
        self._usage: dict[str, int] = {}

    @staticmethod
    def estimate_tokens(*texts: str) -> int:
        joined = " ".join(texts)
        words = [item for item in joined.split(" ") if item]
        return max(1, int(len(words) * 1.3))

    def ensure_budget(self, tenant_id: str, estimated_tokens: int) -> None:
        limit = self.per_tenant_limits.get(tenant_id)
        if limit is None:
            return
        used = self._usage.get(tenant_id, 0)
        if used + estimated_tokens > limit:
            raise LLMProviderError(
                f"Token budget exceeded for tenant={tenant_id}: {used + estimated_tokens}>{limit}",
                retryable=False,
                provider="budget",
            )

    def record_usage(self, tenant_id: str, usage: TokenUsage) -> None:
        self._usage[tenant_id] = self._usage.get(tenant_id, 0) + usage.total_tokens


class ProviderAdapter:
    name: str

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise NotImplementedError

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[LLMStreamChunk]:
        raise NotImplementedError


class MockProviderAdapter(ProviderAdapter):
    name = "mock"

    def __init__(self, response: Any) -> None:
        self.response = response

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        if isinstance(self.response, dict):
            content = json.dumps(self.response)
            raw = self.response
        else:
            content = str(self.response)
            raw = {"content": content}
        return LLMResponse(content=content, raw=raw, provider=self.name)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[LLMStreamChunk]:
        response = await self.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        tokens = response.content.split(" ")
        for idx, token in enumerate(tokens):
            yield LLMStreamChunk(index=idx, delta=token + (" " if idx < len(tokens) - 1 else ""), raw={}, done=False)
        yield LLMStreamChunk(index=len(tokens), delta="", raw={}, done=True)


class OpenAIProviderAdapter(ProviderAdapter):
    name = "openai"

    def __init__(self, *, api_key: str, model: str, base_url: str, timeout: float) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            self._raise_for_status(response)
            data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data, provider=self.name)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[LLMStreamChunk]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                self._raise_for_status(response)
                idx = 0
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    event = line.removeprefix("data:").strip()
                    if event == "[DONE]":
                        break
                    try:
                        payload_item = json.loads(event)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        payload_item.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    )
                    if not delta:
                        continue
                    yield LLMStreamChunk(index=idx, delta=delta, raw=payload_item, done=False)
                    idx += 1
        yield LLMStreamChunk(index=idx, delta="", raw={}, done=True)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        retryable = response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
        raise LLMProviderError(
            f"OpenAI provider failed with status={response.status_code}",
            retryable=retryable,
            provider=self.name,
        )


class AzureProviderAdapter(OpenAIProviderAdapter):
    name = "azure"

    def __init__(
        self,
        *,
        api_key: str,
        deployment: str,
        endpoint: str,
        api_version: str,
        timeout: float,
    ) -> None:
        self.api_key = api_key
        self.model = deployment
        self.base_url = endpoint.rstrip("/")
        self.deployment = deployment
        self.api_version = api_version
        self.timeout = timeout

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = (
            f"{self.base_url}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key}
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            self._raise_for_status(response)
            data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data, provider=self.name)

    async def stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[LLMStreamChunk]:
        # Azure uses the same streaming payload contract as OpenAI chat completions.
        async for chunk in super().stream(system_prompt=system_prompt, user_prompt=user_prompt):
            yield chunk


class LLMGateway:
    def __init__(self, provider: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.retry_policy = RetryPolicy(**self.config.get("retry_policy", {}))
        self.provider_chain = self._resolve_chain(provider)
        self.adapters = {name: self._build_provider(name) for name in self.provider_chain}
        self.cache = self._build_cache()
        self.budget = TokenBudgetManager(self.config.get("token_budgets"))

    def _resolve_chain(self, provider: str | None) -> list[str]:
        chain = self.config.get("provider_chain")
        if chain:
            return [str(item).lower() for item in chain]
        selected = provider or os.getenv("LLM_PROVIDER", "mock")
        fallbacks = self.config.get("fallbacks", [])
        return [selected.lower(), *[str(item).lower() for item in fallbacks]]

    def _build_provider(self, provider_name: str) -> ProviderAdapter:
        timeout = float(os.getenv("LLM_TIMEOUT", "10"))
        if provider_name == "mock":
            response = self.config.get("mock_response")
            if response is None:
                response = {"intents": [{"intent": "general_query", "confidence": 0.5}]}
            return MockProviderAdapter(response=response)
        if provider_name == "openai":
            api_key = os.getenv("LLM_API_KEY")
            if not api_key:
                raise LLMProviderError("LLM_API_KEY is required for OpenAI provider")
            return OpenAIProviderAdapter(
                api_key=api_key,
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                timeout=timeout,
            )
        if provider_name == "azure":
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("LLM_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            if not api_key or not endpoint or not deployment:
                raise LLMProviderError("Azure provider requires endpoint, deployment, and API key")
            return AzureProviderAdapter(
                api_key=api_key,
                deployment=deployment,
                endpoint=endpoint,
                api_version=api_version,
                timeout=timeout,
            )
        raise LLMProviderError(f"Unsupported LLM provider: {provider_name}")

    def _build_cache(self) -> SemanticCache | None:
        cache_cfg = self.config.get("semantic_cache")
        if not cache_cfg:
            return None
        return SemanticCache(
            ttl_seconds=int(cache_cfg.get("ttl_seconds", 300)),
            embedder=cache_cfg.get("embedder"),
            on_hit=cache_cfg.get("on_hit"),
            on_miss=cache_cfg.get("on_miss"),
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tenant_id: str = "default",
    ) -> LLMResponse:
        return await self._run_complete(system_prompt=system_prompt, user_prompt=user_prompt, tenant_id=tenant_id)

    def complete_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tenant_id: str = "default",
    ) -> LLMResponse:
        return asyncio.run(self.complete(system_prompt=system_prompt, user_prompt=user_prompt, tenant_id=tenant_id))

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[LLMStreamChunk]:
        estimate = TokenBudgetManager.estimate_tokens(system_prompt, user_prompt)
        self.budget.ensure_budget(tenant_id, estimate)
        last_error: LLMProviderError | None = None
        for provider_name in self.provider_chain:
            adapter = self.adapters[provider_name]
            for _ in range(self.retry_policy.max_attempts):
                try:
                    async for chunk in adapter.stream(system_prompt=system_prompt, user_prompt=user_prompt):
                        yield chunk
                    self.budget.record_usage(tenant_id, TokenUsage(estimate, 0, estimate))
                    return
                except LLMProviderError as exc:
                    last_error = exc
                    if not exc.retryable:
                        break
            if last_error and not last_error.retryable:
                break
        raise last_error or LLMProviderError("No provider configured")

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        tenant_id: str = "default",
        correction_attempts: int = 2,
    ) -> dict[str, Any]:
        working_prompt = user_prompt
        for _ in range(correction_attempts + 1):
            response = await self._run_complete(
                system_prompt=system_prompt,
                user_prompt=working_prompt,
                tenant_id=tenant_id,
            )
            try:
                payload = json.loads(response.content)
            except json.JSONDecodeError:
                working_prompt = (
                    f"{user_prompt}\n\nReturn strictly valid JSON. Do not include markdown fences or prose."
                )
                continue
            if self._schema_valid(payload, schema):
                return payload
            working_prompt = (
                f"{user_prompt}\n\nYour previous JSON did not satisfy the schema. "
                "Return a corrected JSON object only."
            )
        raise LLMProviderError("Structured response could not be parsed/validated", retryable=False)

    async def _run_complete(self, *, system_prompt: str, user_prompt: str, tenant_id: str) -> LLMResponse:
        estimate = TokenBudgetManager.estimate_tokens(system_prompt, user_prompt)
        self.budget.ensure_budget(tenant_id, estimate)
        if self.cache:
            cached = self.cache.get(tenant_id=tenant_id, system_prompt=system_prompt, user_prompt=user_prompt)
            if cached:
                return cached

        last_error: LLMProviderError | None = None
        for provider_name in self.provider_chain:
            adapter = self.adapters[provider_name]
            for _ in range(self.retry_policy.max_attempts):
                try:
                    response = await adapter.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                    usage = self._extract_usage(response=response, estimate=estimate)
                    self.budget.record_usage(tenant_id, usage)
                    if self.cache:
                        self.cache.put(
                            tenant_id=tenant_id,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            response=response,
                        )
                    return response
                except LLMProviderError as exc:
                    last_error = exc
                    if not exc.retryable:
                        break
            if last_error and not last_error.retryable:
                break
        raise last_error or LLMProviderError("No provider configured")

    def _extract_usage(self, *, response: LLMResponse, estimate: int) -> TokenUsage:
        usage = response.raw.get("usage") if isinstance(response.raw, dict) else None
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens", estimate))
            completion_tokens = int(usage.get("completion_tokens", TokenBudgetManager.estimate_tokens(response.content)))
            total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
            return TokenUsage(prompt_tokens, completion_tokens, total_tokens)
        completion_tokens = TokenBudgetManager.estimate_tokens(response.content)
        return TokenUsage(estimate, completion_tokens, estimate + completion_tokens)

    def _schema_valid(self, payload: Any, schema: dict[str, Any]) -> bool:
        if schema.get("type") == "object" and not isinstance(payload, dict):
            return False
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                return False
        properties = schema.get("properties", {})
        for key, prop in properties.items():
            if key not in payload:
                continue
            expected = prop.get("type")
            value = payload[key]
            if expected == "string" and not isinstance(value, str):
                return False
            if expected == "number" and not isinstance(value, (int, float)):
                return False
            if expected == "integer" and not isinstance(value, int):
                return False
            if expected == "array" and not isinstance(value, list):
                return False
            if expected == "object" and not isinstance(value, dict):
                return False
        return True


LLMClient = LLMGateway
