from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tools.load_testing.runner import (
    LoadScenario,
    LoadSla,
    assert_sla,
    load_profile,
    run_load_scenario,
)


def test_healthz_latency_sla() -> None:
    from api.main import app

    profile = load_profile(Path("tests/load/sla_targets.json"))
    client = TestClient(app)

    def _request() -> int:
        response = client.get("/healthz")
        return response.status_code

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
    )

    result = run_load_scenario(scenario)
    assert_sla(result, sla)
