"""Azure OpenAI provider for the LLM router.

Azure OpenAI is a preferred provider for Australian Government and enterprise
deployments that require data sovereignty (ISM/PSPF), APRA CPS 234 compliance,
and Private Endpoint connectivity.  It is API-compatible with OpenAI but uses
a deployment-scoped URL and an Azure subscription key rather than a user-level
API key.

Environment variables
---------------------
AZURE_OPENAI_ENDPOINT   - Required.  The Azure OpenAI endpoint, e.g.
                          ``https://<resource>.openai.azure.com``.
AZURE_OPENAI_API_KEY    - Required.  The Azure subscription key for the resource.
AZURE_OPENAI_API_VERSION - Optional.  Defaults to ``2024-05-01-preview``.
"""

from __future__ import annotations

from typing import Any

import httpx
from llm.types import LLMProviderError, LLMResponse

# The stable GA API version with json_object response format support.
_DEFAULT_API_VERSION = "2024-05-01-preview"


class AzureOpenAIProvider:
    provider = "azure_openai"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        api_version: str = _DEFAULT_API_VERSION,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.timeout = timeout

    def _chat_url(self, deployment_id: str) -> str:
        # Azure OpenAI uses a deployment-scoped path.
        return (
            f"{self.endpoint}/openai/deployments/{deployment_id}"
            f"/chat/completions?api-version={self.api_version}"
        )

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
        """Send a chat-completion request to Azure OpenAI.

        The ``model_id`` field is used as the Azure *deployment name*.  In
        Azure OpenAI, models are accessed via named deployments, not directly
        by model family.  Operators must create a deployment with the same
        ``model_id`` value used in the model registry.
        """
        payload: dict[str, Any] = {
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

        url = self._chat_url(model_id)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers={"api-key": self.api_key, "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "Azure OpenAI request timed out", retryable=True, provider=self.provider
            ) from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"Azure OpenAI request failed status={response.status_code}",
                retryable=response.status_code in {408, 409, 425, 429, 500, 502, 503, 504},
                provider=self.provider,
            )

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data, provider=self.provider)
