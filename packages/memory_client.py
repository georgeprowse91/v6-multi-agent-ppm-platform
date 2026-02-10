from __future__ import annotations

from typing import Any

from services.memory_service.memory_service import MemoryService


class MemoryClient:
    """Client wrapper used by agents/orchestrator to interact with memory service."""

    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    def save_context(self, key: str, data: dict[str, Any]) -> None:
        self._memory_service.save_context(key, data)

    def load_context(self, key: str) -> dict[str, Any] | None:
        return self._memory_service.load_context(key)

    def delete_context(self, key: str) -> None:
        self._memory_service.delete_context(key)

    def close(self) -> None:
        self._memory_service.close()
