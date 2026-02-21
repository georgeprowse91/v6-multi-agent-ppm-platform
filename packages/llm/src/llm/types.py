from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str
    raw: dict[str, Any]
    provider: str = "unknown"
    cache_hit: bool = False


@dataclass
class LLMStreamChunk:
    index: int
    delta: str
    raw: dict[str, Any]
    done: bool = False


class LLMProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, provider: str | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider
