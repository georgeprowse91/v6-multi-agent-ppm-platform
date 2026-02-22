from __future__ import annotations

from pathlib import Path

import pytest
from llm.evaluation import EvaluationSample, PromptEvaluationHarness
from llm.prompts import PromptRegistry


@pytest.fixture
def registry(tmp_path: Path) -> PromptRegistry:
    return PromptRegistry(registry_path=tmp_path / "registry.json")


def test_template_rendering_with_defaults_and_validation(registry: PromptRegistry) -> None:
    registry.register_prompt(
        name="welcome",
        content="Hello {{ user }} from {{ team }}",
        owner="pm",
        created_by="qa",
        defaults={"team": "platform"},
        required_variables=["user"],
    )

    assert registry.render_prompt("welcome", {"user": "Ada"}) == "Hello Ada from platform"

    with pytest.raises(ValueError, match="Missing required variables"):
        registry.render_prompt("welcome", {})


def test_version_lineage_and_environment_scoping(registry: PromptRegistry) -> None:
    first = registry.register_prompt(
        name="classifier",
        content="v1 {{ text }}",
        owner="ml",
        created_by="dev",
        environment_tags=["dev"],
    )
    promoted = registry.promote_prompt("classifier", first.version, "prod")

    assert promoted.version > first.version
    prod_prompt = registry.get_prompt("classifier", environment="prod")
    assert "prod" in prod_prompt.environment_tags


def test_evaluation_harness_persists_records(registry: PromptRegistry) -> None:
    created = registry.register_prompt(
        name="qa",
        content="Answer {{ question }}",
        owner="qa",
        created_by="tester",
    )
    harness = PromptEvaluationHarness(registry)
    result = harness.run_batch(
        prompt_name="qa",
        version=created.version,
        run_id="run-1",
        samples=[
            EvaluationSample(input_variables={}, output="Yes", expected_output="Yes"),
            EvaluationSample(input_variables={}, output="No", expected_output="Yes"),
        ],
    )
    assert result.average_score == 0.5
