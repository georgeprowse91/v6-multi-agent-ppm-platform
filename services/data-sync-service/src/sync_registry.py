from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from typing import Any

from jira_tasks_sync import JiraTasksSyncJob, SyncResult


@dataclass
class SyncJobDefinition:
    connector: str
    entity: str
    interval_seconds: int
    strategy: str
    description: str
    run: Callable[[bool], SyncResult]
    write_back: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None


@dataclass
class SyncJobState:
    last_run_at: str | None = None
    last_status: str | None = None
    last_latency_ms: int | None = None
    last_error: str | None = None
    next_run_at: str | None = None


class SyncJobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], SyncJobDefinition] = {}

    def register(self, job: SyncJobDefinition) -> None:
        key = (job.connector, job.entity)
        self._jobs[key] = job

    def list_jobs(self) -> list[SyncJobDefinition]:
        return list(self._jobs.values())

    def get_job(self, connector: str, entity: str) -> SyncJobDefinition | None:
        return self._jobs.get((connector, entity))


class SyncScheduler:
    def __init__(self, registry: SyncJobRegistry) -> None:
        self.registry = registry
        self._threads: dict[tuple[str, str], Thread] = {}
        self._stops: dict[tuple[str, str], Event] = {}
        self._states: dict[tuple[str, str], SyncJobState] = {}

    def start(self) -> None:
        for job in self.registry.list_jobs():
            key = (job.connector, job.entity)
            if key in self._threads:
                continue
            stop_event = Event()
            thread = Thread(
                target=self._run_loop,
                name=f"sync-{job.connector}-{job.entity}",
                args=(job, stop_event),
                daemon=True,
            )
            self._stops[key] = stop_event
            self._threads[key] = thread
            thread.start()

    def stop(self) -> None:
        for key, stop_event in self._stops.items():
            stop_event.set()
        for key, thread in self._threads.items():
            if thread.is_alive():
                thread.join(timeout=1)

    def run_job(self, connector: str, entity: str, dry_run: bool = False) -> SyncResult:
        job = self.registry.get_job(connector, entity)
        if not job:
            raise ValueError("Job not found")
        return self._execute(job, dry_run)

    def get_state(self, connector: str, entity: str) -> SyncJobState:
        return self._states.get((connector, entity), SyncJobState())

    def _run_loop(self, job: SyncJobDefinition, stop_event: Event) -> None:
        key = (job.connector, job.entity)
        while not stop_event.is_set():
            self._execute(job, dry_run=False)
            next_run = datetime.now(timezone.utc) + timedelta(seconds=job.interval_seconds)
            state = self._states.get(key, SyncJobState())
            state.next_run_at = next_run.isoformat()
            self._states[key] = state
            stop_event.wait(job.interval_seconds)

    def _execute(self, job: SyncJobDefinition, dry_run: bool) -> SyncResult:
        key = (job.connector, job.entity)
        state = self._states.get(key, SyncJobState())
        start = datetime.now(timezone.utc)
        result = job.run(dry_run)
        state.last_run_at = start.isoformat()
        state.last_status = result.status
        state.last_latency_ms = result.latency_ms
        state.last_error = result.errors[0] if result.errors else None
        state.next_run_at = (
            datetime.now(timezone.utc) + timedelta(seconds=job.interval_seconds)
        ).isoformat()
        self._states[key] = state
        return result


_registry = SyncJobRegistry()
_scheduler = SyncScheduler(_registry)


def build_default_registry() -> None:
    jira_job = JiraTasksSyncJob(strategy="source_of_truth")
    _registry.register(
        SyncJobDefinition(
            connector="jira",
            entity="tasks",
            interval_seconds=300,
            strategy=jira_job.strategy,
            description="Sync Jira issues into internal tasks",
            run=jira_job.run,
            write_back=jira_job.write_back,
        )
    )


def get_registry() -> SyncJobRegistry:
    return _registry


def get_scheduler() -> SyncScheduler:
    return _scheduler
