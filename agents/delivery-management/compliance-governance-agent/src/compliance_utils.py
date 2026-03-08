"""
Compliance & Regulatory Agent - Utility Functions

Shared helpers for ID generation, text embedding, regulation matching,
scoring, RSS parsing, and other cross-cutting concerns.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree

# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_regulation_id() -> str:
    """Generate unique regulation ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"REG-{timestamp}"


async def generate_control_id() -> str:
    """Generate unique control ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CTL-{timestamp}"


async def generate_mapping_id() -> str:
    """Generate unique mapping ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"MAP-{timestamp}"


async def generate_policy_id() -> str:
    """Generate unique policy ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"POL-{timestamp}"


async def generate_audit_id() -> str:
    """Generate unique audit ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"AUD-{timestamp}"


async def generate_evidence_id() -> str:
    """Generate unique evidence ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"EV-{timestamp}"


# ---------------------------------------------------------------------------
# Text embedding / similarity (TF-IDF based)
# ---------------------------------------------------------------------------


def tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def embed_text(text: str) -> dict[str, float]:
    tokens = tokenize_text(text)
    token_counts = Counter(tokens)
    return {token: float(count) for token, count in token_counts.items()}


def cosine_similarity(vector_a: dict[str, float], vector_b: dict[str, float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    intersection = set(vector_a) & set(vector_b)
    dot_product = sum(vector_a[token] * vector_b[token] for token in intersection)
    magnitude_a = math.sqrt(sum(value * value for value in vector_a.values()))
    magnitude_b = math.sqrt(sum(value * value for value in vector_b.values()))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


async def build_control_embeddings(
    control_registry: dict[str, Any],
) -> dict[str, dict[str, float]]:
    if not control_registry:
        return {}
    corpus_tokens = {
        control_id: tokenize_text(
            " ".join(
                filter(
                    None,
                    [
                        control.get("description", ""),
                        control.get("regulation", ""),
                        control.get("control_type", ""),
                    ],
                )
            )
        )
        for control_id, control in control_registry.items()
    }

    document_frequencies: Counter[str] = Counter()
    for tokens in corpus_tokens.values():
        document_frequencies.update(set(tokens))

    total_docs = len(corpus_tokens)
    embeddings: dict[str, dict[str, float]] = {}
    for control_id, tokens in corpus_tokens.items():
        token_counts = Counter(tokens)
        vector: dict[str, float] = {}
        for token, count in token_counts.items():
            idf = math.log((total_docs + 1) / (1 + document_frequencies[token])) + 1
            vector[token] = count * idf
        embeddings[control_id] = vector

    return embeddings


# ---------------------------------------------------------------------------
# Regulation matching
# ---------------------------------------------------------------------------


def build_project_profile(project_id: str, mapping_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "industry": mapping_data.get("industry", ""),
        "geography": mapping_data.get("geography", mapping_data.get("region", "")),
        "data_types": mapping_data.get("data_types", []),
        "data_sensitivity": mapping_data.get("data_sensitivity", "unknown"),
        "hosting": mapping_data.get("hosting", ""),
        "process_id": mapping_data.get("process_id"),
        "process_type": mapping_data.get("process_type", ""),
    }


def matches_regulation(project_profile: dict[str, Any], regulation: dict[str, Any]) -> bool:
    rules = regulation.get("applicability_rules", {})
    if rules.get("applies_to_all"):
        return True

    industry = str(project_profile.get("industry", "")).lower()
    geography = str(project_profile.get("geography", "")).lower()
    data_types = [str(item).lower() for item in project_profile.get("data_types", [])]
    data_sensitivity = str(project_profile.get("data_sensitivity", "")).lower()

    jurisdiction_filter = [str(item).lower() for item in rules.get("jurisdiction_filter", [])]
    industry_filter = [str(item).lower() for item in rules.get("industry_filter", [])]
    data_sensitivity_filter = [
        str(item).lower() for item in rules.get("data_sensitivity_filter", [])
    ]

    jurisdiction_match = not jurisdiction_filter or geography in jurisdiction_filter
    industry_match = not industry_filter or industry in industry_filter
    sensitivity_match = not data_sensitivity_filter or data_sensitivity in data_sensitivity_filter

    if "PRIVACY ACT" in regulation.get("name", "").upper():
        return (
            jurisdiction_match
            or "personal" in data_types
            or "pii" in data_types
            or data_sensitivity in {"high", "sensitive"}
        )

    return jurisdiction_match and industry_match and sensitivity_match


# ---------------------------------------------------------------------------
# Compliance scoring
# ---------------------------------------------------------------------------


def calculate_compliance_scores(
    mapping: dict[str, Any],
    control_assessments: list[dict[str, Any]],
    control_registry: dict[str, Any],
    regulation_library: dict[str, Any],
) -> dict[str, Any]:
    total_controls = len(control_assessments)
    compliant_controls = sum(1 for a in control_assessments if a["compliant"])
    overall_score = (compliant_controls / total_controls * 100) if total_controls > 0 else 0

    regulation_scores: dict[str, dict[str, Any]] = {}
    control_lookup = {item["control_id"]: item for item in control_assessments}
    for control_id in mapping.get("applicable_controls", []):
        control = control_registry.get(control_id, {})
        regulation_id = control.get("regulation")
        if not regulation_id:
            continue
        regulation_entry = regulation_scores.setdefault(
            regulation_id,
            {"total_controls": 0, "compliant_controls": 0, "score": 0.0},
        )
        regulation_entry["total_controls"] += 1
        assessment = control_lookup.get(control_id)
        if assessment and assessment.get("compliant"):
            regulation_entry["compliant_controls"] += 1

    for regulation_id, entry in regulation_scores.items():
        total = entry["total_controls"]
        entry["score"] = (entry["compliant_controls"] / total * 100) if total else 0
        entry["regulation_name"] = regulation_library.get(regulation_id, {}).get("name")

    return {
        "overall_score": overall_score,
        "total_controls": total_controls,
        "compliant_controls": compliant_controls,
        "regulation_scores": regulation_scores,
    }


# ---------------------------------------------------------------------------
# Control testing date helpers
# ---------------------------------------------------------------------------


async def is_recently_tested(control: dict[str, Any], status: dict[str, Any]) -> bool:
    """Check if control has been tested recently."""
    last_test_date_str = status.get("last_tested")
    if not last_test_date_str:
        return False

    last_test_date = datetime.fromisoformat(last_test_date_str)
    # Handle both naive and aware datetimes
    if last_test_date.tzinfo is None:
        last_test_date = last_test_date.replace(tzinfo=timezone.utc)
    test_frequency = control.get("test_frequency", "quarterly")

    frequency_days = {"monthly": 30, "quarterly": 90, "semi-annually": 180, "annually": 365}
    days_threshold = frequency_days.get(test_frequency, 90)
    days_since_test = (datetime.now(timezone.utc) - last_test_date).days

    return days_since_test <= days_threshold


async def calculate_next_test_date(control: dict[str, Any]) -> str:
    """Calculate next test date based on frequency."""
    last_test_date_str = control.get("last_test_date")
    if not last_test_date_str:
        return datetime.now(timezone.utc).isoformat()

    last_test_date = datetime.fromisoformat(last_test_date_str)
    test_frequency = control.get("test_frequency", "quarterly")

    frequency_days = {"monthly": 30, "quarterly": 90, "semi-annually": 180, "annually": 365}
    days_to_add = frequency_days.get(test_frequency, 90)
    next_test_date = last_test_date + timedelta(days=days_to_add)

    return next_test_date.isoformat()


# ---------------------------------------------------------------------------
# Gap analysis helpers
# ---------------------------------------------------------------------------


async def identify_gap_type(assessment: dict[str, Any]) -> str:
    """Identify type of compliance gap."""
    evaluation_gaps = assessment.get("evaluation_gaps", [])
    if "risk_mitigation" in evaluation_gaps:
        return "Missing Risk Mitigation"
    if "audit_logs" in evaluation_gaps:
        return "Missing Audit Logs"
    if not assessment.get("implemented"):
        return "Not Implemented"
    elif not assessment.get("evidence_provided"):
        return "Missing Evidence"
    elif not assessment.get("recently_tested"):
        return "Overdue Testing"
    else:
        return "Unknown"


async def recommend_remediation(assessment: dict[str, Any]) -> str:
    """Recommend remediation action."""
    gap_type = await identify_gap_type(assessment)

    recommendations = {
        "Not Implemented": "Implement control and document procedures",
        "Missing Evidence": "Upload evidence of control implementation",
        "Overdue Testing": "Schedule and perform control testing",
        "Missing Risk Mitigation": "Document risk mitigations and link to controls",
        "Missing Audit Logs": "Enable and retain audit logging for control scope",
        "Unknown": "Review control status",
    }

    return recommendations.get(gap_type, "Review and update")


# ---------------------------------------------------------------------------
# Obligation / text extraction helpers
# ---------------------------------------------------------------------------


def extract_obligations_from_text(text: str, key_phrases: list[str]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    if not text:
        return obligations
    sentences = re.split(r"(?<=[.!?])\s+", text)
    obligation_patterns = re.compile(
        r"\b(shall|must|required|requires|obligated|ensure|prohibit|mandate)\b",
        re.IGNORECASE,
    )
    for sentence in sentences:
        if obligation_patterns.search(sentence):
            obligation = sentence.strip()
            if obligation:
                obligations.append({"obligation": obligation, "deadline": None})

    for phrase in key_phrases[:10]:
        obligations.append({"obligation": phrase, "deadline": None, "source": "key_phrase"})

    return obligations


def extract_effective_date(entities: list[dict[str, Any]]) -> str | None:
    for entity in entities:
        if entity.get("category") in {"DateTime", "Date"}:
            return entity.get("text")
    return None


def extract_sources(snippets: list[str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for snippet in snippets:
        match = re.search(r"\((https?://[^)]+)\)", snippet)
        url = match.group(1) if match else ""
        if not url:
            continue
        sources.append({"url": url, "citation": snippet.strip()})
    return sources


def identify_control_gaps(
    updates: list[dict[str, Any]], regulation_library: dict[str, Any]
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    known_regulations = set(regulation_library.keys())
    for update in updates:
        regulation = update.get("regulation")
        if regulation and regulation not in known_regulations:
            gaps.append(
                {
                    "regulation": regulation,
                    "recommended_action": "Review control library and add mappings.",
                }
            )
    return gaps


# ---------------------------------------------------------------------------
# RSS / feed parsing helpers
# ---------------------------------------------------------------------------


def normalize_regulatory_update(entry: Any, feed_config: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    regulation = entry.get("regulation") or entry.get("title") or entry.get("name")
    description = entry.get("description") or entry.get("summary") or entry.get("details")
    if not regulation and not description:
        return None
    return {
        "regulation": regulation,
        "description": description,
        "effective_date": entry.get("effective_date") or entry.get("effectiveDate"),
        "region": entry.get("region"),
        "source_url": entry.get("source_url") or entry.get("url") or feed_config.get("url"),
        "feed": feed_config.get("name") or feed_config.get("url"),
        "raw": entry,
    }


def parse_rss_updates(payload: str, feed_config: dict[str, Any]) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return updates

    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        description = item.findtext("description") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""
        normalized = normalize_regulatory_update(
            {
                "regulation": title,
                "description": description,
                "effective_date": pub_date,
                "source_url": link,
            },
            feed_config,
        )
        if normalized:
            updates.append(normalized)
    return updates
