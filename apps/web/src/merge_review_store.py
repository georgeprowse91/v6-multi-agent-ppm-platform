from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from merge_review_models import MergeDecision, MergeDecisionRecord, MergeReviewCase, utc_now


class MergeReviewStore:
    def __init__(self, path: Path, seed_path: Path | None = None) -> None:
        self._path = path
        self._seed_path = seed_path
        self._ensure_seed()

    def list_cases(self, status: str | None = None) -> list[MergeReviewCase]:
        payload = self._load()
        cases_raw = payload.get("cases", [])
        cases = [MergeReviewCase.model_validate(item) for item in cases_raw]
        if status:
            return [case for case in cases if case.status == status]
        return cases

    def update_decision(
        self, case_id: str, decision_payload: MergeDecision
    ) -> MergeReviewCase | None:
        store = self._load()
        cases_raw = store.get("cases", [])
        for index, case_raw in enumerate(cases_raw):
            if case_raw.get("case_id") != case_id:
                continue
            case = MergeReviewCase.model_validate(case_raw)
            decision = MergeDecisionRecord(
                decision=decision_payload.decision,
                reviewer_id=decision_payload.reviewer_id,
                comments=decision_payload.comments,
                decided_at=utc_now(),
            )
            updated = case.model_copy(
                update={
                    "status": decision_payload.decision,
                    "updated_at": utc_now(),
                    "decision": decision,
                }
            )
            cases_raw[index] = updated.model_dump(mode="json")
            self._write(store)
            return updated
        return None

    def _ensure_seed(self) -> None:
        if self._path.exists():
            return
        if not self._seed_path or not self._seed_path.exists():
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(self._seed_path.read_text())

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"cases": []}
        return json.loads(self._path.read_text())

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))
