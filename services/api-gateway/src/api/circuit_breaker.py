from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass


@dataclass
class CircuitState:
    failures: int = 0
    successes: int = 0
    opened_at: float | None = None
    state: str = "closed"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        half_open_successes: int = 1,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(1, recovery_timeout)
        self.half_open_successes = max(1, half_open_successes)
        self._lock = threading.Lock()
        self._states: dict[str, CircuitState] = {}

    @classmethod
    def from_env(cls) -> CircuitBreaker:
        failure_threshold = int(os.getenv("CONNECTOR_CIRCUIT_FAILURE_THRESHOLD", "3"))
        recovery_timeout = int(os.getenv("CONNECTOR_CIRCUIT_RECOVERY_SECONDS", "60"))
        half_open_successes = int(os.getenv("CONNECTOR_CIRCUIT_HALF_OPEN_SUCCESSES", "1"))
        return cls(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_successes=half_open_successes,
        )

    def _get_state(self, key: str) -> CircuitState:
        return self._states.setdefault(key, CircuitState())

    def allow_request(self, key: str) -> bool:
        with self._lock:
            state = self._get_state(key)
            if state.state == "open":
                if state.opened_at and time.monotonic() - state.opened_at >= self.recovery_timeout:
                    state.state = "half_open"
                    state.failures = 0
                    state.successes = 0
                    return True
                return False
            return True

    def record_success(self, key: str) -> None:
        with self._lock:
            state = self._get_state(key)
            if state.state == "half_open":
                state.successes += 1
                if state.successes >= self.half_open_successes:
                    state.state = "closed"
                    state.failures = 0
                    state.successes = 0
                    state.opened_at = None
                return
            state.failures = 0
            state.successes = 0
            state.state = "closed"
            state.opened_at = None

    def record_failure(self, key: str) -> None:
        with self._lock:
            state = self._get_state(key)
            if state.state == "half_open":
                state.state = "open"
                state.opened_at = time.monotonic()
                state.failures = self.failure_threshold
                state.successes = 0
                return
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.state = "open"
                state.opened_at = time.monotonic()

    def get_state(self, key: str) -> CircuitState:
        with self._lock:
            state = self._get_state(key)
            return CircuitState(
                failures=state.failures,
                successes=state.successes,
                opened_at=state.opened_at,
                state=state.state,
            )
