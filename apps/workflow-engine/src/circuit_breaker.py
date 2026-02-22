from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic


class CircuitBreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 30


class CircuitBreaker:
    def __init__(
        self,
        config: CircuitBreakerConfig,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.config = config
        self._clock = clock
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    def allow(self) -> bool:
        if self._state != CircuitBreakerState.OPEN:
            return True
        if self._opened_at is None:
            return False
        if self._clock() - self._opened_at >= self.config.recovery_timeout_seconds:
            self._state = CircuitBreakerState.HALF_OPEN
            return True
        return False

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitBreakerState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._state == CircuitBreakerState.HALF_OPEN or (
            self._failure_count >= self.config.failure_threshold
        ):
            self._state = CircuitBreakerState.OPEN
            self._opened_at = self._clock()

    def is_open(self) -> bool:
        return self._state == CircuitBreakerState.OPEN

    def time_until_retry(self) -> float:
        if self._state != CircuitBreakerState.OPEN or self._opened_at is None:
            return 0.0
        remaining = self.config.recovery_timeout_seconds - (self._clock() - self._opened_at)
        return max(0.0, remaining)


class CircuitBreakerRegistry:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, key: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        existing = self._breakers.get(key)
        if existing and existing.config == config:
            return existing
        breaker = CircuitBreaker(config=config, clock=self._clock)
        self._breakers[key] = breaker
        return breaker
