"""Tests for intake intelligence (Enhancement 6).

Tests cover Jaccard similarity, vector search index integration,
NaiveBayes classification fallback, and the duplicate detection pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


# --- Error path and edge case tests ---


def test_jaccard_similarity_case_insensitive():
    """Jaccard should be case-insensitive."""
    score = _jaccard_similarity("Hello World", "hello world")
    assert score == 1.0


def test_jaccard_similarity_both_empty():
    """Both strings empty should return 0.0."""
    assert _jaccard_similarity("", "") == 0.0


def test_jaccard_similarity_symmetric():
    """Similarity should be the same regardless of order."""
    s1 = _jaccard_similarity("cloud migration", "migration cloud strategy")
    s2 = _jaccard_similarity("migration cloud strategy", "cloud migration")
    assert s1 == s2


def test_fallback_embedding_different_texts():
    """Different texts should produce different embeddings."""
    svc = _mod._FallbackEmbeddingService()
    vecs = svc.embed(["cloud migration project", "lunch menu options"])
    assert vecs[0] != vecs[1]


def test_fallback_embedding_empty_text():
    """Empty text should produce a valid vector."""
    svc = _mod._FallbackEmbeddingService()
    vecs = svc.embed([""])
    assert len(vecs) == 1
    assert len(vecs[0]) == 128


def test_fallback_search_empty_index():
    """Searching an empty index should return empty results."""
    svc = _mod._FallbackEmbeddingService()
    index = _mod._FallbackSearchIndex(svc)
    results = index.search("cloud migration", top_k=5)
    assert results == []


def test_fallback_search_top_k_limit():
    """Search should respect top_k limit."""
    svc = _mod._FallbackEmbeddingService()
    index = _mod._FallbackSearchIndex(svc)
    for i in range(10):
        index.add(f"d{i}", f"document {i} about cloud", {"title": f"Doc {i}"})
    results = index.search("cloud", top_k=3)
    assert len(results) <= 3


def test_fallback_search_scores_non_negative():
    """Search scores should be non-negative."""
    svc = _mod._FallbackEmbeddingService()
    index = _mod._FallbackSearchIndex(svc)
    index.add("d1", "cloud migration", {"title": "Cloud"})
    index.add("d2", "budget review", {"title": "Budget"})
    results = index.search("cloud", top_k=5)
    for r in results:
        assert r.score >= -0.01


def test_duplicate_check_model():
    """DuplicateCheckRequest should require title and description."""
    req = _mod.DuplicateCheckRequest(title="Test", description="A test demand")
    assert req.title == "Test"


def test_business_case_model():
    """BusinessCaseRequest should accept optional category."""
    req = _mod.BusinessCaseRequest(
        title="New Platform", description="Build it", category="strategic"
    )
    assert req.category == "strategic"


def test_classification_result_all_fields():
    """ClassificationResult should carry all score fields."""
    scores = {
        "strategic": 0.6,
        "operational": 0.2,
        "regulatory": 0.1,
        "maintenance": 0.05,
        "innovation": 0.05,
    }
    result = _mod.ClassificationResult(
        category="strategic",
        confidence=0.6,
        all_scores=scores,
        method="keyword",
    )
    assert len(result.all_scores) == 5
