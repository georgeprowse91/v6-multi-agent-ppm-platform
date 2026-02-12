from __future__ import annotations

from collections.abc import Callable

import pytest

pytest.importorskip("cryptography")

from security import auth


class _MockResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _MockAsyncClient:
    def __init__(self, payload_factory: Callable[[str], dict[str, object]], calls: list[str], *args, **kwargs) -> None:
        self._payload_factory = payload_factory
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str):
        self._calls.append(url)
        return _MockResponse(self._payload_factory(url))


@pytest.fixture(autouse=True)
def _reset_auth_caches() -> None:
    auth._OIDC_CONFIG_CACHE.clear()
    auth._JWKS_CACHE.clear()


@pytest.mark.asyncio
async def test_oidc_cache_hit_reuses_cached_entry(monkeypatch) -> None:
    calls: list[str] = []
    now = [1000.0]

    def fake_time() -> float:
        return now[0]

    monkeypatch.setattr(auth._time, "time", fake_time)
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _MockAsyncClient(lambda _url: {"jwks_uri": "https://jwks-1"}, calls, *args, **kwargs),
    )

    first = await auth._load_oidc_config("https://issuer/.well-known/openid-configuration")
    second = await auth._load_oidc_config("https://issuer/.well-known/openid-configuration")

    assert first == second
    assert calls == ["https://issuer/.well-known/openid-configuration"]


@pytest.mark.asyncio
async def test_oidc_cache_expiry_fetches_fresh_value(monkeypatch) -> None:
    calls: list[str] = []
    now = [1000.0]

    def fake_time() -> float:
        return now[0]

    monkeypatch.setattr(auth._time, "time", fake_time)
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _MockAsyncClient(
            lambda _url: {"jwks_uri": f"https://jwks-{len(calls) + 1}"}, calls, *args, **kwargs
        ),
    )

    first = await auth._load_oidc_config("https://issuer/.well-known/openid-configuration")
    now[0] += auth._CACHE_TTL + 1
    second = await auth._load_oidc_config("https://issuer/.well-known/openid-configuration")

    assert first["jwks_uri"] == "https://jwks-1"
    assert second["jwks_uri"] == "https://jwks-2"
    assert calls == [
        "https://issuer/.well-known/openid-configuration",
        "https://issuer/.well-known/openid-configuration",
    ]


def test_ttl_cache_evicts_oldest_entry_when_max_size_exceeded(monkeypatch) -> None:
    now = [1000.0]

    def fake_time() -> float:
        return now[0]

    monkeypatch.setattr(auth._time, "time", fake_time)
    cache = auth._TTLCache(ttl_seconds=3600, max_size=2)

    cache.set("issuer-a", {"value": "a"})
    now[0] += 1
    cache.set("issuer-b", {"value": "b"})
    now[0] += 1
    cache.set("issuer-c", {"value": "c"})

    assert cache.get("issuer-a") is None
    assert cache.get("issuer-b") == {"value": "b"}
    assert cache.get("issuer-c") == {"value": "c"}


def test_ttl_cache_refresh_behavior_uses_recently_fetched_order(monkeypatch) -> None:
    now = [1000.0]

    def fake_time() -> float:
        return now[0]

    monkeypatch.setattr(auth._time, "time", fake_time)
    cache = auth._TTLCache(ttl_seconds=3600, max_size=2)

    cache.set("issuer-a", {"value": "a"})
    now[0] += 1
    cache.set("issuer-b", {"value": "b"})

    # Refresh issuer-a by reading it so it becomes most recently used.
    assert cache.get("issuer-a") == {"value": "a"}

    now[0] += 1
    cache.set("issuer-c", {"value": "c"})

    assert cache.get("issuer-a") == {"value": "a"}
    assert cache.get("issuer-b") is None
    assert cache.get("issuer-c") == {"value": "c"}
