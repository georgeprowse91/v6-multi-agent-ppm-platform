from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """Current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str | None = None) -> str:
    """Unique id (uuid4 hex), optionally prefixed."""
    raw = uuid.uuid4().hex
    return f"{prefix}_{raw}" if prefix else raw


def json_dumps(data: Any) -> str:
    """Pretty JSON for storage or display."""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def json_dumps_compact(data: Any) -> str:
    """Compact JSON for logs."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def json_loads(text: str | None) -> Any:
    if not text:
        return None
    return json.loads(text)
