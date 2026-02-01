"""Azure ML integration helpers for scheduling models."""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ModelArtifact:
    model_id: str
    trained_at: datetime
    metadata: Dict[str, Any]
    base_duration: float
    performance_factor: float


class AzureMLDurationEstimator:
    """In-memory Azure ML duration estimator."""

    def __init__(self) -> None:
        self._registry: Dict[str, ModelArtifact] = {}

    def train(
        self,
        historical_durations: List[float],
        team_performance: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelArtifact:
        baseline = statistics.mean(historical_durations) if historical_durations else 5.0
        performance = team_performance if team_performance > 0 else 1.0
        performance_factor = max(0.5, min(1.5, 1 / performance))
        artifact = ModelArtifact(
            model_id=f"ml-{uuid.uuid4().hex}",
            trained_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            base_duration=baseline,
            performance_factor=performance_factor,
        )
        self._registry[artifact.model_id] = artifact
        return artifact

    def predict(self, model_id: str, complexity: str) -> float:
        artifact = self._registry.get(model_id)
        if not artifact:
            raise ValueError("Unknown model_id")
        complexity_factor = {"low": 0.8, "medium": 1.0, "high": 1.3}.get(complexity, 1.0)
        return artifact.base_duration * artifact.performance_factor * complexity_factor

    def get_model(self, model_id: str) -> Optional[ModelArtifact]:
        return self._registry.get(model_id)


class AzureMLClient:
    """API wrapper for Azure ML duration models."""

    def __init__(self, estimator: Optional[AzureMLDurationEstimator] = None) -> None:
        self.estimator = estimator or AzureMLDurationEstimator()

    def train_duration_model(
        self,
        historical_durations: List[float],
        team_performance: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelArtifact:
        return self.estimator.train(historical_durations, team_performance, metadata)

    def predict_duration(self, model_id: str, complexity: str) -> float:
        return self.estimator.predict(model_id, complexity)


__all__ = ["AzureMLClient", "AzureMLDurationEstimator", "ModelArtifact"]
