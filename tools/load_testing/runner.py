from __future__ import annotations

import json
import os
import statistics
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadScenario:
    name: str
    request_fn: Callable[[], int]
    total_requests: int
    concurrency: int


@dataclass(frozen=True)
class LoadSla:
    max_avg_latency_s: float
    max_p95_latency_s: float
    max_error_rate: float
    min_requests_per_s: float | None = None


@dataclass(frozen=True)
class LoadScenarioResult:
    name: str
    durations_s: list[float]
    error_count: int
    total_duration_s: float

    @property
    def average_latency_s(self) -> float:
        return statistics.mean(self.durations_s) if self.durations_s else 0.0

    @property
    def p95_latency_s(self) -> float:
        if not self.durations_s:
            return 0.0
        ordered = sorted(self.durations_s)
        index = max(int(len(ordered) * 0.95) - 1, 0)
        return ordered[index]

    @property
    def error_rate(self) -> float:
        total = len(self.durations_s)
        return self.error_count / total if total else 0.0

    @property
    def requests_per_s(self) -> float:
        if self.total_duration_s <= 0:
            return 0.0
        return len(self.durations_s) / self.total_duration_s


def run_load_scenario(scenario: LoadScenario) -> LoadScenarioResult:
    durations: list[float] = []
    errors = 0

    def _invoke() -> tuple[float, bool]:
        start = time.perf_counter()
        status = scenario.request_fn()
        duration = time.perf_counter() - start
        return duration, status >= 400

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=scenario.concurrency) as executor:
        futures = [executor.submit(_invoke) for _ in range(scenario.total_requests)]
        for future in as_completed(futures):
            duration, failed = future.result()
            durations.append(duration)
            if failed:
                errors += 1
    total_duration = time.perf_counter() - start

    return LoadScenarioResult(
        name=scenario.name,
        durations_s=durations,
        error_count=errors,
        total_duration_s=total_duration,
    )


def load_profile(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        if not payload:
            return {}
        target_name = os.getenv("LOAD_TARGET")
        if target_name:
            for entry in payload:
                if entry.get("name") == target_name:
                    payload = entry
                    break
            else:
                payload = payload[0]
        else:
            payload = payload[0]
    elif isinstance(payload, dict) and "targets" in payload:
        targets = payload.get("targets") or []
        target_name = os.getenv("LOAD_TARGET")
        selected = None
        if target_name:
            selected = next((entry for entry in targets if entry.get("name") == target_name), None)
        payload = selected or (targets[0] if targets else {})
    profiles = payload.get("profiles")
    if not profiles:
        return payload
    profile_name = os.getenv("LOAD_PROFILE", "ci")
    selected = profiles.get(profile_name) or profiles.get("ci")
    if not selected:
        return payload
    merged = {key: value for key, value in payload.items() if key != "profiles"}
    merged.update(selected)
    return merged


def assert_sla(result: LoadScenarioResult, sla: LoadSla) -> None:
    if result.average_latency_s > sla.max_avg_latency_s:
        raise AssertionError(
            f"Average latency {result.average_latency_s:.3f}s exceeds SLA "
            f"{sla.max_avg_latency_s:.3f}s"
        )
    if result.p95_latency_s > sla.max_p95_latency_s:
        raise AssertionError(
            f"P95 latency {result.p95_latency_s:.3f}s exceeds SLA " f"{sla.max_p95_latency_s:.3f}s"
        )
    if result.error_rate > sla.max_error_rate:
        raise AssertionError(
            f"Error rate {result.error_rate:.2%} exceeds SLA " f"{sla.max_error_rate:.2%}"
        )
    if sla.min_requests_per_s is not None and result.requests_per_s < sla.min_requests_per_s:
        raise AssertionError(
            f"Throughput {result.requests_per_s:.2f} rps below SLA "
            f"{sla.min_requests_per_s:.2f} rps"
        )
