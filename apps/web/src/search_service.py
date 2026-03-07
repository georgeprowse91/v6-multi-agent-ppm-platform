"""Federated search service with cross-system fan-out and vector deduplication.

Searches local stores (documents, lessons, spreadsheets) as before, and also
fans out queries to registered connector instances in parallel. Results are
merged, deduplicated, and optionally filtered by field-level RBAC policies.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from knowledge_store import KnowledgeStore
from spreadsheet_models import SheetDetail
from spreadsheet_store import SpreadsheetStore

logger = logging.getLogger(__name__)

MIN_MATCH_SCORE = 0.6
MAX_EXCERPT_CHARS = 200
MAX_TOKEN_SCAN = 200

_CONNECTOR_SEARCH_TIMEOUT = 10.0
_MAX_CONNECTOR_WORKERS = 4


@dataclass(frozen=True)
class SearchResultItem:
    id: str
    result_type: str
    title: str
    summary: str
    project_id: str | None
    updated_at: datetime | None
    score: float
    highlights: dict[str, str] | None
    payload: dict[str, Any]
    source_system: str = "local"
    source_url: str | None = None


# ---------------------------------------------------------------------------
# Field-level RBAC helpers
# ---------------------------------------------------------------------------

_field_policies: dict[str, dict[str, list[str]]] | None = None


def _load_field_policies() -> dict[str, dict[str, list[str]]]:
    """Load field-level RBAC from config/rbac/field-level.yaml."""
    global _field_policies
    if _field_policies is not None:
        return _field_policies
    try:
        import yaml
        from pathlib import Path

        policy_path = Path(__file__).resolve().parents[2] / "config" / "rbac" / "field-level.yaml"
        if policy_path.exists():
            with policy_path.open("r", encoding="utf-8") as fh:
                _field_policies = yaml.safe_load(fh) or {}
        else:
            _field_policies = {}
    except Exception:
        _field_policies = {}
    return _field_policies


def _apply_field_rbac(
    results: list[SearchResultItem],
    user_roles: list[str] | None,
) -> list[SearchResultItem]:
    """Strip fields from results that the user's roles are not allowed to see."""
    if not user_roles:
        return results
    policies = _load_field_policies()
    if not policies:
        return results
    filtered: list[SearchResultItem] = []
    for result in results:
        source_policy = policies.get(result.source_system, {})
        if not source_policy:
            filtered.append(result)
            continue
        cleaned_payload = dict(result.payload)
        for field_name, allowed_roles in source_policy.items():
            if field_name in cleaned_payload and not any(r in allowed_roles for r in user_roles):
                cleaned_payload[field_name] = "***REDACTED***"
        filtered.append(
            SearchResultItem(
                id=result.id,
                result_type=result.result_type,
                title=result.title,
                summary=result.summary,
                project_id=result.project_id,
                updated_at=result.updated_at,
                score=result.score,
                highlights=result.highlights,
                payload=cleaned_payload,
                source_system=result.source_system,
                source_url=result.source_url,
            )
        )
    return filtered


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------


def _dedup_key(result: SearchResultItem) -> str:
    """Generate a stable key for duplicate detection."""
    raw = f"{result.source_system}:{result.id}:{result.result_type}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _deduplicate(results: list[SearchResultItem]) -> list[SearchResultItem]:
    """Remove duplicate results across sources using stable hashing."""
    seen: set[str] = set()
    deduped: list[SearchResultItem] = []
    for result in results:
        key = _dedup_key(result)
        if key not in seen:
            seen.add(key)
            deduped.append(result)
    return deduped


# ---------------------------------------------------------------------------
# Connector registry integration
# ---------------------------------------------------------------------------

# Registered connector instances (populated at app startup)
_connector_registry: dict[str, Any] = {}


def register_search_connector(connector_id: str, connector: Any) -> None:
    """Register a connector instance for federated search."""
    _connector_registry[connector_id] = connector


def unregister_search_connector(connector_id: str) -> None:
    """Unregister a connector instance."""
    _connector_registry.pop(connector_id, None)


def list_search_connectors() -> list[str]:
    """Return IDs of all registered search connectors."""
    return list(_connector_registry.keys())


def _search_connector(
    connector_id: str,
    connector: Any,
    query: str,
    limit: int,
) -> list[SearchResultItem]:
    """Search a single connector and convert results to SearchResultItem."""
    try:
        raw_results = connector.search(query, limit=limit)
    except Exception:
        logger.warning("Connector %s search failed", connector_id)
        return []

    items: list[SearchResultItem] = []
    for r in raw_results:
        items.append(
            SearchResultItem(
                id=r.id,
                result_type=r.resource_type,
                title=r.title,
                summary=r.snippet,
                project_id=r.metadata.get("project_key") or r.metadata.get("ProjectID"),
                updated_at=_parse_datetime(r.updated_at),
                score=r.score,
                highlights=None,
                payload=r.metadata,
                source_system=r.source_system,
                source_url=r.url,
            )
        )
    return items


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Main search service
# ---------------------------------------------------------------------------


class SearchService:
    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        spreadsheet_store: SpreadsheetStore,
    ) -> None:
        self._knowledge_store = knowledge_store
        self._spreadsheet_store = spreadsheet_store

    def search(
        self,
        *,
        query: str,
        types: Iterable[str],
        project_ids: set[str] | None,
        tenant_id: str | None,
        offset: int,
        limit: int,
        user_roles: list[str] | None = None,
        include_connectors: bool = True,
    ) -> tuple[list[SearchResultItem], int]:
        if not query.strip():
            return [], 0

        type_set = {value for value in types if value}
        results: list[SearchResultItem] = []

        # --- Local store searches (existing behaviour) ---
        if "document" in type_set:
            results.extend(self._search_documents(query, project_ids))

        if "knowledge" in type_set or "lesson" in type_set:
            results.extend(self._search_lessons(query, project_ids))

        if tenant_id and {"work_item", "risk"}.intersection(type_set):
            sheet_details = self._spreadsheet_store.list_tenant_sheet_details(tenant_id)
            if "work_item" in type_set:
                results.extend(
                    self._search_sheet_items(query, project_ids, sheet_details, "action log")
                )
            if "risk" in type_set:
                results.extend(
                    self._search_sheet_items(query, project_ids, sheet_details, "risk register")
                )

        # --- Cross-system connector fan-out ---
        if include_connectors and _connector_registry:
            connector_results = self._fan_out_connectors(query, limit)
            results.extend(connector_results)

        # Deduplicate across all sources
        results = _deduplicate(results)

        # Apply field-level RBAC
        if user_roles:
            results = _apply_field_rbac(results, user_roles)

        results.sort(key=lambda item: (item.score, item.updated_at or datetime.min), reverse=True)
        total = len(results)
        return results[offset : offset + limit], total

    def _fan_out_connectors(
        self,
        query: str,
        limit: int,
    ) -> list[SearchResultItem]:
        """Fan out search to all registered connectors in parallel."""
        if not _connector_registry:
            return []

        all_results: list[SearchResultItem] = []
        with ThreadPoolExecutor(max_workers=_MAX_CONNECTOR_WORKERS) as pool:
            futures = {
                pool.submit(
                    _search_connector, cid, conn, query, limit
                ): cid
                for cid, conn in _connector_registry.items()
            }
            for future in as_completed(futures, timeout=_CONNECTOR_SEARCH_TIMEOUT):
                connector_id = futures[future]
                try:
                    all_results.extend(future.result())
                except Exception:
                    logger.warning("Connector %s search timed out or failed", connector_id)

        return all_results

    # ------------------------------------------------------------------
    # Local search helpers (unchanged from original)
    # ------------------------------------------------------------------

    def _search_documents(self, query: str, project_ids: set[str] | None) -> list[SearchResultItem]:
        documents = self._knowledge_store.search_documents(
            query=None, project_ids=sorted(project_ids) if project_ids else None
        )
        results: list[SearchResultItem] = []
        for record in documents:
            text = f"{record.name} {record.content}"
            score = _match_score(query, text)
            if score < MIN_MATCH_SCORE:
                continue
            excerpt = _build_excerpt(record.content, query)
            results.append(
                SearchResultItem(
                    id=record.document_id,
                    result_type="document",
                    title=record.name,
                    summary=f"{record.doc_type} · {record.classification}",
                    project_id=record.project_id,
                    updated_at=record.updated_at,
                    score=score,
                    highlights=_merge_highlights(
                        _highlight_text(query, record.name),
                        excerpt,
                    ),
                    payload={
                        "documentId": record.document_id,
                        "documentKey": record.document_key,
                        "projectId": record.project_id,
                        "name": record.name,
                        "docType": record.doc_type,
                        "classification": record.classification,
                        "latestVersion": record.latest_version,
                        "latestStatus": record.latest_status,
                        "createdAt": record.created_at.isoformat(),
                        "updatedAt": record.updated_at.isoformat(),
                    },
                    source_system="local",
                )
            )
        return results

    def _search_lessons(self, query: str, project_ids: set[str] | None) -> list[SearchResultItem]:
        lessons = self._knowledge_store.list_lessons(project_id=None)
        results: list[SearchResultItem] = []
        for lesson in lessons:
            if project_ids and lesson.project_id not in project_ids:
                continue
            text = f"{lesson.title} {lesson.description} {' '.join(lesson.tags)} {' '.join(lesson.topics)}"
            score = _match_score(query, text)
            if score < MIN_MATCH_SCORE:
                continue
            results.append(
                SearchResultItem(
                    id=lesson.lesson_id,
                    result_type="knowledge",
                    title=lesson.title,
                    summary=lesson.description,
                    project_id=lesson.project_id,
                    updated_at=lesson.updated_at,
                    score=score,
                    highlights=_merge_highlights(
                        _highlight_text(query, lesson.title),
                        _build_excerpt(lesson.description, query),
                    ),
                    payload={
                        "lessonId": lesson.lesson_id,
                        "projectId": lesson.project_id,
                        "stageId": lesson.stage_id,
                        "stageName": lesson.stage_name,
                        "title": lesson.title,
                        "description": lesson.description,
                        "tags": lesson.tags,
                        "topics": lesson.topics,
                        "createdAt": lesson.created_at.isoformat(),
                        "updatedAt": lesson.updated_at.isoformat(),
                    },
                    source_system="local",
                )
            )
        return results

    def _search_sheet_items(
        self,
        query: str,
        project_ids: set[str] | None,
        sheets: list[SheetDetail],
        sheet_label: str,
    ) -> list[SearchResultItem]:
        results: list[SearchResultItem] = []
        normalized_label = sheet_label.lower()
        for detail in sheets:
            if project_ids and detail.sheet.project_id not in project_ids:
                continue
            if normalized_label not in detail.sheet.name.lower():
                continue
            column_map = {column.column_id: column.name for column in detail.sheet.columns}
            for row in detail.rows:
                values = {
                    column_map.get(column_id, column_id): value
                    for column_id, value in row.values.items()
                }
                title = _extract_title(values, sheet_label)
                summary = _build_sheet_summary(values)
                combined = f"{title} {summary}"
                score = _match_score(query, combined)
                if score < MIN_MATCH_SCORE:
                    continue
                result_type = "risk" if "risk" in normalized_label else "work_item"
                results.append(
                    SearchResultItem(
                        id=row.row_id,
                        result_type=result_type,
                        title=title,
                        summary=summary,
                        project_id=detail.sheet.project_id,
                        updated_at=row.updated_at,
                        score=score,
                        highlights=None,
                        payload={
                            "rowId": row.row_id,
                            "sheetId": detail.sheet.sheet_id,
                            "sheetName": detail.sheet.name,
                            "projectId": detail.sheet.project_id,
                            "values": values,
                        },
                        source_system="local",
                    )
                )
        return results


# ---------------------------------------------------------------------------
# Text matching utilities
# ---------------------------------------------------------------------------


def _extract_title(values: dict[str, Any], sheet_label: str) -> str:
    preferred = "Risk" if "risk" in sheet_label.lower() else "Action"
    for key, value in values.items():
        if key.lower() == preferred.lower() and value:
            return str(value)
    for value in values.values():
        if value:
            return str(value)
    return preferred


def _build_sheet_summary(values: dict[str, Any]) -> str:
    summary_parts: list[str] = []
    for key in ("Impact", "Likelihood", "Mitigation", "Owner", "Status", "Due Date"):
        value = values.get(key)
        if value:
            summary_parts.append(f"{key}: {value}")
    if not summary_parts:
        summary_parts = [f"{key}: {value}" for key, value in values.items() if value]
    return " · ".join(summary_parts)


def _match_score(query: str, text: str) -> float:
    normalized_query = query.lower().strip()
    if not normalized_query:
        return 0.0
    text_lower = text.lower()
    if normalized_query in text_lower:
        return 1.0
    tokens = re.findall(r"[a-z0-9]+", text_lower)[:MAX_TOKEN_SCAN]
    if not tokens:
        return 0.0
    return max(SequenceMatcher(None, normalized_query, token).ratio() for token in tokens)


def _build_excerpt(content: str, query: str) -> str | None:
    if not content:
        return None
    lowered = content.lower()
    needle = query.lower().strip()
    if not needle:
        return content[:MAX_EXCERPT_CHARS]
    match = lowered.find(needle)
    if match == -1:
        return content[:MAX_EXCERPT_CHARS]
    start = max(match - 60, 0)
    end = min(match + len(needle) + 60, len(content))
    snippet = content[start:end].strip()
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return pattern.sub(lambda value: f"<mark>{value.group(0)}</mark>", snippet)


def _highlight_text(query: str, text: str) -> str | None:
    needle = query.lower().strip()
    if not needle:
        return None
    lowered = text.lower()
    if needle not in lowered:
        return None
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return pattern.sub(lambda value: f"<mark>{value.group(0)}</mark>", text)


def _merge_highlights(title: str | None, excerpt: str | None) -> dict[str, str] | None:
    highlights: dict[str, str] = {}
    if title:
        highlights["title"] = title
    if excerpt:
        highlights["excerpt"] = excerpt
    return highlights or None
