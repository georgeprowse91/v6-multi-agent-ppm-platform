import subprocess
import sys
from pathlib import Path


def _run(script: str, *args: str) -> None:
    script_path = Path(script)
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_policies() -> None:
    _run("ops/scripts/validate-policies.py")


def test_validate_helm_charts() -> None:
    _run("ops/scripts/validate-helm-charts.py")


def test_validate_analytics_jobs() -> None:
    _run("ops/scripts/validate-analytics-jobs.py")


def test_validate_workflows() -> None:
    _run("ops/scripts/validate-workflows.py")


def test_validate_connector_sandbox() -> None:
    _run("ops/scripts/validate-connector-sandbox.py")


def test_validate_prompts() -> None:
    _run("ops/scripts/validate-prompts.py")


def test_validate_examples() -> None:
    _run("ops/scripts/validate-examples.py")


def test_validate_github_workflows() -> None:
    _run("ops/scripts/validate-github-workflows.py")
