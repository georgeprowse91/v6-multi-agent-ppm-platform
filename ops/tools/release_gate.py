from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "release-gate"
REQUIRED_SERVICES = [
    "api",
    "orchestration-service",
    "workflow-engine",
    "data-service",
    "policy-engine",
    "document-service",
    "notification-service",
]


@dataclass
class CheckResult:
    area: str
    command: str
    status: str
    duration_seconds: float
    output: str



def _run(area: str, command: str) -> CheckResult:
    started = time.monotonic()
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        shell=True,
        text=True,
        capture_output=True,
    )
    duration = time.monotonic() - started
    combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
    status = "pass" if proc.returncode == 0 else "fail"
    return CheckResult(
        area=area,
        command=command,
        status=status,
        duration_seconds=round(duration, 2),
        output=combined,
    )


def _check_profile_manifest(profile: str) -> CheckResult:
    import yaml  # local import to avoid adding hard runtime dependency at import time

    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    services = compose.get("services", {})

    missing = []
    for service in REQUIRED_SERVICES:
        profiles = services.get(service, {}).get("profiles", [])
        if profile not in profiles:
            missing.append(service)

    output = (
        f"{profile} profile contains required services: {', '.join(REQUIRED_SERVICES)}"
        if not missing
        else f"Missing services from profile '{profile}': {', '.join(missing)}"
    )
    return CheckResult(
        area="profile-drift-check",
        command=f"validate docker-compose profile ({profile})",
        status="pass" if not missing else "fail",
        duration_seconds=0.0,
        output=output,
    )


def _quality_report(profile: str, checks: list[CheckResult]) -> dict:
    by_area: dict[str, str] = {}
    for check in checks:
        prior = by_area.get(check.area, "pass")
        if check.status == "fail" or prior == "fail":
            by_area[check.area] = "fail"
        else:
            by_area[check.area] = "pass"

    ordered_areas = [
        "schema-config-validation",
        "unit-integration-security",
        "contract-checks",
        "generated-doc-freshness",
        "profile-drift-check",
        "full-profile-smoke-workflow",
        "restart-resilience",
        "idempotency-behavior",
        "connector-failure-isolation",
        "workflow-resume-after-restart",
    ]
    area_report = {
        area: by_area.get(area, "not-run")
        for area in ordered_areas
    }

    return {
        "profile": profile,
        "generated_at_epoch": int(time.time()),
        "overall_status": "fail" if "fail" in area_report.values() else "pass",
        "capability_areas": area_report,
        "checks": [check.__dict__ for check in checks],
    }


def run_release_gate(profile: str, report_path: Path) -> int:
    checks: list[CheckResult] = []

    pipeline = [
        ("schema-config-validation", "python scripts/validate-schemas.py"),
        ("schema-config-validation", "python ops/scripts/validate_config.py"),
        ("schema-config-validation", "python ops/tools/config_validator.py"),
        ("unit-integration-security", "make test-unit"),
        ("unit-integration-security", "make test-integration"),
        ("unit-integration-security", "make test-security"),
        ("contract-checks", "pytest tests/contract -v"),
        ("generated-doc-freshness", "make check-generated-docs"),
    ]

    smoke_command = (
        "python ops/scripts/quickstart_smoke.py"
        if profile == "core"
        else "python ops/scripts/full_platform_demo_smoke.py"
    )
    pipeline.extend(
        [
            ("full-profile-smoke-workflow", smoke_command),
            (
                "restart-resilience",
                "pytest tests/integration/test_orchestrator_persistence.py::test_orchestrator_state_persists_across_restart -v",
            ),
            (
                "idempotency-behavior",
                "pytest tests/e2e/test_user_journey.py::test_workflow_idempotency_prevents_duplicate_side_effects -v",
            ),
            (
                "connector-failure-isolation",
                "pytest tests/integration/test_circuit_breaker.py::test_circuit_breaker_opens_and_recovers -v",
            ),
            (
                "workflow-resume-after-restart",
                "pytest tests/e2e/test_user_journey.py::test_workflow_resume_after_mid_workflow_failure -v",
            ),
        ]
    )

    checks.append(_check_profile_manifest(profile))

    for area, command in pipeline:
        result = _run(area, command)
        checks.append(result)
        print(f"[{result.status}] {area}: {command}")
        if result.status == "fail":
            break

    report = _quality_report(profile, checks)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    if report["overall_status"] == "fail":
        print(f"Release gate failed for profile '{profile}'. See report: {report_path}")
        return 1

    print(f"Release gate passed for profile '{profile}'. Report: {report_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run release maturity gate and emit quality report")
    parser.add_argument("--profile", choices=["core", "full"], default="full")
    parser.add_argument(
        "--report",
        default=None,
        help="Optional path to quality report JSON (default: artifacts/release-gate/quality-report-<profile>.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = Path(args.report) if args.report else ARTIFACT_DIR / f"quality-report-{args.profile}.json"
    raise SystemExit(run_release_gate(args.profile, report))
