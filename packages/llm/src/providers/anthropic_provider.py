from __future__ import annotations

from typing import Any

import httpx
from llm.types import LLMProviderError, LLMResponse


class AnthropicProvider:
    provider = "anthropic"

    def __init__(
        self, *, api_key: str, base_url: str = "https://api.anthropic.com/v1", timeout: float = 10.0
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
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens or 1024,
        }
        if json_mode:
            payload["metadata"] = {"json_mode": True}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "Anthropic request timed out", retryable=True, provider=self.provider
            ) from exc
        if response.status_code >= 400:
            raise LLMProviderError(
                f"Anthropic request failed status={response.status_code}",
                retryable=response.status_code in {408, 409, 425, 429, 500, 502, 503, 504},
                provider=self.provider,
            )
        data = response.json()
        blocks = data.get("content") or []
        text = ""
        if blocks and isinstance(blocks[0], dict):
            text = str(blocks[0].get("text", ""))
        return LLMResponse(content=text, raw=data, provider=self.provider)
