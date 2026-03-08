from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text()


def test_orchestrator_emits_standard_business_metrics() -> None:
    source = _read("services/orchestration-service/src/orchestrator.py")
    assert (
        "build_business_workflow_metrics" in source
        and "orchestration-service" in source
        and "orchestrator" in source
    )
    assert "self._orchestrator_business_metrics.executions_total.add" in source
    assert "self._orchestrator_business_metrics.execution_duration_seconds.record" in source
    assert '"tenant.id"' in source
    assert '"trace.id"' in source


def test_workflow_service_emits_standard_business_metrics() -> None:
    source = _read("services/workflow-service/src/workflow_runtime.py")
    assert (
        "build_business_workflow_metrics" in source
        and "workflow-service" in source
        and '"workflow"' in source
    )
    assert "self._workflow_business_metrics.executions_total.add" in source
    assert "self._workflow_business_metrics.execution_duration_seconds.record" in source
    assert '"tenant.id"' in source
    assert '"trace.id"' in source


def test_connector_sync_emits_standard_business_metrics() -> None:
    source = _read("agents/operations-management/data-synchronisation-agent/src/data_sync_agent.py")
    assert (
        "build_business_workflow_metrics" in source
        and "data-sync-agent" in source
        and "connector_sync" in source
    )
    assert "self._sync_business_metrics.executions_total.add" in source
    assert "self._sync_business_metrics.execution_duration_seconds.record" in source
    assert '"tenant.id"' in source
    assert '"trace.id"' in source
