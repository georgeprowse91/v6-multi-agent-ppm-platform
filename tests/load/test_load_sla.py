from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urljoin

import httpx

from tools.load_testing.runner import (
    LoadScenario,
    LoadSla,
    assert_sla,
    load_profile,
    run_load_scenario,
)


def test_healthz_latency_sla() -> None:
    profile = load_profile(Path("tests/load/sla_targets.json"))
    base_url = os.getenv(
        "PERFORMANCE_BASE_URL",
        profile.get("base_url") or "https://staging.api.ppm-platform.com",
    )
    target_url = profile.get("target_url", "/api/v1/health")
    request_url = (
        target_url
        if target_url.startswith("http")
        else urljoin(base_url.rstrip("/") + "/", target_url)
    )
    timeout = float(profile.get("timeout_s", 10.0))
    headers: dict[str, str] = {}
    auth_token = os.getenv("PERFORMANCE_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    tenant_id = os.getenv("PERFORMANCE_TENANT_ID")
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    def _request() -> int:
        try:
            response = httpx.get(request_url, timeout=timeout, headers=headers)
            return response.status_code
        except httpx.RequestError:
            return 599

    scenario = LoadScenario(
        name=profile["name"],
        request_fn=_request,
        total_requests=int(profile["total_requests"]),
        concurrency=int(profile["concurrency"]),
    )
    sla = LoadSla(
        max_avg_latency_s=float(profile["max_avg_latency_s"]),
        max_p95_latency_s=float(profile["max_p95_latency_s"]),
        max_error_rate=float(profile["max_error_rate"]),
        min_requests_per_s=(
            float(profile["min_requests_per_s"]) if profile.get("min_requests_per_s") else None
        ),
    )

    result = run_load_scenario(scenario)
    assert_sla(result, sla)
