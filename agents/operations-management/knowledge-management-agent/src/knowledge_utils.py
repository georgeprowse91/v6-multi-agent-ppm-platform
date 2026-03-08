"""
Utility helpers for the Knowledge Management Agent.

Pure functions and stateless helpers extracted from the monolithic agent so
they can be imported by both the main class and individual action modules.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


async def generate_document_id() -> str:
    """Generate unique document ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"DOC-{timestamp}-{uuid.uuid4().hex[:8]}"


async def generate_lesson_id() -> str:
    """Generate unique lesson ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"LESSON-{timestamp}-{uuid.uuid4().hex[:8]}"


async def generate_ingestion_id() -> str:
    """Generate unique ingestion ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INGEST-{timestamp}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Text / keyword helpers
# ---------------------------------------------------------------------------


def extract_keywords(content: str, *, limit: int = 10) -> list[str]:
    """Extract simple keyword list from content."""
    tokens = [token.lower().strip(".,;:()[]") for token in content.split()]
    tokens = [token for token in tokens if len(token) > 3]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(limit)]


def detect_language(content: str) -> str:
    if not content:
        return "unknown"
    ascii_ratio = sum(1 for char in content if ord(char) < 128) / len(content)
    return "en" if ascii_ratio > 0.9 else "unknown"


def extract_document_attributes(content: str) -> dict[str, Any]:
    """Extract author, date, and tags from content using simple NLP heuristics."""
    author_match = re.search(r"(?im)^author\\s*:\\s*(.+)$", content)
    date_match = re.search(r"(?im)^date\\s*:\\s*(.+)$", content)
    tag_match = re.search(r"(?im)^tags?\\s*:\\s*(.+)$", content)
    hash_tags = re.findall(r"#(\\w+)", content)
    tags: list[str] = []
    if tag_match:
        tags.extend([tag.strip() for tag in tag_match.group(1).split(",") if tag.strip()])
    tags.extend(hash_tags)
    return {
        "author": author_match.group(1).strip() if author_match else None,
        "date": date_match.group(1).strip() if date_match else None,
        "tags": list(dict.fromkeys(tags)),
        "metadata": {"hashtags": hash_tags} if hash_tags else {},
    }


def classify_topic_phase_domain(content: str) -> dict[str, str | None]:
    content_lower = content.lower()
    phase_keywords = {
        "initiation": ["charter", "business case", "kickoff"],
        "planning": ["plan", "schedule", "scope", "requirements"],
        "execution": ["implementation", "delivery", "build"],
        "monitoring": ["status", "metrics", "risk", "issue"],
        "closure": ["handover", "retrospective", "closure", "lessons learned"],
    }
    domain_keywords = {
        "security": ["security", "vulnerability", "access control"],
        "finance": ["budget", "cost", "invoice", "capex"],
        "operations": ["operations", "runbook", "incident"],
        "compliance": ["compliance", "policy", "audit"],
        "engineering": ["architecture", "design", "code", "deployment"],
    }
    phase = None
    for candidate, keywords in phase_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            phase = candidate
            break
    domain = None
    for candidate, keywords in domain_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            domain = candidate
            break
    return {"topic": phase, "phase": phase, "domain": domain}


def extract_risks(content: str) -> list[str]:
    keywords = [
        token.strip(".,:;") for token in content.split() if token.lower().startswith("risk")
    ]
    return keywords[:5]


def extract_decisions(content: str) -> list[str]:
    decisions = []
    for line in content.splitlines():
        if "decision" in line.lower():
            decisions.append(line.strip()[:80])
    return decisions[:5]


# ---------------------------------------------------------------------------
# Graph ID helpers
# ---------------------------------------------------------------------------


def graph_document_id(document_id: str) -> str:
    return f"document:{document_id}"


def graph_entity_id(entity_text: str | None) -> str:
    return f"entity:{entity_text}" if entity_text else "entity:unknown"


def graph_risk_id(risk: str) -> str:
    return f"risk:{risk}"


def graph_decision_id(decision: str) -> str:
    return f"decision:{decision}"


# ---------------------------------------------------------------------------
# Excerpt / search helpers
# ---------------------------------------------------------------------------


def extract_query_terms(query: str) -> list[str]:
    return [token for token in re.findall(r"\w+", query, flags=re.UNICODE) if len(token) > 1]


def normalize_excerpt_text(content: str) -> str:
    without_markup = re.sub(r"<[^>]+>", " ", content)
    return re.sub(r"\s+", " ", without_markup, flags=re.UNICODE).strip()


def normalize_offset_spans(offsets: list[Any] | None, content_length: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    if not offsets:
        return spans

    for item in offsets:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            start, end = item[0], item[1]
        elif isinstance(item, dict):
            start = item.get("start")
            end = item.get("end")
        else:
            continue

        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if end <= start:
            continue

        clamped_start = max(0, min(start, content_length))
        clamped_end = max(clamped_start, min(end, content_length))
        if clamped_end > clamped_start:
            spans.append((clamped_start, clamped_end))

    return sorted(spans)


def find_match_spans(text: str, query_terms: list[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for term in query_terms:
        escaped_term = re.escape(term)
        for match in re.finditer(escaped_term, text, flags=re.IGNORECASE | re.UNICODE):
            spans.append((match.start(), match.end()))
    return sorted(spans)


def enforce_excerpt_limit(excerpt: str, max_length: int) -> str:
    if len(excerpt) <= max_length:
        return excerpt

    clipped = excerpt[: max(0, max_length - 3)].rstrip()
    if clipped.startswith("...") and not clipped.endswith("..."):
        return clipped + "..."
    return clipped + "..."


def highlight_terms(excerpt: str, query_terms: list[str]) -> str:
    if not excerpt or not query_terms:
        return excerpt

    unique_terms = sorted({term for term in query_terms if term}, key=len, reverse=True)
    if not unique_terms:
        return excerpt

    pattern = "|".join(re.escape(term) for term in unique_terms)
    return re.sub(
        rf"(?i)({pattern})",
        r"<mark>\1</mark>",
        excerpt,
        flags=re.UNICODE,
    )


def build_excerpt(
    *,
    content: str,
    query_terms: list[str],
    max_length: int,
    window_radius: int,
    semantic_offsets: list[Any] | None = None,
) -> str:
    text = normalize_excerpt_text(content)
    if not text:
        return ""

    match_spans = find_match_spans(text, query_terms)
    semantic_spans = normalize_offset_spans(semantic_offsets, len(text))
    candidate_spans = semantic_spans or match_spans

    if candidate_spans:
        center = candidate_spans[0][0]
        for start, end in candidate_spans:
            if (end - start) > 0:
                center = start + ((end - start) // 2)
                break
        start_idx = max(0, center - window_radius)
        end_idx = min(len(text), center + window_radius)
        excerpt = text[start_idx:end_idx].strip()
        if start_idx > 0:
            excerpt = "..." + excerpt
        if end_idx < len(text):
            excerpt = excerpt + "..."
    else:
        excerpt = text[:max_length].strip()
        if len(text) > max_length:
            excerpt += "..."

    excerpt = enforce_excerpt_limit(excerpt, max_length)
    return highlight_terms(excerpt, query_terms)


# ---------------------------------------------------------------------------
# Graph infrastructure helpers
# ---------------------------------------------------------------------------


def register_graph_node(
    graph_nodes: dict[str, dict[str, Any]],
    node_id: str,
    node_type: str,
    attributes: dict[str, Any],
) -> None:
    if node_id not in graph_nodes:
        graph_nodes[node_id] = {"type": node_type, "attributes": attributes}
    else:
        graph_nodes[node_id]["attributes"].update(attributes)


def register_graph_edge(
    graph_edges: list[dict[str, Any]], source: str, target: str, relation: str
) -> None:
    graph_edges.append({"from": source, "to": target, "relation": relation})


def traverse_graph(
    graph_nodes: dict[str, dict[str, Any]],
    graph_edges: list[dict[str, Any]],
    start_node: str,
    relation: str | None = None,
    target_type: str | None = None,
    depth: int = 2,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    visited: set[str] = set()
    frontier = [(start_node, 0)]
    while frontier:
        node_id, level = frontier.pop(0)
        if node_id in visited or level >= depth:
            continue
        visited.add(node_id)
        for edge in graph_edges:
            if edge["from"] != node_id:
                continue
            if relation and edge["relation"] != relation:
                continue
            target = edge["to"]
            node = graph_nodes.get(target)
            if target_type and node and node.get("type") != target_type:
                frontier.append((target, level + 1))
                continue
            if node:
                results.append({"node_id": target, **node})
            frontier.append((target, level + 1))
    return results


def update_graph_for_document(
    document: dict[str, Any],
    graph_nodes: dict[str, dict[str, Any]],
    graph_edges: list[dict[str, Any]],
) -> None:
    """Update knowledge graph with document relationships (pure-function form)."""
    document_id = document.get("document_id")
    if not document_id:
        return
    doc_node = graph_document_id(document_id)
    register_graph_node(
        graph_nodes,
        doc_node,
        "document",
        {"title": document.get("title"), "doc_type": document.get("type")},
    )

    for relation, key in [
        ("project", "project_id"),
        ("program", "program_id"),
        ("portfolio", "portfolio_id"),
    ]:
        related_id = document.get(key)
        if related_id:
            related_node = f"{relation}:{related_id}"
            register_graph_node(graph_nodes, related_node, relation, {"id": related_id})
            register_graph_edge(graph_edges, doc_node, related_node, "relates_to")

    for risk in extract_risks(document.get("content", "")):
        risk_node = graph_risk_id(risk)
        register_graph_node(graph_nodes, risk_node, "risk", {"name": risk})
        register_graph_edge(graph_edges, risk_node, doc_node, "documented_in")

    for decision in extract_decisions(document.get("content", "")):
        decision_node = graph_decision_id(decision)
        register_graph_node(graph_nodes, decision_node, "decision", {"name": decision})
        register_graph_edge(graph_edges, decision_node, doc_node, "documented_in")


# ---------------------------------------------------------------------------
# Schema / doc-type mapping
# ---------------------------------------------------------------------------

DOC_TYPE_SCHEMA_MAP: dict[str, str] = {
    "requirements": "requirement",
    "design": "specification",
    "test_plan": "specification",
    "charter": "report",
    "policy": "policy",
    "procedure": "policy",
    "report": "report",
    "lessons_learned": "report",
    "meeting_minutes": "report",
}


def map_doc_type_for_schema(doc_type: str | None) -> str:
    """Map internal document type to schema doc_type."""
    if not doc_type:
        return "report"
    return DOC_TYPE_SCHEMA_MAP.get(doc_type, "report")


# ---------------------------------------------------------------------------
# Access control helpers
# ---------------------------------------------------------------------------


def is_access_allowed(document: dict[str, Any], access_context: dict[str, Any]) -> bool:
    """Evaluate RBAC/ABAC rules for document access (pure function)."""
    if document.get("classification") == "public":
        return True

    permissions = document.get("permissions", {})
    if permissions.get("public"):
        return True

    if not access_context:
        return False

    user_id = access_context.get("user_id")
    if user_id and user_id in permissions.get("users", []):
        return True

    roles = set(access_context.get("roles", []))
    if roles and roles.intersection(set(permissions.get("roles", []))):
        return True

    required_attrs = permissions.get("attributes", {})
    if required_attrs:
        user_attrs = access_context.get("attributes", {})
        for key, value in required_attrs.items():
            if user_attrs.get(key) != value:
                return False
        return True

    return False


def matches_search_filters(document: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if document matches search filters (pure function)."""
    if "type" in filters and document.get("type") != filters["type"]:
        return False

    if "project_id" in filters and document.get("project_id") != filters["project_id"]:
        return False

    if "tags" in filters:
        doc_tags = set(document.get("tags", []))
        filter_tags = set(filters["tags"])
        if not doc_tags.intersection(filter_tags):
            return False

    return True
