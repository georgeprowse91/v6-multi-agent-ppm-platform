from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from knowledge_store import KnowledgeStore
from spreadsheet_models import SheetDetail
from spreadsheet_store import SpreadsheetStore

MIN_MATCH_SCORE = 0.6
MAX_EXCERPT_CHARS = 200
MAX_TOKEN_SCAN = 200


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


class SearchService:
    def __init__(
        self, knowledge_store: KnowledgeStore, spreadsheet_store: SpreadsheetStore
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
    ) -> tuple[list[SearchResultItem], int]:
        if not query.strip():
            return [], 0

        type_set = {value for value in types if value}
        results: list[SearchResultItem] = []

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

        results.sort(key=lambda item: (item.score, item.updated_at or datetime.min), reverse=True)
        total = len(results)
        return results[offset : offset + limit], total

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
                    )
                )
        return results


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
