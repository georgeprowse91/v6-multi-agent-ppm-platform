from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class LocalEmbeddingService:
    """Lightweight embedding generator using hashing for offline-friendly similarity."""

    def __init__(self, dimensions: int = 128, seed: int = 42) -> None:
        self.dimensions = dimensions
        random.seed(seed)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            vector = [0.0 for _ in range(self.dimensions)]
            for token in _tokenize(text):
                index = hash(token) % self.dimensions
                vector[index] += 1.0
            embeddings.append(_normalize(vector))
        return embeddings


class NaiveBayesTextClassifier:
    """Simple multinomial naive Bayes classifier for text categories."""

    def __init__(self, labels: Iterable[str]) -> None:
        self.labels = list(labels)
        self.label_counts: Counter[str] = Counter()
        self.token_counts: dict[str, Counter[str]] = {label: Counter() for label in self.labels}
        self.total_tokens: dict[str, int] = {label: 0 for label in self.labels}
        self.vocabulary: set[str] = set()

    def fit(self, samples: Iterable[tuple[str, str]]) -> None:
        for text, label in samples:
            if label not in self.token_counts:
                self.token_counts[label] = Counter()
                self.total_tokens[label] = 0
            tokens = _tokenize(text)
            self.label_counts[label] += 1
            self.token_counts[label].update(tokens)
            self.total_tokens[label] += len(tokens)
            self.vocabulary.update(tokens)

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        tokens = _tokenize(text)
        vocab_size = max(len(self.vocabulary), 1)
        total_docs = sum(self.label_counts.values()) or 1
        scores: dict[str, float] = {}
        for label in self.labels:
            label_count = self.label_counts.get(label, 0) + 1
            log_prob = math.log(label_count / (total_docs + len(self.labels)))
            token_counts = self.token_counts.get(label, Counter())
            total_tokens = self.total_tokens.get(label, 0) + vocab_size
            for token in tokens:
                log_prob += math.log((token_counts.get(token, 0) + 1) / total_tokens)
            scores[label] = log_prob
        best_label = max(scores, key=scores.get)
        probabilities = _softmax(scores)
        return best_label, probabilities


@dataclass
class VectorSearchResult:
    doc_id: str
    score: float
    metadata: dict[str, Any]


class VectorSearchIndex:
    """In-memory vector search index for semantic similarity."""

    def __init__(self, embedding_service: LocalEmbeddingService) -> None:
        self.embedding_service = embedding_service
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def add(self, doc_id: str, text: str, metadata: dict[str, Any]) -> None:
        embedding = self.embedding_service.embed([text])[0]
        self._vectors[doc_id] = embedding
        self._metadata[doc_id] = metadata

    def search(self, query: str, *, top_k: int = 5) -> list[VectorSearchResult]:
        if not self._vectors:
            return []
        query_vector = self.embedding_service.embed([query])[0]
        scored = []
        for doc_id, vector in self._vectors.items():
            score = _cosine_similarity(query_vector, vector)
            scored.append(
                VectorSearchResult(doc_id=doc_id, score=score, metadata=self._metadata[doc_id])
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


class NotificationService:
    """Simple notification dispatcher that uses an event bus when available."""

    def __init__(self, event_bus: Any | None = None, default_channel: str = "email") -> None:
        self.event_bus = event_bus
        self.default_channel = default_channel

    async def send(self, message: dict[str, Any]) -> None:
        payload = {
            "channel": message.get("channel", self.default_channel),
            "recipient": message.get("recipient"),
            "subject": message.get("subject"),
            "body": message.get("body"),
            "metadata": message.get("metadata", {}),
            "sent_at": message.get("sent_at"),
        }
        if self.event_bus:
            await self.event_bus.publish("notification.sent", payload)


class DataConnector:
    """Provides access to external datasets using config-defined mock datasets."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}

    def get_cost_data(self, project_type: str) -> dict[str, Any]:
        return self.data.get("cost_data", {}).get(project_type, {})

    def get_benefit_data(self, project_type: str) -> dict[str, Any]:
        return self.data.get("benefit_data", {}).get(project_type, {})

    def get_market_data(self, market: str) -> dict[str, Any]:
        return self.data.get("market_data", {}).get(market, {})

    def get_resource_profiles(self) -> list[dict[str, Any]]:
        return list(self.data.get("resources", []))

    def get_quality_metrics(self) -> list[dict[str, Any]]:
        return list(self.data.get("quality_metrics", []))


class SentimentAnalyzer:
    """Rule-based sentiment analysis for feedback signals."""

    def __init__(self) -> None:
        self.positive = {"good", "great", "excellent", "helpful", "clear", "supportive"}
        self.negative = {"bad", "poor", "confusing", "slow", "unhelpful", "late"}

    def score(self, text: str) -> float:
        tokens = _tokenize(text)
        if not tokens:
            return 0.0
        score = 0
        for token in tokens:
            if token in self.positive:
                score += 1
            if token in self.negative:
                score -= 1
        return score / max(len(tokens), 1)


class ForecastingModel:
    """Simple forecasting using linear trend extrapolation."""

    def forecast(self, series: list[float], periods: int) -> list[float]:
        if not series:
            return [0.0 for _ in range(periods)]
        if len(series) == 1:
            return [series[0] for _ in range(periods)]
        x_values = list(range(len(series)))
        slope, intercept = _linear_regression(x_values, series)
        start = len(series)
        return [slope * (start + i) + intercept for i in range(periods)]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.split() if token.strip()]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    max_score = max(scores.values())
    exp_values = {label: math.exp(value - max_score) for label, value in scores.items()}
    total = sum(exp_values.values()) or 1.0
    return {label: value / total for label, value in exp_values.items()}


def _linear_regression(x_values: list[int], y_values: list[float]) -> tuple[float, float]:
    n = len(x_values)
    if n == 0:
        return 0.0, 0.0
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values) or 1.0
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept
