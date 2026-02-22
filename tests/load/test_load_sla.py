from __future__ import annotations

from pathlib import Path

from ops.tools.load_testing.runner import LoadSla, assert_sla, load_profile, run_load_scenario
from tests.load.multi_agent_scenarios import build_multi_agent_flow_scenario


def test_healthz_latency_sla() -> None:
    profile = load_profile(Path("tests/load/sla_targets.json"))
    scenario = build_multi_agent_flow_scenario(profile)

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

    max_step_avg_latency_s = float(
        profile.get("max_step_avg_latency_s", profile["max_avg_latency_s"])
    )
    max_step_error_rate = float(profile.get("max_step_error_rate", profile["max_error_rate"]))
    for step_name, avg_latency in result.step_average_latency_s.items():
        assert avg_latency <= max_step_avg_latency_s, (
            f"Step {step_name} average latency {avg_latency:.3f}s exceeds "
            f"{max_step_avg_latency_s:.3f}s"
        )

    for step_name, step_error_rate in result.step_error_rate.items():
        assert step_error_rate <= max_step_error_rate, (
            f"Step {step_name} error rate {step_error_rate:.2%} exceeds "
            f"{max_step_error_rate:.2%}"
        )
