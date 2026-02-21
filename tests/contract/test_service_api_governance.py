from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SERVICE_ENTRYPOINTS = [
    "services/data-service/src/main.py",
    "services/agent-runtime/src/main.py",
    "services/policy-engine/src/main.py",
    "services/data-sync-service/src/main.py",
    "services/realtime-coedit-service/src/main.py",
    "services/notification-service/src/main.py",
    "services/auth-service/src/main.py",
    "services/data-lineage-service/src/main.py",
    "services/telemetry-service/src/main.py",
    "services/audit-log/src/main.py",
    "services/identity-access/src/main.py",
    "apps/orchestration-service/src/main.py",
    "apps/document-service/src/main.py",
    "apps/workflow-engine/src/main.py",
    "apps/analytics-service/src/main.py",
    "apps/web/src/main.py",
]


@pytest.mark.parametrize("module_path", SERVICE_ENTRYPOINTS)
def test_entrypoints_apply_governance_and_version_contract(module_path: str) -> None:
    source = (REPO_ROOT / module_path).read_text()
    assert "apply_api_governance(app, service_name=" in source, module_path
    assert "version_response_payload(" in source, module_path
    assert "@app.get(\"/version\")" in source, module_path
    assert "\"/healthz\"" in source or "\"/health\"" in source, module_path


@pytest.mark.parametrize("module_path", SERVICE_ENTRYPOINTS)
def test_entrypoints_import_shared_governance_module(module_path: str) -> None:
    source = (REPO_ROOT / module_path).read_text()
    assert "from security.api_governance import" in source, module_path


def test_shared_error_envelope_contract_shape() -> None:
    source = (REPO_ROOT / "packages/security/src/security/errors.py").read_text()
    assert 'payload: dict[str, dict[str, Any]] = {"error": {"message": message, "code": code}}' in source
    assert 'payload["error"]["correlation_id"] = correlation_id' in source
    assert 'headers.setdefault("X-Correlation-ID", correlation_id)' in source
