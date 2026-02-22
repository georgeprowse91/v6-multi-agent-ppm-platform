from __future__ import annotations

import json

import pytest
from llm.client import LLMProviderError
from model_registry import clear_model_registry_cache, get_enabled_models
from router import LLMRouter, LLMRouteRequest


def test_registry_filters_enabled_and_demo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    registry_path = tmp_path / "llm_models.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "provider": "openai",
                    "model_id": "a",
                    "display_name": "A",
                    "enabled": True,
                    "capabilities": ["chat"],
                    "allow_in_demo": True,
                },
                {
                    "provider": "google",
                    "model_id": "b",
                    "display_name": "B",
                    "enabled": False,
                    "capabilities": ["chat"],
                    "allow_in_demo": True,
                },
                {
                    "provider": "anthropic",
                    "model_id": "c",
                    "display_name": "C",
                    "enabled": True,
                    "capabilities": ["chat"],
                    "allow_in_demo": False,
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_MODEL_REGISTRY_PATH", str(registry_path))
    clear_model_registry_cache()

    enabled = get_enabled_models(demo_mode=False)
    assert [(item.provider, item.model_id) for item in enabled] == [
        ("openai", "a"),
        ("anthropic", "c"),
    ]

    demo_only = get_enabled_models(demo_mode=True)
    assert [(item.provider, item.model_id) for item in demo_only] == [("openai", "a")]


@pytest.mark.anyio
async def test_router_rejects_unknown_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    registry_path = tmp_path / "llm_models.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "provider": "openai",
                    "model_id": "known",
                    "display_name": "Known",
                    "enabled": True,
                    "capabilities": ["chat"],
                    "allow_in_demo": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_MODEL_REGISTRY_PATH", str(registry_path))
    clear_model_registry_cache()

    router = LLMRouter(demo_mode=False)
    with pytest.raises(LLMProviderError, match="unavailable"):
        await router.route(
            provider="openai",
            model_id="missing",
            request=LLMRouteRequest(system_prompt="s", user_prompt="u"),
        )
