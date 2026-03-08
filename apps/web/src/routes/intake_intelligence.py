"""Intelligent demand intake — duplicate detection, auto-classification, business case generation.

Production-grade implementation using:
- VectorSearchIndex (128-dim LocalEmbeddingService) for semantic duplicate detection
- NaiveBayesTextClassifier trained on corpus for classification fallback
- LLM for primary classification and business case generation
- Real intake store and project data for the demand corpus
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from routes._deps import _load_projects, logger
from routes._llm_helpers import llm_complete_json

router = APIRouter(tags=["intake-intelligence"])

# ---------------------------------------------------------------------------
# Embedding and classification infrastructure
# ---------------------------------------------------------------------------

_embedding_service = None
_search_index = None
_classifier = None


def _get_embedding_service():
    """Lazy-init the LocalEmbeddingService."""
    global _embedding_service
    if _embedding_service is not None:
        return _embedding_service
    try:
        from integration_services import LocalEmbeddingService

        _embedding_service = LocalEmbeddingService(dimensions=128, seed=42)
    except ImportError:
        # Inline fallback
        _embedding_service = _FallbackEmbeddingService()
    return _embedding_service


def _get_search_index():
    """Lazy-init the VectorSearchIndex with corpus data."""
    global _search_index
    if _search_index is not None:
        return _search_index

    embedding_svc = _get_embedding_service()

    try:
        from integration_services import VectorSearchIndex

        _search_index = VectorSearchIndex(embedding_svc)
    except ImportError:
        _search_index = _FallbackSearchIndex(embedding_svc)

    # Populate with corpus
    _ensure_corpus()
    for demand in _demand_corpus:
        text = f"{demand.get('title', '')} {demand.get('description', '')}"
        if text.strip():
            _search_index.add(
                demand.get(
                    "id",
                    f"demand-{len(_search_index._vectors) if hasattr(_search_index, '_vectors') else 0}",
                ),
                text,
                demand,
            )

    return _search_index


def _get_classifier():
    """Lazy-init NaiveBayes classifier trained on corpus + training data."""
    global _classifier
    if _classifier is not None:
        return _classifier

    labels = ["strategic", "operational", "regulatory", "maintenance", "innovation"]

    try:
        from integration_services import NaiveBayesTextClassifier

        _classifier = NaiveBayesTextClassifier(labels)
    except ImportError:
        _classifier = None
        return None

    # Training data — representative samples for each category
    training_samples = [
        (
            "digital transformation cloud migration competitive advantage market expansion",
            "strategic",
        ),
        ("AI machine learning platform modernization growth strategy", "strategic"),
        ("new market entry competitive positioning brand strategy", "strategic"),
        ("process automation workflow optimization efficiency improvement", "operational"),
        ("internal tooling team collaboration mobile app for field workers", "operational"),
        ("system integration data pipeline consolidation reporting", "operational"),
        ("GDPR compliance privacy regulation data protection", "regulatory"),
        ("SOX audit financial compliance reporting controls", "regulatory"),
        ("HIPAA healthcare patient data security regulatory requirement", "regulatory"),
        ("bug fix patch upgrade legacy system technical debt refactor", "maintenance"),
        ("infrastructure upgrade server migration performance optimization", "maintenance"),
        ("security patching vulnerability remediation system hardening", "maintenance"),
        ("research prototype experiment emerging technology pilot", "innovation"),
        ("blockchain IoT edge computing quantum computing POC", "innovation"),
        ("machine learning research natural language processing computer vision", "innovation"),
    ]

    # Also train on corpus data
    _ensure_corpus()
    for demand in _demand_corpus:
        cat = demand.get("category", "")
        if cat in labels:
            text = f"{demand.get('title', '')} {demand.get('description', '')}"
            if text.strip():
                training_samples.append((text, cat))

    _classifier.fit(training_samples)
    return _classifier


# ---------------------------------------------------------------------------
# Fallback implementations when integration_services not importable
# ---------------------------------------------------------------------------


class _FallbackEmbeddingService:
    """Minimal embedding service using hash-based vectors."""

    dimensions = 128

    def embed(self, texts):
        import hashlib

        results = []
        for text in texts:
            vector = [0.0] * 128
            for token in text.lower().split():
                idx = int(hashlib.md5(token.encode()).hexdigest()[:8], 16) % 128
                vector[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vector))
            if norm > 0:
                vector = [v / norm for v in vector]
            results.append(vector)
        return results


class _FallbackSearchIndex:
    """Minimal vector search index."""

    def __init__(self, embedding_service):
        self._embedding = embedding_service
        self._vectors = {}
        self._metadata = {}

    def add(self, doc_id, text, metadata):
        self._vectors[doc_id] = self._embedding.embed([text])[0]
        self._metadata[doc_id] = metadata

    def search(self, query, *, top_k=5):
        if not self._vectors:
            return []
        query_vec = self._embedding.embed([query])[0]
        scored = []
        for doc_id, vec in self._vectors.items():
            dot = sum(a * b for a, b in zip(query_vec, vec))
            scored.append(
                type(
                    "Result",
                    (),
                    {"doc_id": doc_id, "score": dot, "metadata": self._metadata[doc_id]},
                )()
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# Demand corpus — loaded from real intake store + projects
# ---------------------------------------------------------------------------
_demand_corpus: list[dict[str, Any]] = []
_corpus_initialized = False


def _ensure_corpus() -> None:
    global _demand_corpus, _corpus_initialized
    if _corpus_initialized:
        return
    _corpus_initialized = True

    try:
        from routes._deps import intake_store

        items = intake_store.list_requests()
        for item in items:
            if isinstance(item, dict):
                _demand_corpus.append(item)
            elif hasattr(item, "model_dump"):
                _demand_corpus.append(item.model_dump())
    except Exception as exc:
        logger.debug("Intake store unavailable for corpus: %s", exc)

    # Also pull projects as past demands
    projects = _load_projects()
    for p in projects[:20]:
        _demand_corpus.append(
            {
                "id": getattr(p, "id", ""),
                "title": getattr(p, "name", ""),
                "description": getattr(p, "description", "") if hasattr(p, "description") else "",
                "status": getattr(p, "status", "completed"),
                "category": (
                    getattr(p, "methodology", {}).get("type", "operational")
                    if isinstance(getattr(p, "methodology", None), dict)
                    else "operational"
                ),
            }
        )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DuplicateCheckRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class DuplicateMatch(BaseModel):
    demand_id: str
    title: str
    description: str
    status: str
    similarity_score: float


class ClassifyRequest(BaseModel):
    description: str = Field(min_length=1)


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    all_scores: dict[str, float]
    method: str = "fallback"


class BusinessCaseRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = ""


class BusinessCaseSkeleton(BaseModel):
    problem_statement: str
    proposed_solution: str
    expected_benefits: list[str]
    estimated_cost_range: str
    risk_factors: list[str]
    success_criteria: list[str]


# ---------------------------------------------------------------------------
# Jaccard similarity (kept as supplementary signal)
# ---------------------------------------------------------------------------


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/api/intake/check-duplicates")
async def check_duplicates(request: DuplicateCheckRequest) -> list[DuplicateMatch]:
    """Find duplicate/similar demands using vector similarity + Jaccard."""
    logger.info("Duplicate check request: title=%s", request.title)
    combined = f"{request.title} {request.description}"
    index = _get_search_index()

    matches: list[DuplicateMatch] = []
    seen_ids: set[str] = set()

    # Vector search for top candidates
    try:
        vector_results = index.search(combined, top_k=10)
    except Exception:
        logger.exception("Vector search failed for duplicate check")
        vector_results = []
    for result in vector_results:
        demand = result.metadata
        demand_id = demand.get("id", "unknown")
        if demand_id in seen_ids:
            continue
        seen_ids.add(demand_id)

        existing_text = f"{demand.get('title', '')} {demand.get('description', '')}"
        jaccard = _jaccard_similarity(combined, existing_text)

        # Combine vector score and Jaccard (weighted average), capped to [0, 1]
        combined_score = min(max(result.score * 0.7 + jaccard * 0.3, 0.0), 1.0)

        if combined_score > 0.15:
            matches.append(
                DuplicateMatch(
                    demand_id=demand_id,
                    title=demand.get("title", ""),
                    description=demand.get("description", "")[:200],
                    status=demand.get("status", "unknown"),
                    similarity_score=round(combined_score, 3),
                )
            )

    matches.sort(key=lambda m: m.similarity_score, reverse=True)
    return matches[:5]


@router.post("/api/intake/auto-classify")
async def auto_classify(request: ClassifyRequest) -> ClassificationResult:
    """Auto-classify using LLM → NaiveBayes → keyword matching fallback chain."""
    logger.info("Auto-classify request: description_length=%d", len(request.description))

    # Tier 1: LLM classification
    llm_result = await llm_complete_json(
        "You are a demand classifier for a PPM system. "
        "Classify the description into exactly one category: "
        "strategic, operational, regulatory, maintenance, innovation. "
        'Return JSON: {"category": "...", "confidence": 0.0-1.0, '
        '"all_scores": {"strategic": 0.0, "operational": 0.0, "regulatory": 0.0, '
        '"maintenance": 0.0, "innovation": 0.0}}',
        f"Classify this demand:\n{request.description}",
    )

    if llm_result and llm_result.get("category"):
        return ClassificationResult(
            category=llm_result["category"],
            confidence=float(llm_result.get("confidence", 0.8)),
            all_scores=llm_result.get("all_scores", {llm_result["category"]: 0.8}),
            method="llm",
        )

    # Tier 2: NaiveBayes classifier
    classifier = _get_classifier()
    if classifier is not None:
        best_label, probabilities = classifier.predict(request.description)
        return ClassificationResult(
            category=best_label,
            confidence=round(probabilities.get(best_label, 0.5), 3),
            all_scores={k: round(v, 3) for k, v in probabilities.items()},
            method="naive_bayes",
        )

    # Tier 3: Keyword-based classification
    text = request.description.lower()
    keyword_map = {
        "strategic": [
            "transform",
            "innovate",
            "competitive",
            "market",
            "growth",
            "ai",
            "cloud",
            "digital",
            "strategy",
        ],
        "operational": [
            "process",
            "efficiency",
            "integrate",
            "automate",
            "workflow",
            "team",
            "internal",
            "mobile",
        ],
        "regulatory": [
            "compliance",
            "gdpr",
            "sox",
            "audit",
            "regulation",
            "privacy",
            "retention",
            "security",
            "hipaa",
        ],
        "maintenance": ["fix", "patch", "upgrade", "maintain", "legacy", "debt", "refactor", "bug"],
        "innovation": [
            "research",
            "prototype",
            "experiment",
            "pilot",
            "emerging",
            "ml",
            "blockchain",
        ],
    }

    scores: dict[str, float] = {}
    for cat, keywords in keyword_map.items():
        matches = sum(1 for kw in keywords if kw in text)
        scores[cat] = round(matches / max(len(keywords), 1), 3)

    best_cat = max(scores, key=lambda k: scores[k])
    confidence = scores[best_cat]
    if confidence < 0.1:
        best_cat = "operational"
        confidence = 0.3

    return ClassificationResult(
        category=best_cat,
        confidence=round(min(confidence * 3, 0.95), 2),
        all_scores=scores,
        method="keyword",
    )


@router.post("/api/intake/generate-business-case")
async def generate_business_case(request: BusinessCaseRequest) -> BusinessCaseSkeleton:
    """Generate a business case skeleton using LLM."""
    logger.info("Business case generation request: title=%s", request.title)
    llm_result = await llm_complete_json(
        "You are a business case writer for enterprise projects. "
        "Generate a structured business case skeleton. "
        'Return JSON: {"problem_statement": "...", "proposed_solution": "...", '
        '"expected_benefits": ["..."], "estimated_cost_range": "$X - $Y", '
        '"risk_factors": ["..."], "success_criteria": ["..."]}',
        f"Title: {request.title}\n"
        f"Description: {request.description}\n"
        f"Category: {request.category or 'not specified'}\n\n"
        "Generate a specific, realistic business case for this demand.",
    )

    if llm_result and llm_result.get("problem_statement"):
        return BusinessCaseSkeleton.model_validate(llm_result)

    # Fallback
    return BusinessCaseSkeleton(
        problem_statement=f"The organization needs to address: {request.description[:200]}",
        proposed_solution=f"Implement '{request.title}' leveraging the platform's agent infrastructure.",
        expected_benefits=[
            "Improved operational efficiency",
            "Reduced manual effort through automation",
            "Enhanced visibility and decision-making",
        ],
        estimated_cost_range="$50,000 — $250,000 (refine after scoping)",
        risk_factors=[
            "Integration complexity with existing systems",
            "Resource availability for implementation",
            "Change management and user adoption",
        ],
        success_criteria=[
            "Solution deployed within agreed timeline",
            "User adoption rate exceeds 80% within 3 months",
            "Measurable improvement in target KPIs",
        ],
    )
