"""Tests for the Azure OpenAI provider.

Covers:
- Successful chat completion
- JSON mode header injection (response_format)
- max_tokens forwarding
- Timeout → retryable LLMProviderError
- HTTP 4xx/5xx → retryable / non-retryable LLMProviderError
- Correct deployment URL construction
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure providers package is importable when running from repo root.
_LLM_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_LLM_SRC) not in sys.path:
    sys.path.insert(0, str(_LLM_SRC))

import httpx  # noqa: E402

from llm.types import LLMProviderError  # noqa: E402
from providers.azure_openai_provider import AzureOpenAIProvider  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENDPOINT = "https://my-resource.openai.azure.com"
_API_KEY = "test-azure-key"
_API_VERSION = "2024-05-01-preview"
_DEPLOYMENT = "gpt-4o"


def _provider(**kwargs) -> AzureOpenAIProvider:
    defaults = dict(api_key=_API_KEY, endpoint=_ENDPOINT, api_version=_API_VERSION)
    defaults.update(kwargs)
    return AzureOpenAIProvider(**defaults)


def _ok_response(content: str = "hello") -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "model": _DEPLOYMENT,
    }
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_successful_completion() -> None:
    provider = _provider()
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok_response("Paris")
        result = await provider.complete(
            model_id=_DEPLOYMENT,
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the capital of France?",
            json_mode=False,
            temperature=0.0,
            max_tokens=None,
        )
    assert result.content == "Paris"
    assert result.provider == "azure_openai"


@pytest.mark.anyio
async def test_json_mode_sets_response_format() -> None:
    provider = _provider()
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok_response('{"answer": "Paris"}')
        await provider.complete(
            model_id=_DEPLOYMENT,
            system_prompt="Answer in JSON.",
            user_prompt="Capital of France?",
            json_mode=True,
            temperature=0.0,
            max_tokens=128,
        )
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json") or call_kwargs[0][1]
    assert payload.get("response_format") == {"type": "json_object"}
    assert payload.get("max_tokens") == 128


@pytest.mark.anyio
async def test_deployment_url_correct() -> None:
    """The URL must embed the deployment name and api-version query param."""
    provider = _provider()
    captured_url: list[str] = []

    async def _fake_post(url: str, **kwargs):  # type: ignore[return]
        captured_url.append(url)
        return _ok_response()

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, side_effect=_fake_post):
        await provider.complete(
            model_id=_DEPLOYMENT,
            system_prompt="sys",
            user_prompt="user",
            json_mode=False,
            temperature=0.0,
            max_tokens=None,
        )

    assert captured_url
    url = captured_url[0]
    assert f"/openai/deployments/{_DEPLOYMENT}/chat/completions" in url
    assert f"api-version={_API_VERSION}" in url


@pytest.mark.anyio
async def test_timeout_raises_retryable_error() -> None:
    provider = _provider()
    with patch.object(
        httpx.AsyncClient, "post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("t/o")
    ):
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(
                model_id=_DEPLOYMENT,
                system_prompt="s",
                user_prompt="u",
                json_mode=False,
                temperature=0.0,
                max_tokens=None,
            )
    assert exc_info.value.retryable is True
    assert exc_info.value.provider == "azure_openai"


@pytest.mark.anyio
async def test_429_raises_retryable_error() -> None:
    provider = _provider()
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(
                model_id=_DEPLOYMENT,
                system_prompt="s",
                user_prompt="u",
                json_mode=False,
                temperature=0.0,
                max_tokens=None,
            )
    assert exc_info.value.retryable is True


@pytest.mark.anyio
async def test_400_raises_non_retryable_error() -> None:
    provider = _provider()
    mock_response = MagicMock()
    mock_response.status_code = 400
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(
                model_id=_DEPLOYMENT,
                system_prompt="s",
                user_prompt="u",
                json_mode=False,
                temperature=0.0,
                max_tokens=None,
            )
    assert exc_info.value.retryable is False


@pytest.mark.anyio
async def test_api_key_sent_in_header() -> None:
    provider = _provider()
    captured_headers: list[dict] = []

    async def _fake_post(url: str, *, headers: dict, **kwargs):  # type: ignore[return]
        captured_headers.append(headers)
        return _ok_response()

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, side_effect=_fake_post):
        await provider.complete(
            model_id=_DEPLOYMENT,
            system_prompt="s",
            user_prompt="u",
            json_mode=False,
            temperature=0.0,
            max_tokens=None,
        )

    assert captured_headers
    assert captured_headers[0].get("api-key") == _API_KEY


@pytest.mark.anyio
async def test_router_builds_azure_openai_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """LLMRouter._build_adapter must return AzureOpenAIProvider for azure_openai."""
    import json as _json

    registry_path = tmp_path / "models.json"
    registry_path.write_text(
        _json.dumps(
            [
                {
                    "provider": "azure_openai",
                    "model_id": "gpt-4o",
                    "display_name": "Azure GPT-4o",
                    "enabled": True,
                    "capabilities": ["chat"],
                    "allow_in_demo": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_MODEL_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://resource.openai.azure.com")

    # Avoid the lru_cache returning a stale registry from an earlier test.
    from model_registry import clear_model_registry_cache

    clear_model_registry_cache()

    from router import LLMRouter  # noqa: PLC0415

    router = LLMRouter()
    adapter = router._build_adapter("azure_openai")
    assert isinstance(adapter, AzureOpenAIProvider)
    assert adapter.api_key == "azure-test-key"
    assert "resource.openai.azure.com" in adapter.endpoint
