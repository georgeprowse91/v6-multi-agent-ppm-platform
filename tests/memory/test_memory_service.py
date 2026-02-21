from __future__ import annotations

from pathlib import Path

import pytest

from services.memory_service import memory_service as memory_module
from services.memory_service.memory_service import MemoryService


class FakeClock:
    def __init__(self, now: float) -> None:
        self.now = now

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_ttl_expiration_logic_with_deterministic_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock(1_000.0)
    monkeypatch.setattr(memory_module.time, "time", clock.time)

    service = MemoryService(backend="memory", default_ttl_seconds=10)
    service.save_context("ttl", {"value": 1})

    clock.advance(9.9)
    assert service.load_context("ttl") == {"value": 1}

    clock.advance(0.1)
    assert service.load_context("ttl") is None


def test_optional_sqlite_persistence_toggle_behavior(tmp_path: Path) -> None:
    memory_only = MemoryService(backend="memory")
    memory_only.save_context("shared", {"mode": "memory"})

    sqlite_path = tmp_path / "memory.sqlite"
    sqlite_service = MemoryService(backend="sqlite", sqlite_path=str(sqlite_path))
    sqlite_service.save_context("shared", {"mode": "sqlite"})
    sqlite_service.close()

    reopened = MemoryService(backend="sqlite", sqlite_path=str(sqlite_path))
    assert reopened.load_context("shared") == {"mode": "sqlite"}
    assert memory_only.load_context("shared") == {"mode": "memory"}
    reopened.close()


def test_key_overwrite_missing_key_and_serialization_edges(tmp_path: Path) -> None:
    in_memory = MemoryService(backend="memory")
    assert in_memory.load_context("missing") is None

    in_memory.save_context("same", {"v": 1})
    in_memory.save_context("same", {"v": 2})
    assert in_memory.load_context("same") == {"v": 2}

    sqlite_service = MemoryService(backend="sqlite", sqlite_path=str(tmp_path / "edge.db"))
    sqlite_service.save_context("same", {"v": 1})
    sqlite_service.save_context("same", {"v": 3})
    assert sqlite_service.load_context("same") == {"v": 3}
    assert sqlite_service.load_context("missing") is None

    with pytest.raises(TypeError):
        sqlite_service.save_context("bad", {"value": {1, 2, 3}})

    sqlite_service.close()


def test_sqlite_ttl_expiry_uses_deterministic_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = FakeClock(5_000.0)
    monkeypatch.setattr(memory_module.time, "time", clock.time)

    service = MemoryService(
        backend="sqlite",
        sqlite_path=str(tmp_path / "ttl.sqlite"),
        default_ttl_seconds=30,
    )
    service.save_context("k", {"payload": True})

    clock.advance(29)
    assert service.load_context("k") == {"payload": True}

    clock.advance(1)
    assert service.load_context("k") is None
    service.close()
