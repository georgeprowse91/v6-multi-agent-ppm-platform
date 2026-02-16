from __future__ import annotations

import os
from dataclasses import dataclass

from model_registry import find_model, get_enabled_models
from providers.anthropic_provider import AnthropicProvider
from providers.google_provider import GoogleProvider
from providers.openai_provider import OpenAIProvider
from llm.types import LLMProviderError, LLMResponse

try:
    from security.secrets import resolve_secret
except Exception:  # pragma: no cover - package standalone mode

    def resolve_secret(value: str | None) -> str | None:  # type: ignore[no-redef]
        return value


@dataclass
class LLMRouteRequest:
    system_prompt: str
    user_prompt: str
    json_mode: bool = False
    temperature: float = 0.0
    max_tokens: int | None = None


class LLMRouter:
    def __init__(self, *, demo_mode: bool = False, timeout: float = 10.0) -> None:
        self.demo_mode = demo_mode
        self.timeout = timeout

    async def route(self, *, provider: str, model_id: str, request: LLMRouteRequest) -> LLMResponse:
        model = find_model(provider, model_id, demo_mode=self.demo_mode)
        if not model:
            raise LLMProviderError(
                f"Model {provider}:{model_id} is unavailable",
                retryable=False,
                provider=provider,
            )
        adapter = self._build_adapter(model.provider)
        return await adapter.complete(
            model_id=model.model_id,
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            json_mode=request.json_mode,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

    def default_selection(self) -> tuple[str, str]:
        models = get_enabled_models(demo_mode=self.demo_mode)
        if not models:
            raise LLMProviderError("No enabled LLM models are configured", retryable=False, provider="router")
        selected = models[0]
        return selected.provider, selected.model_id

    def _build_adapter(self, provider: str):
        if provider == "openai":
            api_key = resolve_secret(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))
            if not api_key:
                raise LLMProviderError("OpenAI API key is not configured", retryable=False, provider=provider)
            return OpenAIProvider(
                api_key=api_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                timeout=self.timeout,
            )
        if provider == "anthropic":
            api_key = resolve_secret(os.getenv("ANTHROPIC_API_KEY"))
            if not api_key:
                raise LLMProviderError("Anthropic API key is not configured", retryable=False, provider=provider)
            return AnthropicProvider(
                api_key=api_key,
                base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
                timeout=self.timeout,
            )
        if provider == "google":
            api_key = resolve_secret(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
            if not api_key:
                raise LLMProviderError("Google API key is not configured", retryable=False, provider=provider)
            return GoogleProvider(
                api_key=api_key,
                base_url=os.getenv("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
                timeout=self.timeout,
            )
        raise LLMProviderError(f"Unsupported provider: {provider}", retryable=False, provider=provider)
