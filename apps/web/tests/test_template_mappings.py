import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from template_mappings import (  # noqa: E402
    get_template_mapping,
    list_templates_for_methodology_node,
    load_template_mappings,
)


def test_template_mappings_load_and_referential_integrity() -> None:
    registry = load_template_mappings()
    assert registry.templates
    assert len(registry.templates) == 3
    assert get_template_mapping("adaptive-software-dev") is not None


def test_list_templates_for_methodology_node_across_methods() -> None:
    adaptive = list_templates_for_methodology_node(
        "adaptive",
        "0.5-iteration-sprint-delivery-repeating-cycle",
        "0.5.1-sprint-iteration-planning",
        task_id=None,
        lifecycle_event="generate",
    )
    predictive = list_templates_for_methodology_node(
        "predictive",
        "0.4-planning",
        "0.4.2-schedule-planning-agent",
        task_id=None,
        lifecycle_event="generate",
    )
    hybrid = list_templates_for_methodology_node(
        "hybrid",
        "0.8-release-readiness-deployment-transition-gate-2-3-4-depending-on-model",
        "0.8.8-release-sign-off-and-gate-approval-to-proceed-close",
        task_id=None,
        lifecycle_event="generate",
    )

    assert any(item.template_id == "adaptive-software-dev" for item in adaptive)
    assert any(item.template_id == "predictive-infrastructure" for item in predictive)
    assert any(item.template_id == "hybrid-transformation" for item in hybrid)
