from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Thread
from typing import Callable

from storage import LineageStore


class RetentionScheduler:
    def __init__(self, store: LineageStore, interval_seconds: int = 3600) -> None:
        self.store = store
        self.interval_seconds = interval_seconds
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

    def snapshot(self) -> dict[str, str | int | None]:
        return {
            "last_pruned_at": self._last_pruned_at,
            "last_pruned_count": self._last_pruned_count,
            "interval_seconds": self.interval_seconds,
        }

    def _run_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._prune()

    def _prune(self) -> None:
        now = datetime.now(timezone.utc)
        deleted = self.store.prune_expired(now)
        self._last_pruned_at = now.isoformat()
        self._last_pruned_count = deleted
