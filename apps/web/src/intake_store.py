from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intake_models import IntakeDecision, IntakeDecisionRecord, IntakeRequest, IntakeRequestCreate, utc_now


class IntakeStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def list_requests(self, status: str | None = None) -> list[IntakeRequest]:
        payload = self._load()
        requests_raw = payload.get("requests", [])
        requests = [IntakeRequest.model_validate(item) for item in requests_raw]
        if status:
            return [request for request in requests if request.status == status]
        return requests

    def create_request(self, payload: IntakeRequestCreate) -> IntakeRequest:
        store = self._load()
        requests_raw = store.setdefault("requests", [])
        request = IntakeRequest.build(payload)
        requests_raw.append(request.model_dump(mode="json"))
        self._write(store)
        return request

    def get_request(self, request_id: str) -> IntakeRequest | None:
        store = self._load()
        for request_raw in store.get("requests", []):
            if request_raw.get("request_id") == request_id:
                return IntakeRequest.model_validate(request_raw)
        return None

    def update_decision(self, request_id: str, decision_payload: IntakeDecision) -> IntakeRequest | None:
        store = self._load()
        requests_raw = store.get("requests", [])
        for index, request_raw in enumerate(requests_raw):
            if request_raw.get("request_id") != request_id:
                continue
            request = IntakeRequest.model_validate(request_raw)
            if request.reviewers and decision_payload.reviewer_id not in request.reviewers:
                raise ValueError("Reviewer is not authorized for this request")
            decision = IntakeDecisionRecord(
                decision=decision_payload.decision,
                reviewer_id=decision_payload.reviewer_id,
                comments=decision_payload.comments,
                decided_at=utc_now(),
            )
            status = "approved" if decision_payload.decision == "approved" else "rejected"
            updated = request.model_copy(
                update={
                    "status": status,
                    "updated_at": utc_now(),
                    "decision": decision,
                }
            )
            requests_raw[index] = updated.model_dump(mode="json")
            self._write(store)
            return updated
        return None

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"requests": []}
        return json.loads(self._path.read_text())

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))
