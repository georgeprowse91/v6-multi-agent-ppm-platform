from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from services.scope_baseline import scope_baseline_service as baseline_service


@pytest.fixture
def scope_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "scope_baselines.db"
    monkeypatch.setenv("SCOPE_BASELINE_DB_URL", f"sqlite:///{db_path}")
    return db_path


def test_sqlite_crud_lifecycle_and_constraints(scope_db: Path) -> None:
    payload = {"version": "1.0", "created_by": "qa", "summary": "first"}
    baseline_id = baseline_service.create_baseline("PRJ-1", payload)

    fetched = baseline_service.retrieve_baseline(baseline_id)
    assert fetched["baseline_id"] == baseline_id
    assert fetched["project_id"] == "PRJ-1"
    assert fetched["data"]["summary"] == "first"

    baseline_service.create_baseline(
        "PRJ-1",
        {
            "baseline_id": baseline_id,
            "version": "2.0",
            "created_by": "qa",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "summary": "updated",
        },
    )
    updated = baseline_service.retrieve_baseline(baseline_id)
    assert updated["version"] == "2.0"
    assert updated["data"]["summary"] == "updated"

    listed = baseline_service.list_baselines("PRJ-1")
    assert len(listed) == 1
    assert listed[0]["baseline_id"] == baseline_id

    with pytest.raises(ValueError, match="Baseline not found"):
        baseline_service.retrieve_baseline("missing")

    with pytest.raises(sqlite3.IntegrityError):
        baseline_service.create_baseline(None, {"created_by": "qa"})  # type: ignore[arg-type]


def test_concurrent_update_read_and_invalid_inputs(scope_db: Path) -> None:
    baseline_id = baseline_service.create_baseline(
        "PRJ-2",
        {
            "baseline_id": "BL-PRJ-2-fixed",
            "version": "0",
            "created_by": "qa",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "counter": 0,
        },
    )

    exceptions: list[Exception] = []

    def writer() -> None:
        try:
            for i in range(1, 21):
                baseline_service.create_baseline(
                    "PRJ-2",
                    {
                        "baseline_id": baseline_id,
                        "version": str(i),
                        "created_by": "qa",
                        "timestamp": f"2024-01-01T00:00:{i:02d}+00:00",
                        "counter": i,
                    },
                )
        except Exception as exc:  # pragma: no cover
            exceptions.append(exc)

    def reader() -> None:
        try:
            for _ in range(50):
                record = baseline_service.retrieve_baseline(baseline_id)
                assert record["baseline_id"] == baseline_id
                assert record["project_id"] == "PRJ-2"
        except Exception as exc:  # pragma: no cover
            exceptions.append(exc)

    writer_thread = threading.Thread(target=writer)
    reader_thread = threading.Thread(target=reader)
    writer_thread.start()
    reader_thread.start()
    writer_thread.join()
    reader_thread.join()

    assert exceptions == []
    assert baseline_service.retrieve_baseline(baseline_id)["data"]["counter"] == 20

    with pytest.raises(TypeError):
        baseline_service.create_baseline("PRJ-2", {"bad": {"non_serializable": set()}})
