from pathlib import Path

import pytest
import yaml

from agents.runtime.eval.run_eval import EvaluationError, run_manifest


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload))


def test_eval_harness_supports_expected_outputs(tmp_path: Path) -> None:
    fixture = tmp_path / "agent-output.yaml"
    _write_yaml(
        fixture,
        {
            "input": {"query": "status"},
            "actual_output": {"summary": "all green", "confidence": 0.93},
        },
    )

    manifest = tmp_path / "manifest.yaml"
    _write_yaml(
        manifest,
        {
            "evaluations": [
                {
                    "id": "output-check",
                    "fixture": fixture.name,
                    "expected_outputs": [
                        {"field": "summary", "contains": "green"},
                        {"field": "confidence", "equals": 0.93},
                    ],
                }
            ]
        },
    )

    assert run_manifest(manifest) == 1


def test_eval_harness_runs_multi_agent_flow_manifest(tmp_path: Path) -> None:
    step1 = tmp_path / "step1.yaml"
    step2 = tmp_path / "step2.yaml"
    _write_yaml(step1, {"actual_output": {"intent": "financial_query"}})
    _write_yaml(step2, {"actual_output": {"execution": {"successful_agents": 2}}})

    manifest = tmp_path / "manifest.yaml"
    _write_yaml(
        manifest,
        {
            "evaluations": [],
            "multi_agent_flows": [
                {
                    "id": "full-flow",
                    "steps": [
                        {
                            "id": "intent",
                            "fixture": step1.name,
                            "expected_outputs": [{"field": "intent", "equals": "financial_query"}],
                        },
                        {
                            "id": "orchestrate",
                            "fixture": step2.name,
                            "expected_outputs": [
                                {"field": "execution.successful_agents", "equals": 2}
                            ],
                        },
                    ],
                }
            ],
        },
    )

    assert run_manifest(manifest) == 1


def test_eval_harness_reports_expected_output_failures(tmp_path: Path) -> None:
    fixture = tmp_path / "agent-output.yaml"
    _write_yaml(fixture, {"actual_output": {"summary": "warning state"}})

    manifest = tmp_path / "manifest.yaml"
    _write_yaml(
        manifest,
        {
            "evaluations": [
                {
                    "id": "output-check",
                    "fixture": fixture.name,
                    "expected_outputs": [{"field": "summary", "contains": "green"}],
                }
            ]
        },
    )

    with pytest.raises(EvaluationError, match="output-check"):
        run_manifest(manifest)
