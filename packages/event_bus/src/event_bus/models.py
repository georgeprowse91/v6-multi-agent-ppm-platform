from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class EventRecord:
    topic: str
    payload: dict[str, Any]
    published_at: str
