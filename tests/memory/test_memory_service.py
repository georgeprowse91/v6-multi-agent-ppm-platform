from __future__ import annotations

import time

from services.memory_service.memory_service import MemoryService


def test_memory_service_save_load_delete_in_memory() -> None:
    service = MemoryService(backend="memory")

    service.save_context("k1", {"foo": "bar"})
    assert service.load_context("k1") == {"foo": "bar"}

    service.delete_context("k1")
    assert service.load_context("k1") is None


def test_memory_service_ttl_expiry_in_memory() -> None:
    service = MemoryService(backend="memory", default_ttl_seconds=1)

    service.save_context("ttl", {"value": 1})
    assert service.load_context("ttl") == {"value": 1}
    time.sleep(1.1)
    assert service.load_context("ttl") is None


def test_memory_service_sqlite_backend_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    service = MemoryService(backend="sqlite", sqlite_path=str(db_path))

    service.save_context("sqlite-key", {"count": 2})
    assert service.load_context("sqlite-key") == {"count": 2}

    service.delete_context("sqlite-key")
    assert service.load_context("sqlite-key") is None
    service.close()
