from __future__ import annotations

from pathlib import Path


def _assert_contains(path: Path, snippets: list[str]) -> None:
    content = path.read_text()
    for snippet in snippets:
        assert snippet in content


def test_deployment_runbook_exists() -> None:
    path = Path("docs/runbooks/deployment.md")
    assert path.exists()
    _assert_contains(path, ["Deployment Runbook", "Pre-deployment", "Rollback"])


def test_secret_init_runbook_exists() -> None:
    path = Path("docs/runbooks/secret-init.md")
    assert path.exists()
    _assert_contains(path, ["Secret Initialization Runbook", "Key Vault", "Validation"])


def test_credential_acquisition_exists() -> None:
    path = Path("docs/runbooks/credential-acquisition.md")
    assert path.exists()
    _assert_contains(path, ["Credential Acquisition Guide", "Azure", "Connector"])


def test_troubleshooting_runbook_exists() -> None:
    path = Path("docs/runbooks/troubleshooting.md")
    assert path.exists()
    _assert_contains(path, ["Troubleshooting Guide", "Authentication", "Escalation"])


def test_secret_rotation_runbook_exists() -> None:
    path = Path("docs/runbooks/secret-rotation.md")
    assert path.exists()
    _assert_contains(path, ["Secret Rotation Runbook", "Rotation cadence", "Emergency rotation"])


def test_monitoring_dashboards_runbook_exists() -> None:
    path = Path("docs/runbooks/monitoring-dashboards.md")
    assert path.exists()
    _assert_contains(path, ["Operational Monitoring Dashboards", "SLO Dashboard"])


def test_disaster_recovery_drill_documented() -> None:
    path = Path("docs/runbooks/disaster-recovery.md")
    assert path.exists()
    _assert_contains(path, ["DR Testing Procedures", "DR drill"])


def test_schema_promotion_rollback_runbook_exists() -> None:
    path = Path("docs/runbooks/schema-promotion-rollback.md")
    assert path.exists()
    _assert_contains(path, ["Schema Promotion Rollback Runbook", "Rollback Procedure", "Verification Checklist"])
