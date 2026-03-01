"""Readiness scoring model for lifecycle gate evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any

from integrations.services.integration.ai_models import AIModelService, ModelTask


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = exp(-value)
        return 1 / (1 + z)
    z = exp(value)
    return z / (1 + z)


@dataclass
class ReadinessScoringModel:
    feature_names: list[str] = field(
        default_factory=lambda: [
            "criteria_ratio",
            "schedule_score",
            "cost_score",
            "risk_score",
            "quality_score",
            "resource_score",
        ]
    )
    weights: list[float] = field(default_factory=list)
    bias: float = 0.0
    trained: bool = False
    ai_model_id: str | None = None
    ai_model_task: ModelTask = ModelTask.READINESS_SCORING

    def fit(self, samples: list[dict[str, Any]], iterations: int = 200, lr: float = 0.1) -> None:
        if not samples:
            return
        if not self.weights:
            self.weights = [0.0 for _ in self.feature_names]
        for _ in range(iterations):
            grad_w = [0.0 for _ in self.weights]
            grad_b = 0.0
            for sample in samples:
                features = sample["features"]
                label = float(sample["label"])
                prediction = self.predict(features)
                error = prediction - label
                for idx, name in enumerate(self.feature_names):
                    grad_w[idx] += error * float(features.get(name, 0.0))
                grad_b += error
            scale = 1.0 / max(len(samples), 1)
            for idx in range(len(self.weights)):
                self.weights[idx] -= lr * grad_w[idx] * scale
            self.bias -= lr * grad_b * scale
        self.trained = True

    def predict(self, features: dict[str, Any]) -> float:
        if not self.weights:
            self.weights = [0.0 for _ in self.feature_names]
        linear = self.bias
        for idx, name in enumerate(self.feature_names):
            linear += self.weights[idx] * float(features.get(name, 0.0))
        score = _sigmoid(linear)
        return min(max(score, 0.0), 1.0)

    def build_features(
        self, criteria_status: list[dict[str, Any]], health_data: dict[str, Any] | None
    ) -> dict[str, float]:
        criteria_ratio = (
            sum(1 for criterion in criteria_status if criterion.get("met")) / len(criteria_status)
            if criteria_status
            else 0.0
        )
        metrics = (health_data or {}).get("metrics", {})
        return {
            "criteria_ratio": criteria_ratio,
            "schedule_score": float(metrics.get("schedule", {}).get("score", 0.0)),
            "cost_score": float(metrics.get("cost", {}).get("score", 0.0)),
            "risk_score": float(metrics.get("risk", {}).get("score", 0.0)),
            "quality_score": float(metrics.get("quality", {}).get("score", 0.0)),
            "resource_score": float(metrics.get("resource", {}).get("score", 0.0)),
        }

    def build_readiness_features(
        self,
        project_data: dict[str, Any] | None,
        health_data: dict[str, Any] | None,
        criteria_status: list[dict[str, Any]] | None,
    ) -> dict[str, float]:
        project_data = project_data or {}
        health_metrics = (health_data or {}).get("metrics", {})
        return {
            "scope_complexity": float(project_data.get("scope_complexity", 0.5)),
            "resource_readiness": float(
                project_data.get(
                    "resource_readiness", health_metrics.get("resource", {}).get("score", 0.5)
                )
            ),
            "risk_profile": float(health_metrics.get("risk", {}).get("score", 0.5)),
            "quality_metrics": float(health_metrics.get("quality", {}).get("score", 0.5)),
            "criteria_ratio": float(
                sum(1 for c in (criteria_status or []) if c.get("met"))
                / max(len(criteria_status or []), 1)
            ),
        }

    def train_with_ai_service(
        self, service: AIModelService, training_samples: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not training_samples:
            return {"status": "skipped", "reason": "no_samples"}
        dataset = []
        for sample in training_samples:
            features = sample["features"]
            label = float(sample.get("label", 0.0))
            readiness_value = self._aggregate_readiness_signal(features)
            dataset.append(label * readiness_value)
        result = service.train_model(self.ai_model_task, dataset)
        self.ai_model_id = result.record.model_id
        return {"status": "trained", "model_id": self.ai_model_id, "summary": result.summary}

    def predict_with_ai_service(
        self, service: AIModelService, features: dict[str, Any]
    ) -> float | None:
        if not self.ai_model_id:
            return None
        weight = (
            float(features.get("resource_readiness", 0.5) + features.get("quality_metrics", 0.5))
            / 2
        )
        complexity = (
            float(features.get("scope_complexity", 0.5) + features.get("risk_profile", 0.5)) / 2
        )
        return service.predict(self.ai_model_id, {"weight": weight, "complexity": complexity})

    def _aggregate_readiness_signal(self, features: dict[str, Any]) -> float:
        resource_ready = float(features.get("resource_readiness", 0.5))
        quality = float(features.get("quality_metrics", 0.5))
        scope_complexity = float(features.get("scope_complexity", 0.5))
        risk_profile = float(features.get("risk_profile", 0.5))
        criteria_ratio = float(features.get("criteria_ratio", 0.0))
        return max(
            min(
                (
                    resource_ready
                    + quality
                    + (1 - scope_complexity)
                    + (1 - risk_profile)
                    + criteria_ratio
                )
                / 5,
                1.0,
            ),
            0.0,
        )
