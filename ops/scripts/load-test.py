#!/usr/bin/env python3
"""Run configurable load tests against a target URL."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from tools.load_testing.runner import LoadScenario, LoadSla, assert_sla, load_profile, run_load_scenario


def _request_factory(url: str, timeout_s: float):
    client = httpx.Client(timeout=timeout_s)

    def _request() -> int:
        response = client.get(url)
        return response.status_code

    return client, _request


def main() -> int:
    parser = argparse.ArgumentParser(description="Run load tests for the PPM platform.")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("tests/load/sla_targets.json"),
        help="Path to load profile JSON.",
    )
    parser.add_argument("--target", type=str, help="Override target URL in the profile.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    target = args.target or profile.get("target_url")
    if not target:
        raise SystemExit("No target URL configured in profile or CLI")

    client, request_fn = _request_factory(target, args.timeout)
    scenario = LoadScenario(
        name=profile.get("name", "load-test"),
        request_fn=request_fn,
        total_requests=int(profile.get("total_requests", 50)),
        concurrency=int(profile.get("concurrency", 5)),
    )
    sla = LoadSla(
        max_avg_latency_s=float(profile.get("max_avg_latency_s", 0.5)),
        max_p95_latency_s=float(profile.get("max_p95_latency_s", 0.9)),
        max_error_rate=float(profile.get("max_error_rate", 0.01)),
    )

    try:
        result = run_load_scenario(scenario)
        assert_sla(result, sla)
    finally:
        client.close()

    print(
        f"{scenario.name} OK | avg={result.average_latency_s:.3f}s "
        f"p95={result.p95_latency_s:.3f}s error_rate={result.error_rate:.2%}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
