"""Tests for the OIDC discovery cache in the API gateway middleware.

Ensures:
- Cache returns stored entries within TTL
- Cache evicts expired entries after TTL
- Cache evicts LRU entry when max_size is exceeded
- Cache is thread-safe (concurrent reads/writes do not corrupt state)
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

# Make api-gateway source importable.
_API_SRC = Path(__file__).resolve().parents[2] / "apps" / "api-gateway" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

# Import the internal TTL cache class directly for unit testing.
from api.middleware.security import _OIDCTTLCache  # noqa: E402


# ---------------------------------------------------------------------------
# Basic get / set
# ---------------------------------------------------------------------------


def test_get_returns_none_on_empty_cache() -> None:
    cache = _OIDCTTLCache(ttl=60, max_size=8)
    assert cache.get("https://example.com/.well-known/openid-configuration") is None


def test_set_and_get_within_ttl() -> None:
    cache = _OIDCTTLCache(ttl=60, max_size=8)
    data = {"issuer": "https://example.com", "jwks_uri": "https://example.com/keys"}
    cache.set("https://example.com/oidc", data)
    assert cache.get("https://example.com/oidc") == data


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


def test_entry_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate TTL expiry by advancing the clock via monkeypatching time.time."""
    import api.middleware.security as sec_mod  # noqa: PLC0415

    cache = _OIDCTTLCache(ttl=5, max_size=8)
    data = {"issuer": "https://example.com"}
    cache.set("url", data)

    # Advance time beyond the TTL.
    original_time = time.time
    monkeypatch.setattr(sec_mod._time, "time", lambda: original_time() + 10)

    # The entry should now be treated as expired.
    assert cache.get("url") is None


def test_entry_valid_just_before_ttl_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.middleware.security as sec_mod  # noqa: PLC0415

    cache = _OIDCTTLCache(ttl=30, max_size=8)
    data = {"issuer": "https://example.com"}
    cache.set("url", data)

    # Advance time to just under TTL.
    original_time = time.time
    monkeypatch.setattr(sec_mod._time, "time", lambda: original_time() + 29)

    assert cache.get("url") == data


# ---------------------------------------------------------------------------
# Size cap (LRU eviction)
# ---------------------------------------------------------------------------


def test_oldest_entry_evicted_when_max_size_exceeded() -> None:
    cache = _OIDCTTLCache(ttl=60, max_size=3)
    for i in range(4):
        cache.set(f"url-{i}", {"id": i})

    # url-0 is the oldest and should have been evicted.
    assert cache.get("url-0") is None
    # The three most recent entries should still be present.
    for i in range(1, 4):
        assert cache.get(f"url-{i}") == {"id": i}


def test_max_size_one_replaces_only_entry() -> None:
    cache = _OIDCTTLCache(ttl=60, max_size=1)
    cache.set("a", {"v": 1})
    cache.set("b", {"v": 2})
    assert cache.get("a") is None
    assert cache.get("b") == {"v": 2}


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_concurrent_writes_do_not_corrupt_cache() -> None:
    """Write from multiple threads and verify the cache is internally consistent."""
    cache = _OIDCTTLCache(ttl=60, max_size=200)
    errors: list[Exception] = []

    def _worker(thread_id: int) -> None:
        try:
            for i in range(50):
                key = f"thread-{thread_id}-url-{i}"
                cache.set(key, {"thread": thread_id, "item": i})
                _ = cache.get(key)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Cache thread-safety failures: {errors}"
