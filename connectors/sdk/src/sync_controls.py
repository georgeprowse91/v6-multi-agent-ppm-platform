from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class WriteControlPolicy:
    idempotency_fields: tuple[str, ...] = ("id", "external_id", "key")
    conflict_timestamp_field: str = "updated_at"


def build_idempotency_key(record: dict[str, Any], policy: WriteControlPolicy) -> str:
    values = {field: record.get(field) for field in policy.idempotency_fields}
    if not any(value is not None for value in values.values()):
        values["payload"] = record
    payload = json.dumps(values, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dedupe_by_idempotency(
    records: list[dict[str, Any]],
    policy: WriteControlPolicy,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        key = build_idempotency_key(record, policy)
        if key in seen:
            continue
        seen.add(key)
        enriched = dict(record)
        enriched.setdefault("_idempotency_key", key)
        deduped.append(enriched)
    return deduped


def detect_conflict(
    client_record: dict[str, Any],
    server_record: dict[str, Any] | None,
    policy: WriteControlPolicy,
) -> bool:
    if not server_record:
        return False
    field = policy.conflict_timestamp_field
    client_ts = client_record.get(field)
    server_ts = server_record.get(field)
    return bool(client_ts and server_ts and client_ts != server_ts)
