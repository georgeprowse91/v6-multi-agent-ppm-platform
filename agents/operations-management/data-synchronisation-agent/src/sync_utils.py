"""
Utility and helper functions for the Data Synchronization Agent.

These are stateless helpers extracted from the monolithic agent class.
Functions that need agent state receive it via parameters.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from jsonschema import ValidationError, validate  # noqa: E402

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - optional dependency
    fuzz = None


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def is_duplicate_record(
    seen_record_hashes: dict[str, set[str]],
    tenant_id: str,
    entity_type: str,
    data: dict[str, Any],
) -> bool:
    """Return ``True`` if an identical (entity_type, data) pair was already seen."""
    normalized_payload = json.dumps(
        {"entity_type": entity_type, "data": data},
        sort_keys=True,
        default=str,
    )
    record_hash = hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()
    seen_hashes = seen_record_hashes.setdefault(tenant_id, set())
    if record_hash in seen_hashes:
        return True
    seen_hashes.add(record_hash)
    return False


# ---------------------------------------------------------------------------
# Transformation helpers
# ---------------------------------------------------------------------------


def validate_transformation_rule(
    rule: dict[str, Any],
    transformation_schema: dict[str, Any],
    logger: Any,
) -> bool:
    """Validate a transformation rule against the schema."""
    try:
        validate(instance=rule, schema=transformation_schema)
    except ValidationError as exc:
        logger.warning(
            "invalid_transformation_rule",
            extra={"error": str(exc), "rule": rule},
        )
        return False
    return True


def apply_transformations(
    payload: dict[str, Any], transformations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Apply a list of field transformations to a payload dict."""
    updated = payload.copy()
    for transformation in transformations:
        field = transformation.get("field")
        operation = transformation.get("operation")
        value = transformation.get("value")
        if field is None or operation is None:
            continue
        current = updated.get(field)
        if operation == "uppercase" and isinstance(current, str):
            updated[field] = current.upper()
        elif operation == "lowercase" and isinstance(current, str):
            updated[field] = current.lower()
        elif operation == "strip" and isinstance(current, str):
            updated[field] = current.strip()
        elif operation == "prefix" and isinstance(current, str) and isinstance(value, str):
            updated[field] = f"{value}{current}"
        elif operation == "suffix" and isinstance(current, str) and isinstance(value, str):
            updated[field] = f"{current}{value}"
        elif operation == "concat" and isinstance(value, list):
            parts = [str(updated.get(part, "")) for part in value]
            updated[field] = "".join(parts)
        elif operation == "cast_int":
            try:
                updated[field] = int(current)
            except (TypeError, ValueError):
                continue
        elif operation == "cast_float":
            try:
                updated[field] = float(current)
            except (TypeError, ValueError):
                continue
    return updated


def get_transformation_rules(
    transformation_rules: list[dict[str, Any]],
    entity_type: str,
    source_system: str,
) -> list[dict[str, Any]]:
    """Filter transformation rules by entity type and source system."""
    rules = []
    for rule in transformation_rules:
        if rule.get("entity_type") != entity_type:
            continue
        if rule.get("source_system") and rule.get("source_system") != source_system:
            continue
        rules.append(rule)
    return rules


# ---------------------------------------------------------------------------
# Timestamp extraction
# ---------------------------------------------------------------------------


def extract_timestamp(payload: dict[str, Any]) -> datetime | None:
    """Extract a datetime from common timestamp fields in a payload."""
    for key in ("updated_at", "timestamp", "created_at"):
        raw = payload.get(key)
        if isinstance(raw, str):
            try:
                dt = datetime.fromisoformat(raw)
                # Ensure timezone-aware so arithmetic with datetime.now(utc) works.
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Conflict resolution helpers
# ---------------------------------------------------------------------------


def resolve_by_timestamp(
    master_record: dict[str, Any],
    new_data: dict[str, Any],
    conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved = new_data.copy()
    new_timestamp = extract_timestamp(new_data) or extract_timestamp(master_record)
    current_timestamp = extract_timestamp(master_record)
    if new_timestamp and current_timestamp and new_timestamp < current_timestamp:
        for conflict in conflicts:
            field = conflict.get("field")
            if field in master_record.get("data", {}):
                resolved[field] = master_record["data"][field]
    return resolved


def resolve_by_authority(
    master_record: dict[str, Any],
    new_data: dict[str, Any],
    conflicts: list[dict[str, Any]],
    authoritative_sources: dict[str, str],
) -> dict[str, Any]:
    resolved = master_record.get("data", {}).copy()
    resolved.update(new_data)
    for conflict in conflicts:
        field = conflict.get("field")
        source_system = conflict.get("source_system")
        authoritative_source = authoritative_sources.get(field)
        if authoritative_source and source_system != authoritative_source:
            resolved[field] = master_record.get("data", {}).get(field)
    return resolved


def resolve_prefer_existing(
    master_record: dict[str, Any],
    new_data: dict[str, Any],
    conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved = master_record.get("data", {}).copy()
    for key, value in new_data.items():
        if key not in resolved or resolved[key] in (None, ""):
            resolved[key] = value
    for conflict in conflicts:
        field = conflict.get("field")
        if field in master_record.get("data", {}):
            resolved[field] = master_record["data"][field]
    return resolved


# ---------------------------------------------------------------------------
# Similarity / duplicate detection helpers
# ---------------------------------------------------------------------------


def find_potential_duplicates(
    records: list[tuple],
    duplicate_confidence_threshold: float,
) -> list[list[str]]:
    """Find duplicates using fuzzy matching across a list of (id, record) tuples."""
    duplicates: list[set[str]] = []
    for index, (left_id, left_record) in enumerate(records):
        left_text = build_similarity_text(left_record)
        for right_id, right_record in records[index + 1 :]:
            right_text = build_similarity_text(right_record)
            similarity = calculate_similarity(left_text, right_text)
            if similarity >= duplicate_confidence_threshold:
                _add_duplicate_pair(duplicates, left_id, right_id)
    return [sorted(group) for group in duplicates]


def build_similarity_text(record: dict[str, Any]) -> str:
    data = record.get("data", {})
    fields = [
        str(data.get("name", "")),
        str(data.get("title", "")),
        str(data.get("email", "")),
        str(data.get("id", "")),
    ]
    return " ".join(part for part in fields if part).lower().strip()


def calculate_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    fuzz_ratio = fuzz.token_set_ratio(left, right) / 100.0 if fuzz else 0.0
    token_sim = token_similarity(left, right)
    levenshtein_sim = levenshtein_similarity(left, right)
    return max(fuzz_ratio, token_sim, levenshtein_sim)


def token_similarity(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens.intersection(right_tokens)
    union = left_tokens.union(right_tokens)
    return len(intersection) / len(union)


def levenshtein_similarity(left: str, right: str) -> float:
    distance = levenshtein_distance(left, right)
    max_len = max(len(left), len(right))
    if max_len == 0:
        return 1.0
    return 1 - (distance / max_len)


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _add_duplicate_pair(groups: list[set[str]], left_id: str, right_id: str) -> None:
    left_group = None
    right_group = None
    for group in groups:
        if left_id in group:
            left_group = group
        if right_id in group:
            right_group = group
    if left_group and right_group and left_group is not right_group:
        left_group.update(right_group)
        groups.remove(right_group)
    elif left_group:
        left_group.add(right_id)
    elif right_group:
        right_group.add(left_id)
    else:
        groups.append({left_id, right_id})


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def validate_against_schema(schema: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Validate data against a JSON schema, returning a list of error strings."""
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        return [str(exc)]
    return []


# ---------------------------------------------------------------------------
# Quality dimension computation
# ---------------------------------------------------------------------------


def compute_quality_dimensions(
    entity_type: str,
    validation_result: dict[str, Any],
    schema_registry: dict[str, dict[str, Any]],
    validation_rules: dict[str, list[dict[str, Any]]],
    sync_latency_sla_seconds: float,
) -> tuple[float, float, float, float | None]:
    """Compute completeness, consistency, timeliness scores and age."""
    data = validation_result.get("data") or {}
    required_fields = get_required_fields(entity_type, schema_registry, validation_rules)
    completeness_score = 1.0
    if required_fields:
        present = sum(1 for field in required_fields if data.get(field) not in (None, "", []))
        completeness_score = present / len(required_fields)

    error_count = len(validation_result.get("errors", []))
    if error_count == 0:
        consistency_score = 1.0
    else:
        divisor = max(len(required_fields), 1)
        consistency_score = max(0.0, 1 - (error_count / divisor))

    timestamp = extract_timestamp(data) if isinstance(data, dict) else None
    age_seconds = None
    if timestamp:
        age_seconds = max((datetime.now(timezone.utc) - timestamp).total_seconds(), 0.0)
        if sync_latency_sla_seconds <= 0:
            timeliness_score = 1.0
        elif age_seconds <= sync_latency_sla_seconds:
            timeliness_score = 1.0
        else:
            timeliness_score = max(
                0.0,
                1 - (age_seconds / (sync_latency_sla_seconds * 2)),
            )
    else:
        timeliness_score = 1.0

    return completeness_score, consistency_score, timeliness_score, age_seconds


def get_required_fields(
    entity_type: str,
    schema_registry: dict[str, dict[str, Any]],
    validation_rules: dict[str, list[dict[str, Any]]],
) -> list[str]:
    """Collect required fields from schema registry and validation rules."""
    required_fields: list[str] = []
    schema = schema_registry.get(entity_type)
    if schema:
        schema_required = schema.get("required")
        if isinstance(schema_required, list):
            required_fields.extend(str(field) for field in schema_required)
    for rule in validation_rules.get(entity_type, []):
        if rule.get("required") and rule.get("field"):
            required_fields.append(rule["field"])
    return list(dict.fromkeys(required_fields))


def quality_record_key(record: dict[str, Any]) -> str:
    return (
        f"{record['tenant_id']}-{record['entity_type']}-{record['validated_at'].replace(':', '-')}"
    )
