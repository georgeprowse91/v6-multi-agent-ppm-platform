from __future__ import annotations

from typing import Any

import httpx
from llm.types import LLMProviderError, LLMResponse


class OpenAIProvider:
    provider = "openai"

    def __init__(
        self, *, api_key: str, base_url: str = "https://api.openai.com/v1", timeout: float = 10.0
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "OpenAI request timed out", retryable=True, provider=self.provider
            ) from exc
        if response.status_code >= 400:
            raise LLMProviderError(
                f"OpenAI request failed status={response.status_code}",
                retryable=response.status_code in {408, 409, 425, 429, 500, 502, 503, 504},
                provider=self.provider,
            )
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data, provider=self.provider)
