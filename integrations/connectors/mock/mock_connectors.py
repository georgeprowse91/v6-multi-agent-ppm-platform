"""Mock connectors HTTP surface for demo mode."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DATA_ROOT = REPO_ROOT / "data" / "demo"

app = FastAPI(title="Mock Connectors API")


def _load_demo_data(object_name: str) -> list[dict[str, Any]]:
    data_file = DEMO_DATA_ROOT / f"{object_name}.json"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"Demo object '{object_name}' not found")
    payload = json.loads(data_file.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", object_name):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise HTTPException(status_code=500, detail=f"Unsupported payload format for '{object_name}'")


def _paginate(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    offset = (page - 1) * page_size
    paged_items = items[offset : offset + page_size]
    return {
        "data": paged_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": len(items),
            "has_next": offset + page_size < len(items),
        },
    }


@app.get("/{object_name}")
async def list_objects(object_name: str, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)) -> dict[str, Any]:
    return _paginate(_load_demo_data(object_name), page, page_size)


@app.get("/connectors/{connector_id}/{object_name}")
async def list_connector_objects(
    connector_id: str,
    object_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    response = _paginate(_load_demo_data(object_name), page, page_size)
    response["connector_id"] = connector_id
    response["mode"] = "demo"
    return response


@app.post("/{object_name}")
@app.put("/{object_name}/{record_id}")
async def write_objects(object_name: str, request: Request, record_id: str | None = None) -> dict[str, Any]:
    body = await request.json()
    logger.info("mock_connector_write", extra={"object_name": object_name, "record_id": record_id, "payload": body})
    return {"success": True, "object": object_name, "record_id": record_id, "mode": "demo", "persisted": False}
