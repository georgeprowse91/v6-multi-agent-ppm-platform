import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gating import evaluate_activity_access, next_required_activity, stage_progress
from methodologies import get_methodology_map
from workspace_state import build_default_state


def test_prereq_blocks_activity_until_complete_for_wbs_ids():
    methodology_map = get_methodology_map("adaptive")
    state = build_default_state("tenant-a", "demo-1")

    backlog_refinement = "0.4.3-backlog-creation-and-refinement"
    architecture_shaping = "0.4.4-architecture-risk-and-compliance-shaping-as-needed"
    sprint_planning = "0.5.1-sprint-iteration-planning"
    sprint_build = "0.5.2-build-test-within-sprint"
    release_strategy = "0.6.1-define-release-strategy-feature-flags-phased-rollout"

    access = evaluate_activity_access(methodology_map, state, architecture_shaping)
    assert access["allowed"] is False
    assert access["missing_prereqs"] == [backlog_refinement]

    state.activity_completion[backlog_refinement] = True
    access = evaluate_activity_access(methodology_map, state, architecture_shaping)
    assert access["allowed"] is True

    access = evaluate_activity_access(methodology_map, state, sprint_planning)
    assert access["allowed"] is False
    assert access["missing_prereqs"] == [architecture_shaping]

    state.activity_completion[architecture_shaping] = True
    access = evaluate_activity_access(methodology_map, state, sprint_build)
    assert access["allowed"] is False
    assert access["missing_prereqs"] == [sprint_planning]

    access = evaluate_activity_access(methodology_map, state, release_strategy)
    assert access["allowed"] is False
    assert access["missing_prereqs"] == [
        "0.5.5-sprint-retrospective-and-improvement"
    ]


def test_next_required_activity_returns_wbs_prereq():
    methodology_map = get_methodology_map("adaptive")
    state = build_default_state("tenant-a", "demo-1")
    state.current_activity_id = "0.5.2-build-test-within-sprint"
    assert (
        next_required_activity(methodology_map, state)
        == "0.5.1-sprint-iteration-planning"
    )


def test_stage_progress_calculation_with_wbs_stage_id():
    methodology_map = get_methodology_map("adaptive")
    state = build_default_state("tenant-a", "demo-1")
    state.activity_completion["0.4.1-understand-users-and-problem-space"] = True
    progress = stage_progress(methodology_map, state, "0.4-discovery-definition-iterative")
    assert progress["complete_count"] == 1
    assert progress["total_count"] == 4
    assert progress["percent"] == 25.0


def test_methodology_aliases_resolve_to_new_maps():
    adaptive = get_methodology_map("adaptive")
    predictive = get_methodology_map("predictive")

    assert get_methodology_map("adaptive")["id"] == adaptive["id"]
    assert get_methodology_map("predictive")["id"] == predictive["id"]
    assert get_methodology_map("adaptive")["stages"][0]["id"] == adaptive["stages"][0]["id"]
    assert (
        get_methodology_map("predictive")["stages"][0]["id"]
        == predictive["stages"][0]["id"]
    )
