from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from conflict_store import get_conflict_store


@dataclass
class EntityUpdate:
    entity_type: str
    entity_id: str
    source_system: str
    payload: dict[str, Any]
    updated_at: str | None = None
    canonical_updated_at: str | None = None
    external_id: str | None = None


@dataclass
class PropagationAction:
    rule_id: str
    target: str
    mode: str
    status: str
    reason: str | None
    payload: dict[str, Any] | None = None


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)


def apply_propagation_rules(
    update: EntityUpdate,
    rules: Iterable[Any],
    *,
    dry_run: bool = False,
) -> list[PropagationAction]:
    actions: list[PropagationAction] = []
    conflict_store = get_conflict_store()
    update_ts = _parse_timestamp(update.updated_at)
    canonical_ts = _parse_timestamp(update.canonical_updated_at)

    for rule in rules:
        if update.source_system != rule.source:
            actions.append(
                PropagationAction(
                    rule_id=rule.id,
                    target=rule.target,
                    mode=rule.mode,
                    status="skipped",
                    reason="source_mismatch",
                )
            )
            continue

        strategy = getattr(rule, "conflict_strategy", "source_of_truth")
        if strategy == "manual_required":
            conflict_store.record(
                connector=update.source_system,
                entity=update.entity_type,
                task_id=update.entity_id,
                external_id=update.external_id,
                strategy=strategy,
                reason="manual_resolution_required",
                internal_updated_at=update.canonical_updated_at,
                external_updated_at=update.updated_at,
                details={
                    "rule_id": rule.id,
                    "target": rule.target,
                    "mode": rule.mode,
                },
            )
            actions.append(
                PropagationAction(
                    rule_id=rule.id,
                    target=rule.target,
                    mode=rule.mode,
                    status="conflict",
                    reason="manual_resolution_required",
                )
            )
            continue

        if strategy == "last_write_wins" and canonical_ts > update_ts:
            actions.append(
                PropagationAction(
                    rule_id=rule.id,
                    target=rule.target,
                    mode=rule.mode,
                    status="skipped",
                    reason="canonical_newer",
                )
            )
            continue

        actions.append(
            PropagationAction(
                rule_id=rule.id,
                target=rule.target,
                mode=rule.mode,
                status="applied" if not dry_run else "planned",
                reason=None,
                payload=update.payload,
            )
        )

    return actions
