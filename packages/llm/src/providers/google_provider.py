from __future__ import annotations

from typing import Any

import httpx
from llm.types import LLMProviderError, LLMResponse


class GoogleProvider:
    provider = "google"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 10.0,
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
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        url = f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "Google request timed out", retryable=True, provider=self.provider
            ) from exc
        if response.status_code >= 400:
            raise LLMProviderError(
                f"Google request failed status={response.status_code}",
                retryable=response.status_code in {408, 409, 425, 429, 500, 502, 503, 504},
                provider=self.provider,
            )
        data = response.json()
        candidates = data.get("candidates") or []
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            if parts and isinstance(parts[0], dict):
                text = str(parts[0].get("text", ""))
        return LLMResponse(content=text, raw=data, provider=self.provider)
