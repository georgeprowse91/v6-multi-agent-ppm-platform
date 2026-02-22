from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import TypeVar

try:
    from prometheus_client import Counter
except Exception:  # pragma: no cover
    Counter = None

from feature_flags.manager import clear_dependency_degraded, set_dependency_degraded

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a circuit breaker is open and denies execution."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_s: float = 0.2
    backoff_multiplier: float = 2.0


@dataclass(frozen=True)
class TimeoutPolicy:
    timeout_s: float = 10.0


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 5
    failure_window_s: float = 60.0
    recovery_timeout_s: float = 30.0


@dataclass(frozen=True)
class DependencyResilienceConfig:
    dependency: str
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    timeout: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    circuit_breaker: CircuitBreakerPolicy = field(default_factory=CircuitBreakerPolicy)


if Counter:
    _state_transitions = Counter(
        "dependency_circuit_breaker_state_transitions_total",
        "Count of dependency circuit breaker state transitions",
        ("dependency", "from_state", "to_state"),
    )
    _open_denials = Counter(
        "dependency_circuit_breaker_open_denials_total",
        "Count of dependency requests denied because circuit is open",
        ("dependency",),
    )
else:  # pragma: no cover
    _state_transitions = None
    _open_denials = None


class ResilienceMiddleware:
    def __init__(self, config: DependencyResilienceConfig) -> None:
        self.config = config
        self._state = "closed"
        self._opened_at: float | None = None
        self._failure_timestamps: list[float] = []
        self._lock = Lock()

    def _record_transition(self, old_state: str, new_state: str) -> None:
        if old_state == new_state:
            return
        if _state_transitions is not None:
            _state_transitions.labels(
                dependency=self.config.dependency,
                from_state=old_state,
                to_state=new_state,
            ).inc()
        if new_state == "open":
            set_dependency_degraded(self.config.dependency)
        elif new_state == "closed":
            clear_dependency_degraded(self.config.dependency)

    def _prune_failures(self, now: float) -> None:
        window_start = now - self.config.circuit_breaker.failure_window_s
        self._failure_timestamps = [
            item for item in self._failure_timestamps if item >= window_start
        ]

    def _before_call(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune_failures(now)
            if self._state != "open":
                return
            if (
                self._opened_at
                and (now - self._opened_at) >= self.config.circuit_breaker.recovery_timeout_s
            ):
                old_state = self._state
                self._state = "half_open"
                self._record_transition(old_state, self._state)
                return
        if _open_denials is not None:
            _open_denials.labels(dependency=self.config.dependency).inc()
        raise CircuitOpenError(f"Circuit open for dependency={self.config.dependency}")

    def _mark_success(self) -> None:
        with self._lock:
            self._failure_timestamps = []
            self._opened_at = None
            old_state = self._state
            self._state = "closed"
            self._record_transition(old_state, self._state)

    def _mark_failure(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._failure_timestamps.append(now)
            self._prune_failures(now)
            should_open = (
                len(self._failure_timestamps) >= self.config.circuit_breaker.failure_threshold
            )
            if should_open:
                old_state = self._state
                self._state = "open"
                self._opened_at = now
                self._record_transition(old_state, self._state)

    async def execute_async(self, operation: Callable[[], Awaitable[T]]) -> T:
        self._before_call()
        last_error: Exception | None = None
        for attempt in range(self.config.retry.max_attempts):
            try:
                result = await asyncio.wait_for(operation(), timeout=self.config.timeout.timeout_s)
                self._mark_success()
                return result
            except CircuitOpenError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._mark_failure()
                if attempt + 1 >= self.config.retry.max_attempts:
                    break
                delay = self.config.retry.initial_backoff_s * (
                    self.config.retry.backoff_multiplier**attempt
                )
                if delay > 0:
                    await asyncio.sleep(delay)
        if last_error is None:
            raise RuntimeError("Unexpected resilience middleware state")
        raise last_error

    def execute(self, operation: Callable[[], T]) -> T:
        self._before_call()
        last_error: Exception | None = None
        for attempt in range(self.config.retry.max_attempts):
            try:
                result = operation()
                self._mark_success()
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._mark_failure()
                if attempt + 1 >= self.config.retry.max_attempts:
                    break
                delay = self.config.retry.initial_backoff_s * (
                    self.config.retry.backoff_multiplier**attempt
                )
                if delay > 0:
                    time.sleep(delay)
        if last_error is None:
            raise RuntimeError("Unexpected resilience middleware state")
        raise last_error


def dependency_config_from_env(
    dependency: str,
    *,
    timeout_s: float,
    max_attempts: int,
    initial_backoff_s: float,
) -> DependencyResilienceConfig:
    return DependencyResilienceConfig(
        dependency=dependency,
        timeout=TimeoutPolicy(timeout_s=timeout_s),
        retry=RetryPolicy(
            max_attempts=max(1, max_attempts), initial_backoff_s=max(0.0, initial_backoff_s)
        ),
    )
