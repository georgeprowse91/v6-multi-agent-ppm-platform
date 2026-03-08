"""Demand Intake Agent - Pure utility functions."""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

DEFAULT_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "for",
        "of",
        "in",
        "on",
        "with",
        "via",
        "from",
        "is",
        "are",
    }
)


def combine_demand_text(request_data: dict[str, Any]) -> str:
    """Combine title, description, and business_objective into a single searchable string."""
    title = request_data.get("title", "")
    description = request_data.get("description", "")
    objective = request_data.get("business_objective", "")
    return f"{title} {description} {objective}".strip().lower()


def tokenize(text: str, stopwords: frozenset[str] = DEFAULT_STOPWORDS) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens, removing stopwords."""
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    return [token for token in tokens if token and token not in stopwords]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def semantic_similarity(
    query: str,
    corpus: list[str],
    stopwords: frozenset[str] = DEFAULT_STOPWORDS,
) -> list[float]:
    """Compute TF-IDF-weighted cosine similarity between a query and a corpus of documents."""
    tokens_list = [tokenize(text, stopwords) for text in corpus + [query]]
    vocabulary = sorted({token for tokens in tokens_list for token in tokens})

    if not vocabulary:
        return [0.0 for _ in corpus]

    doc_freq = {term: 0 for term in vocabulary}
    for tokens in tokens_list:
        for term in set(tokens):
            doc_freq[term] += 1

    total_docs = len(tokens_list)
    idf = {term: math.log((total_docs + 1) / (doc_freq[term] + 1)) + 1 for term in vocabulary}

    vectors = []
    for tokens in tokens_list:
        term_counts: dict[str, int] = {}
        for token in tokens:
            term_counts[token] = term_counts.get(token, 0) + 1
        vector = [term_counts.get(term, 0) * idf[term] for term in vocabulary]
        vectors.append(vector)

    query_vector = vectors[-1]
    results = []
    for vector in vectors[:-1]:
        similarity = cosine_similarity(query_vector, vector)
        results.append(similarity)
    return results


def build_duplicate_rationale(
    request_data: dict[str, Any],
    candidate_data: dict[str, Any],
    similarity: float,
    stopwords: frozenset[str] = DEFAULT_STOPWORDS,
) -> dict[str, Any]:
    """Build a human-readable rationale explaining why two demand items are duplicates."""
    request_tokens = set(tokenize(combine_demand_text(request_data), stopwords))
    candidate_tokens = set(tokenize(combine_demand_text(candidate_data), stopwords))
    overlapping_terms = sorted(request_tokens & candidate_tokens)
    matched_fields = []
    for field in ("title", "description", "business_objective"):
        request_field_tokens = set(tokenize(request_data.get(field, ""), stopwords))
        candidate_field_tokens = set(tokenize(candidate_data.get(field, ""), stopwords))
        if request_field_tokens & candidate_field_tokens:
            matched_fields.append(field)
    return {
        "similarity_score": round(similarity, 3),
        "overlapping_terms": overlapping_terms[:8],
        "matched_fields": matched_fields,
    }


def strip_duplicate_rationale(duplicates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip internal rationale data from duplicate candidates before returning to callers."""
    return [
        {key: value for key, value in item.items() if key != "rationale"} for item in duplicates
    ]


def generate_demand_id() -> str:
    """Generate a unique demand ID with timestamp and random suffix."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"DEM-{timestamp}-{uuid.uuid4().hex[:8]}"
