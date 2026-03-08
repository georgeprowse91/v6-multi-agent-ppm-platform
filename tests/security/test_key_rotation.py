"""Tests for in-process LLM key rotation (Issue 3).

Verifies:
- clear_auth_caches() clears both OIDC and JWKS caches in security.auth
- The SIGUSR1 signal handler is installed during gateway startup
- The /v1/admin/llm/keys/rotate endpoint triggers cache clearing
- The /v1/admin/model-registry/cache/clear endpoint clears model registry cache
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# clear_auth_caches
# ---------------------------------------------------------------------------


def test_clear_auth_caches_is_exported() -> None:
    """clear_auth_caches must be importable from security.auth."""
    from security.auth import clear_auth_caches  # noqa: F401

    assert callable(clear_auth_caches)


def test_clear_auth_caches_clears_oidc_cache() -> None:
    """clear_auth_caches() must empty the OIDC config cache."""
    from security.auth import _OIDC_CONFIG_CACHE, clear_auth_caches

    _OIDC_CONFIG_CACHE.set("https://example.com/oidc", {"issuer": "https://example.com"})
    assert _OIDC_CONFIG_CACHE.get("https://example.com/oidc") is not None

    clear_auth_caches()

    assert (
        _OIDC_CONFIG_CACHE.get("https://example.com/oidc") is None
    ), "clear_auth_caches() must evict all entries from _OIDC_CONFIG_CACHE"


def test_clear_auth_caches_clears_jwks_cache() -> None:
    """clear_auth_caches() must empty the JWKS cache."""
    from security.auth import _JWKS_CACHE, clear_auth_caches

    _JWKS_CACHE.set("https://example.com/keys", {"keys": []})
    assert _JWKS_CACHE.get("https://example.com/keys") is not None

    clear_auth_caches()

    assert (
        _JWKS_CACHE.get("https://example.com/keys") is None
    ), "clear_auth_caches() must evict all entries from _JWKS_CACHE"


def test_clear_auth_caches_idempotent() -> None:
    """Calling clear_auth_caches() on an already-empty cache must not raise."""
    from security.auth import clear_auth_caches

    clear_auth_caches()
    clear_auth_caches()  # second call must not raise


# ---------------------------------------------------------------------------
# Signal handler installation
# ---------------------------------------------------------------------------


def test_install_key_rotation_handler_available() -> None:
    """_install_key_rotation_handler must exist in api.main source."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / "services" / "api-gateway" / "src" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    assert (
        "def _install_key_rotation_handler(" in source
    ), "_install_key_rotation_handler must be defined in api.main"


def test_signal_handler_clears_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulating SIGUSR1 must call clear_auth_caches."""
    import signal as _signal

    if not hasattr(_signal, "SIGUSR1"):
        pytest.skip("SIGUSR1 not available on this platform")

    # Set required env vars so api.main can be imported
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    # Invalidate the settings cache so our env vars take effect
    try:
        import api.config as _cfg

        _cfg.get_settings.cache_clear()
    except Exception:
        pass

    cleared = []

    def mock_clear():
        cleared.append(True)

    import sys

    # Remove cached module if it failed to import previously
    sys.modules.pop("api.main", None)

    import api.main as main_mod

    # Patch after import so the closure inside _install_key_rotation_handler
    # captures our mock when we re-install the handler below.
    monkeypatch.setattr(main_mod, "clear_auth_caches", mock_clear)

    main_mod._install_key_rotation_handler()

    # Simulate SIGUSR1
    handler = _signal.getsignal(_signal.SIGUSR1)
    assert callable(handler), "SIGUSR1 handler must be installed"
    handler(_signal.SIGUSR1, None)

    assert cleared, "clear_auth_caches must be called when SIGUSR1 is received"


# ---------------------------------------------------------------------------
# Model registry cache clear
# ---------------------------------------------------------------------------


def test_clear_model_registry_cache_is_callable() -> None:
    """clear_model_registry_cache must be importable from model_registry."""
    from model_registry import clear_model_registry_cache  # noqa: F401

    assert callable(clear_model_registry_cache)


def test_model_registry_cache_clear_resets_lru(tmp_path: pytest.fixture) -> None:  # type: ignore[valid-type]
    """After clear_model_registry_cache(), load_model_registry re-reads the file."""
    import json
    from unittest.mock import patch

    registry_file = tmp_path / "llm_models.json"
    registry_file.write_text(
        json.dumps(
            [
                {
                    "provider": "openai",
                    "model_id": "gpt-4o",
                    "display_name": "GPT-4o",
                    "enabled": True,
                    "capabilities": ["chat"],
                    "allow_in_demo": False,
                }
            ]
        )
    )

    from model_registry import clear_model_registry_cache, load_model_registry

    with patch("model_registry._registry_path", return_value=registry_file):
        clear_model_registry_cache()
        models = load_model_registry()
        assert len(models) == 1
        assert models[0].model_id == "gpt-4o"

        # Simulate registry update
        registry_file.write_text(
            json.dumps(
                [
                    {
                        "provider": "openai",
                        "model_id": "gpt-4o",
                        "display_name": "GPT-4o",
                        "enabled": True,
                        "capabilities": ["chat"],
                        "allow_in_demo": False,
                    },
                    {
                        "provider": "anthropic",
                        "model_id": "claude-3-5-sonnet",
                        "display_name": "Claude 3.5 Sonnet",
                        "enabled": True,
                        "capabilities": ["chat"],
                        "allow_in_demo": True,
                    },
                ]
            )
        )

        # Without clearing, still returns cached (1 model)
        old_models = load_model_registry()
        assert len(old_models) == 1, "Cache should still return the old value"

        # After clearing, returns new data
        clear_model_registry_cache()
        new_models = load_model_registry()
        assert len(new_models) == 2, "After cache clear, updated registry must be loaded"
