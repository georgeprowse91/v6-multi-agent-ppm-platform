from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeline_models import PipelineBoard, PipelineItem, PipelineStage


class PipelineStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def get_board(self, entity_type: str, entity_id: str) -> PipelineBoard:
        payload = self._load()
        boards = payload.setdefault("boards", {})
        key = self._key(entity_type, entity_id)
        if key not in boards:
            boards[key] = self._seed_board().model_dump(mode="json")
            self._write(payload)
        return PipelineBoard.model_validate(boards[key])

    def update_item_status(
        self, entity_type: str, entity_id: str, item_id: str, status: PipelineStage
    ) -> PipelineItem | None:
        payload = self._load()
        boards = payload.setdefault("boards", {})
        key = self._key(entity_type, entity_id)
        board_raw = boards.get(key)
        if not board_raw:
            board_raw = self._seed_board().model_dump(mode="json")
            boards[key] = board_raw
        board = PipelineBoard.model_validate(board_raw)
        if status not in board.stages:
            raise ValueError("Invalid pipeline stage")
        updated_items: list[PipelineItem] = []
        updated_item: PipelineItem | None = None
        for item in board.items:
            if item.item_id == item_id:
                updated_item = item.model_copy(update={"status": status})
                updated_items.append(updated_item)
            else:
                updated_items.append(item)
        if updated_item is None:
            return None
        updated_board = board.model_copy(update={"items": updated_items})
        boards[key] = updated_board.model_dump(mode="json")
        self._write(payload)
        return updated_item

    def _key(self, entity_type: str, entity_id: str) -> str:
        return f"{entity_type}:{entity_id}"

    def _seed_board(self) -> PipelineBoard:
        stages: list[PipelineStage] = ["Draft", "Review", "Approved"]
        items = [
            PipelineItem(
                item_id=str(uuid4()),
                title="Customer data unification",
                summary="Consolidate CRM sources into a single customer profile service.",
                sponsor="Ava Patel",
                priority="High",
                type="intake",
                status="Draft",
            ),
            PipelineItem(
                item_id=str(uuid4()),
                title="Regulatory compliance uplift",
                summary="Address SOC 2 gaps ahead of the Q4 audit.",
                sponsor="Mia Johnson",
                priority="Medium",
                type="intake",
                status="Review",
            ),
            PipelineItem(
                item_id=str(uuid4()),
                title="Mobile experience refresh",
                summary="Phase two rollout for the unified mobile workspace.",
                sponsor="Noah Chen",
                priority="High",
                type="project",
                status="Approved",
            ),
            PipelineItem(
                item_id=str(uuid4()),
                title="Analytics self-service enablement",
                summary="Deploy BI workspaces and training for marketing and sales.",
                sponsor="Liam Smith",
                priority="Low",
                type="project",
                status="Approved",
            ),
        ]
        return PipelineBoard(stages=stages, items=items)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"boards": {}}
        return json.loads(self._path.read_text())

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))
