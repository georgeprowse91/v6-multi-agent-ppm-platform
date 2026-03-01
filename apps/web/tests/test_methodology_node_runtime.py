import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from methodology_node_runtime import (  # noqa: E402
    RuntimeRegistry,
    _validate_registry,
    load_methodology_node_runtime_registry,
    resolve_runtime,
)


def test_runtime_registry_loads_and_enforces_view_coverage() -> None:
    registry = load_methodology_node_runtime_registry()
    assert registry.mappings

    view_keys = {
        (
            mapping.key.methodology_id,
            mapping.key.stage_id,
            mapping.key.activity_id,
            mapping.key.task_id,
        )
        for mapping in registry.mappings
        if mapping.key.lifecycle_event == "view"
    }
    assert view_keys


def test_resolve_runtime_returns_complete_contract_for_multiple_methodologies() -> None:
    adaptive = resolve_runtime(
        "adaptive",
        "0.5-iteration-sprint-delivery-repeating-cycle",
        "0.5.1-sprint-iteration-planning",
        None,
        "generate",
    )
    predictive = resolve_runtime(
        "predictive",
        "0.4-planning",
        "0.4.2-schedule-planning-agent",
        None,
        "generate",
    )
    hybrid = resolve_runtime(
        "hybrid",
        "0.8-release-readiness-deployment-transition-gate-2-3-4-depending-on-model",
        "0.8.8-release-sign-off-and-gate-approval-to-proceed-close",
        None,
        "review",
    )

    for payload in (adaptive, predictive, hybrid):
        assert payload["template_ids"]
        assert "agent_workflow" in payload
        assert "connectors" in payload
        assert "canvas" in payload
        assert "assistant" in payload


def test_missing_runtime_mapping_fails_with_clear_error() -> None:
    with pytest.raises(ValueError, match="No runtime mapping found"):
        resolve_runtime(
            "adaptive",
            "0.5-iteration-sprint-delivery-repeating-cycle",
            "0.5.1-sprint-iteration-planning",
            None,
            "archive",
        )


def test_validation_fails_when_task_view_mapping_missing(monkeypatch) -> None:
    registry = load_methodology_node_runtime_registry()
    task_view_mapping = next(
        mapping
        for mapping in registry.mappings
        if mapping.key.task_id is not None and mapping.key.lifecycle_event == "view"
    )
    missing_task_view = [
        mapping.model_dump(mode="json")
        for mapping in registry.mappings
        if mapping != task_view_mapping
    ]
    candidate = RuntimeRegistry.model_validate({"mappings": missing_task_view})

    with pytest.raises(ValueError, match="missing_lifecycle_events=view"):
        _validate_registry(candidate)
