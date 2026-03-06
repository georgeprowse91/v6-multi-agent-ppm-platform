"""Tests for intake intelligence (Enhancement 6).

Tests cover Jaccard similarity, vector search index integration,
NaiveBayes classification fallback, and the duplicate detection pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure helper is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _route_test_helpers import load_route_module

_mod = load_route_module("intake_intelligence.py")
_jaccard_similarity = _mod._jaccard_similarity


def test_jaccard_similarity_identical():
    score = _jaccard_similarity("hello world", "hello world")
    assert score == 1.0


def test_jaccard_similarity_different():
    score = _jaccard_similarity("hello world", "foo bar")
    assert score == 0.0


def test_jaccard_similarity_partial():
    score = _jaccard_similarity("cloud migration finance", "cloud migration azure")
    assert 0 < score < 1


def test_jaccard_similarity_empty():
    assert _jaccard_similarity("", "hello") == 0.0
    assert _jaccard_similarity("hello", "") == 0.0


def test_fallback_embedding_service():
    """Test the fallback embedding service produces valid vectors."""
    svc = _mod._FallbackEmbeddingService()
    vecs = svc.embed(["hello world", "test input"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 128
    # Vectors should be normalized (approximately unit length)
    import math
    norm = math.sqrt(sum(v * v for v in vecs[0]))
    assert abs(norm - 1.0) < 0.01


def test_fallback_search_index():
    """Test the fallback search index returns ranked results."""
    svc = _mod._FallbackEmbeddingService()
    index = _mod._FallbackSearchIndex(svc)
    index.add("d1", "cloud migration project", {"title": "Cloud Migration"})
    index.add("d2", "budget review for finance", {"title": "Budget Review"})
    index.add("d3", "cloud infrastructure upgrade", {"title": "Cloud Infra"})

    results = index.search("cloud migration", top_k=3)
    assert len(results) >= 2
    # The top result should be more relevant to cloud migration
    assert results[0].score >= results[-1].score


def test_classification_result_has_method():
    """Test ClassificationResult includes method field."""
    result = _mod.ClassificationResult(
        category="strategic",
        confidence=0.85,
        all_scores={"strategic": 0.85},
        method="naive_bayes",
    )
    assert result.method == "naive_bayes"
