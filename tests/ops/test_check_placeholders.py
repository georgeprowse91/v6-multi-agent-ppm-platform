from __future__ import annotations

from pathlib import Path

from ops.scripts.check_placeholders import main, run_checks


FIXTURES = Path(__file__).parent / "fixtures" / "check_placeholders"


def test_run_checks_passes_for_complete_fixture() -> None:
    violations = run_checks(FIXTURES / "valid")

    assert violations == []


def test_run_checks_reports_placeholder_and_completeness_violations() -> None:
    violations = run_checks(FIXTURES / "invalid")

    assert any("apps/demo-app/README.md:5: forbidden scaffold phrase found" in v for v in violations)
    assert any("services/demo-service/README.md:5: forbidden scaffold phrase found" in v for v in violations)
    assert any("missing configuration section" in v for v in violations)
    assert any("missing run instructions section" in v for v in violations)
    assert any("missing ownership/support metadata" in v for v in violations)


def test_main_returns_failure_exit_code_for_invalid_fixture() -> None:
    exit_code = main(["--root", str(FIXTURES / "invalid")])

    assert exit_code == 1
