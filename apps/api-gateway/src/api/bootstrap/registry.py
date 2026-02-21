from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from fastapi import FastAPI

logger = logging.getLogger(__name__)

StartupCallable = Callable[[FastAPI], Awaitable[None]]
ShutdownCallable = Callable[[FastAPI], Awaitable[None]]
ReadinessCallable = Callable[[FastAPI], dict[str, Any]]


@dataclass(slots=True)
class StartupComponent:
    name: str
    startup: StartupCallable
    shutdown: ShutdownCallable
    dependencies: tuple[str, ...] = ()
    readiness: ReadinessCallable | None = None
    required: bool = True


@dataclass(slots=True)
class ComponentRuntimeState:
    status: str = "pending"
    detail: str = "not_started"


@dataclass(slots=True)
class StartupFailure(Exception):
    component: str
    message: str
    startup_order: list[str]

    def __str__(self) -> str:
        return (
            f"startup failure in component '{self.component}': {self.message}; "
            f"started_before_failure={self.startup_order}"
        )


@dataclass(slots=True)
class BootstrapRegistry:
    _components: dict[str, StartupComponent] = field(default_factory=dict)
    _startup_sequence: list[str] = field(default_factory=list)

    def register(self, component: StartupComponent) -> None:
        if component.name in self._components:
            raise ValueError(f"component '{component.name}' already registered")
        self._components[component.name] = component

    @property
    def components(self) -> dict[str, StartupComponent]:
        return dict(self._components)

    def _resolve_startup_order(self) -> list[str]:
        indegree: dict[str, int] = {name: 0 for name in self._components}
        graph: dict[str, list[str]] = {name: [] for name in self._components}

        for name, component in self._components.items():
            for dep in component.dependencies:
                if dep not in self._components:
                    raise ValueError(f"component '{name}' depends on unknown component '{dep}'")
                indegree[name] += 1
                graph[dep].append(name)

        queue = deque(sorted([name for name, degree in indegree.items() if degree == 0]))
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in sorted(graph[current]):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._components):
            unresolved = sorted(set(self._components) - set(order))
            raise ValueError(f"cyclic component dependency detected: {unresolved}")
        return order

    async def startup(self, app: FastAPI) -> None:
        app.state.bootstrap_component_state = {
            name: ComponentRuntimeState() for name in self._components
        }
        self._startup_sequence = []
        for name in self._resolve_startup_order():
            component = self._components[name]
            state = app.state.bootstrap_component_state[name]
            try:
                await component.startup(app)
                state.status = "running"
                state.detail = "started"
                self._startup_sequence.append(name)
            except Exception as exc:
                state.status = "failed"
                state.detail = str(exc)
                logger.exception("bootstrap_component_startup_failed", extra={"component": name})
                await self.shutdown(app)
                raise StartupFailure(
                    component=name,
                    message=str(exc),
                    startup_order=list(self._startup_sequence),
                ) from exc

    async def shutdown(self, app: FastAPI) -> None:
        component_state = getattr(app.state, "bootstrap_component_state", {})
        for name in reversed(self._startup_sequence):
            component = self._components[name]
            state = component_state.get(name)
            try:
                await component.shutdown(app)
                if state:
                    state.status = "stopped"
                    state.detail = "stopped"
            except Exception as exc:
                logger.exception("bootstrap_component_shutdown_failed", extra={"component": name})
                if state:
                    state.status = "failed_shutdown"
                    state.detail = str(exc)

    def readiness(self, app: FastAPI) -> dict[str, dict[str, Any]]:
        component_state = getattr(app.state, "bootstrap_component_state", {})
        readiness: dict[str, dict[str, Any]] = {}
        for name, component in self._components.items():
            state = component_state.get(name, ComponentRuntimeState())
            payload: dict[str, Any] = {
                "status": state.status,
                "detail": state.detail,
                "required": component.required,
                "ready": state.status == "running",
            }
            if component.readiness is not None:
                payload.update(component.readiness(app))
            readiness[name] = payload
        return readiness
