from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from llm.prompts import PromptRegistry


@dataclass(frozen=True)
class EvaluationSample:
    input_variables: dict[str, Any]
    output: str
    expected_output: str | None = None
    rubric_keywords: list[str] | None = None


@dataclass(frozen=True)
class EvaluationResult:
    prompt_name: str
    prompt_version: int
    run_id: str
    samples: int
    average_score: float
    scores: list[float]
    scored_at: str


class PromptEvaluationHarness:
    def __init__(self, registry: PromptRegistry) -> None:
        self.registry = registry

    def run_batch(
        self,
        *,
        prompt_name: str,
        samples: list[EvaluationSample],
        run_id: str,
        scorer: Callable[[EvaluationSample], float] | None = None,
        version: int | None = None,
    ) -> EvaluationResult:
        prompt = self.registry.get_prompt(prompt_name, version=version)
        score_func = scorer or self._default_scorer
        scores = [score_func(sample) for sample in samples]
        result = EvaluationResult(
            prompt_name=prompt_name,
            prompt_version=prompt.version,
            run_id=run_id,
            samples=len(samples),
            average_score=mean(scores) if scores else 0.0,
            scores=scores,
            scored_at=datetime.now(timezone.utc).isoformat(),
        )
        self.registry.append_evaluation_record(asdict(result))
        return result

    @staticmethod
    def _default_scorer(sample: EvaluationSample) -> float:
        if sample.expected_output is not None:
            return (
                1.0
                if sample.output.strip().lower() == sample.expected_output.strip().lower()
                else 0.0
            )
        if sample.rubric_keywords:
            output = sample.output.lower()
            hits = [kw for kw in sample.rubric_keywords if kw.lower() in output]
            return len(hits) / len(sample.rubric_keywords)
        return 0.0
