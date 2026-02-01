"""AI/ML model registry and pipeline helpers."""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelTask(str, Enum):
    SCHEDULE_ESTIMATION = "schedule_estimation"
    RISK_PREDICTION = "risk_prediction"
    VENDOR_SCORING = "vendor_scoring"
    DEFECT_CLASSIFICATION = "defect_classification"
    PROCESS_DISCOVERY = "process_discovery"


class ModelStage(str, Enum):
    TRAINED = "trained"
    EVALUATED = "evaluated"
    DEPLOYED = "deployed"


class AIModelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_MODEL_", env_file=".env")

    provider: str = "in_memory"
    azure_ml_endpoint: Optional[str] = None
    azure_ml_api_key: Optional[str] = None
    default_task: ModelTask = ModelTask.SCHEDULE_ESTIMATION


@dataclass
class ModelRecord:
    model_id: str
    task: ModelTask
    stage: ModelStage
    trained_at: datetime
    metrics: Dict[str, Any]
    artifact: Dict[str, Any]


@dataclass
class TrainingResult:
    record: ModelRecord
    summary: Dict[str, Any]


@dataclass
class EvaluationResult:
    model_id: str
    metrics: Dict[str, Any]
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ModelRegistry:
    """In-memory registry for model artifacts."""

    def __init__(self) -> None:
        self._records: Dict[str, ModelRecord] = {}

    def register(self, record: ModelRecord) -> None:
        self._records[record.model_id] = record

    def get(self, model_id: str) -> Optional[ModelRecord]:
        return self._records.get(model_id)

    def list(self, task: Optional[ModelTask] = None) -> List[ModelRecord]:
        records = list(self._records.values())
        if task:
            records = [record for record in records if record.task == task]
        return records

    def update_stage(self, model_id: str, stage: ModelStage) -> None:
        record = self._records.get(model_id)
        if not record:
            raise ValueError("Unknown model_id")
        record.stage = stage


class TrainingPipeline:
    """Simple training pipeline for in-memory AI models."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def train(self, task: ModelTask, dataset: Iterable[float]) -> TrainingResult:
        values = list(dataset)
        baseline = statistics.mean(values) if values else 0.0
        variance = statistics.pvariance(values) if len(values) > 1 else 0.0
        model_id = f"model-{uuid.uuid4().hex}"
        record = ModelRecord(
            model_id=model_id,
            task=task,
            stage=ModelStage.TRAINED,
            trained_at=datetime.now(timezone.utc),
            metrics={"baseline": baseline, "variance": variance},
            artifact={"baseline": baseline, "variance": variance},
        )
        self._registry.register(record)
        return TrainingResult(record=record, summary={"samples": len(values), "baseline": baseline})


class EvaluationPipeline:
    """Evaluation pipeline for in-memory models."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def evaluate(self, model_id: str, dataset: Iterable[float]) -> EvaluationResult:
        record = self._registry.get(model_id)
        if not record:
            raise ValueError("Unknown model_id")
        values = list(dataset)
        baseline = record.metrics.get("baseline", 0.0)
        error = statistics.mean([abs(value - baseline) for value in values]) if values else 0.0
        metrics = {"mean_absolute_error": error, "samples": len(values)}
        record.metrics.update(metrics)
        record.stage = ModelStage.EVALUATED
        return EvaluationResult(model_id=model_id, metrics=metrics)


class DeploymentManager:
    """Deployment manager to move models into production."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def deploy(self, model_id: str) -> ModelRecord:
        self._registry.update_stage(model_id, ModelStage.DEPLOYED)
        record = self._registry.get(model_id)
        if not record:
            raise ValueError("Unknown model_id")
        return record


class InferenceService:
    """Inference service for running predictions."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def predict(self, model_id: str, features: Dict[str, Any]) -> float:
        record = self._registry.get(model_id)
        if not record:
            raise ValueError("Unknown model_id")
        baseline = float(record.artifact.get("baseline", 0.0))
        weight = float(features.get("weight", 1.0))
        complexity = float(features.get("complexity", 1.0))
        return baseline * weight * complexity


class AIModelService:
    """Unified service for training, evaluating, deploying, and inference."""

    def __init__(
        self,
        settings: Optional[AIModelSettings] = None,
        registry: Optional[ModelRegistry] = None,
    ) -> None:
        self.settings = settings or AIModelSettings()
        self.registry = registry or ModelRegistry()
        self.training = TrainingPipeline(self.registry)
        self.evaluation = EvaluationPipeline(self.registry)
        self.deployment = DeploymentManager(self.registry)
        self.inference = InferenceService(self.registry)

    def train_model(self, task: ModelTask, dataset: Iterable[float]) -> TrainingResult:
        return self.training.train(task, dataset)

    def evaluate_model(self, model_id: str, dataset: Iterable[float]) -> EvaluationResult:
        return self.evaluation.evaluate(model_id, dataset)

    def deploy_model(self, model_id: str) -> ModelRecord:
        return self.deployment.deploy(model_id)

    def predict(self, model_id: str, features: Dict[str, Any]) -> float:
        return self.inference.predict(model_id, features)


__all__ = [
    "AIModelSettings",
    "AIModelService",
    "DeploymentManager",
    "EvaluationPipeline",
    "EvaluationResult",
    "InferenceService",
    "ModelRecord",
    "ModelRegistry",
    "ModelStage",
    "ModelTask",
    "TrainingPipeline",
    "TrainingResult",
]
