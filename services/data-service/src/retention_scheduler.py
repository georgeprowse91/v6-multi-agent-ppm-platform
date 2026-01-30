from __future__ import annotations

from datetime import datetime, timezone, timedelta
import asyncio
from threading import Event, Thread

from storage import DataServiceStore


class RetentionScheduler:
    def __init__(self, store: DataServiceStore, interval_seconds: int, retention_days: int) -> None:
        self.store = store
        self.interval_seconds = interval_seconds
        self.retention_days = retention_days
        self._thread: Thread | None = None
        self._stop = Event()
        self._last_pruned_at: str | None = None
        self._last_pruned_count: int = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def snapshot(self) -> dict[str, str | int]:
        return {
            "last_pruned_at": self._last_pruned_at or "",
            "last_pruned_count": self._last_pruned_count,
            "interval_seconds": self.interval_seconds,
            "retention_days": self.retention_days,
        }

    def _run_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._prune()

    def _prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        deleted = asyncio.run(self.store.prune_entities(cutoff))
        self._last_pruned_at = datetime.now(timezone.utc).isoformat()
        self._last_pruned_count = int(deleted)
