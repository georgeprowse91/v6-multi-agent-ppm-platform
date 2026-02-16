from __future__ import annotations

import asyncio

import pytest

from common.resilience import (
    CircuitBreakerPolicy,
    CircuitOpenError,
    DependencyResilienceConfig,
    ResilienceMiddleware,
    RetryPolicy,
    TimeoutPolicy,
)


class _FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _build_middleware() -> ResilienceMiddleware:
    return ResilienceMiddleware(
        DependencyResilienceConfig(
            dependency="common-tests",
            retry=RetryPolicy(max_attempts=1, initial_backoff_s=0),
            timeout=TimeoutPolicy(timeout_s=0.1),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                failure_window_s=60,
                recovery_timeout_s=5,
            ),
        )
    )


def test_circuit_breaker_closed_to_open_to_half_open_to_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _FakeClock()
    monkeypatch.setattr("common.resilience.time.monotonic", clock.monotonic)

    middleware = _build_middleware()

    with pytest.raises(RuntimeError):
        middleware.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert middleware._state == "open"  # noqa: SLF001

    with pytest.raises(CircuitOpenError):
        middleware.execute(lambda: 1)

    clock.advance(5.1)
    assert middleware.execute(lambda: 42) == 42
    assert middleware._state == "closed"  # noqa: SLF001


@pytest.mark.asyncio
async def test_retry_policy_attempts_and_async_backoff_progression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("common.resilience.asyncio.sleep", fake_sleep)

    middleware = ResilienceMiddleware(
        DependencyResilienceConfig(
            dependency="retry-async",
            retry=RetryPolicy(max_attempts=4, initial_backoff_s=0.1, backoff_multiplier=3.0),
            timeout=TimeoutPolicy(timeout_s=1),
            circuit_breaker=CircuitBreakerPolicy(failure_threshold=10),
        )
    )

    attempts = 0

    async def flaky_operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("transient")
        return "ok"

    result = await middleware.execute_async(flaky_operation)

    assert result == "ok"
    assert attempts == 3
    assert sleep_calls == [0.1, 0.30000000000000004]


@pytest.mark.asyncio
async def test_retry_policy_does_not_retry_circuit_open_error() -> None:
    middleware = ResilienceMiddleware(
        DependencyResilienceConfig(
            dependency="retry-circuit-open",
            retry=RetryPolicy(max_attempts=5, initial_backoff_s=0.2),
            timeout=TimeoutPolicy(timeout_s=1),
            circuit_breaker=CircuitBreakerPolicy(failure_threshold=10),
        )
    )

    attempts = 0

    async def operation() -> int:
        nonlocal attempts
        attempts += 1
        raise CircuitOpenError("already open")

    with pytest.raises(CircuitOpenError):
        await middleware.execute_async(operation)

    assert attempts == 1


@pytest.mark.asyncio
async def test_timeout_enforces_cancellation_and_cleanup() -> None:
    middleware = ResilienceMiddleware(
        DependencyResilienceConfig(
            dependency="timeout-test",
            retry=RetryPolicy(max_attempts=1, initial_backoff_s=0),
            timeout=TimeoutPolicy(timeout_s=0.01),
            circuit_breaker=CircuitBreakerPolicy(failure_threshold=10),
        )
    )

    cancelled = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def never_finishes() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        finally:
            cleaned_up.set()

    with pytest.raises(asyncio.TimeoutError):
        await middleware.execute_async(never_finishes)

    assert cancelled.is_set()
    assert cleaned_up.is_set()
