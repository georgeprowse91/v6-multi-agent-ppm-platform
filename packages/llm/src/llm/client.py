from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class LLMResponse:
    content: str
    raw: dict[str, Any]


class LLMProviderError(RuntimeError):
    pass


class LLMProvider:
    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    def __init__(self, response: Any) -> None:
        self.response = response

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if isinstance(self.response, dict):
            content = json.dumps(self.response)
            raw = self.response
        else:
            content = str(self.response)
            raw = {"content": content}
        return LLMResponse(content=content, raw=raw)


class OpenAIHTTPProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str, base_url: str, timeout: float) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
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
            response.raise_for_status()
            data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data)


class AzureOpenAIHTTPProvider(LLMProvider):
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
        self.deployment = deployment
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.timeout = timeout

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
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
            response.raise_for_status()
            data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data)


class LLMClient:
    def __init__(self, provider: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.provider_name = provider or os.getenv("LLM_PROVIDER", "mock")
        self.provider = self._build_provider(self.provider_name)

    def _build_provider(self, provider_name: str) -> LLMProvider:
        provider_name = provider_name.lower()
        timeout = float(os.getenv("LLM_TIMEOUT", "10"))

        if provider_name == "mock":
            response = self.config.get("mock_response")
            if response is None:
                response = {"intents": [{"intent": "general_query", "confidence": 0.5}]}
            return MockLLMProvider(response=response)

        if provider_name in {"openai", "openai-http"}:
            api_key = os.getenv("LLM_API_KEY")
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
            if not api_key:
                raise LLMProviderError("LLM_API_KEY is required for OpenAI provider")
            return OpenAIHTTPProvider(
                api_key=api_key,
                model=model,
                base_url=base_url,
                timeout=timeout,
            )

        if provider_name in {"azure-openai", "azure"}:
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("LLM_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            if not api_key or not endpoint or not deployment:
                raise LLMProviderError("Azure OpenAI requires endpoint, deployment, and API key")
            return AzureOpenAIHTTPProvider(
                api_key=api_key,
                deployment=deployment,
                endpoint=endpoint,
                api_version=api_version,
                timeout=timeout,
            )

        raise LLMProviderError(f"Unsupported LLM provider: {provider_name}")

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return await self.provider.complete(system_prompt, user_prompt)
