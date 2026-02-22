from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGES_ROOT = REPO_ROOT / "packages"
AGENTS_ROOT = REPO_ROOT / "agents"
CONNECTOR_REGISTRY_PATH = REPO_ROOT / "integrations" / "connectors" / "registry" / "connectors.json"
RUNTIME_CONFIG_DIR = Path(__file__).resolve().parent / "config"

for path in [
    REPO_ROOT,
    PACKAGES_ROOT / "data-quality" / "src",
    PACKAGES_ROOT / "contracts" / "src",
    PACKAGES_ROOT / "observability" / "src",
    PACKAGES_ROOT / "security" / "src",
    PACKAGES_ROOT / "llm" / "src",
    PACKAGES_ROOT / "event-bus" / "src",
    PACKAGES_ROOT / "feature-flags" / "src",
    PACKAGES_ROOT / "common" / "src",
    REPO_ROOT / "services" / "data-sync-service" / "src",
    REPO_ROOT / "ops",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common.resilience import (  # noqa: E402
    CircuitBreakerPolicy,
    CircuitOpenError,
    DependencyResilienceConfig,
    ResilienceMiddleware,
    RetryPolicy,
    TimeoutPolicy,
)

try:  # noqa: E402
    from integrations.connectors.sdk.src.base_connector import (
        CircuitBreakerOpenError,
        ConnectorCallFailedError,
        ConnectorSchemaValidationError,
    )
except Exception:  # pragma: no cover - optional import fallback for isolated test runs
    CircuitBreakerOpenError = type("CircuitBreakerOpenError", (Exception,), {})
    ConnectorCallFailedError = type("ConnectorCallFailedError", (Exception,), {})
    ConnectorSchemaValidationError = type("ConnectorSchemaValidationError", (Exception,), {})

from agents.runtime import (  # noqa: E402
    AGENT_CATALOG,
    BaseAgent,
    EventBus,
    get_event_bus,
)
from agents.runtime.src.agent_catalog import get_catalog_entry  # noqa: E402
from runtime_flags import demo_mode_enabled  # noqa: E402


@dataclass(frozen=True)
class _LocalEventRecord:
    topic: str
    payload: dict[str, Any]
    published_at: str


class _LocalEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Any]] = {}
        self._events: list[_LocalEventRecord] = []

    def subscribe(self, topic: str, handler: Any) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        record = _LocalEventRecord(
            topic=topic,
            payload=payload,
            published_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._events.append(record)
        for handler in self._handlers.get(topic, []):
            await handler(payload)

    def get_metrics(self) -> dict[str, int]:
        return {"published": len(self._events)}

    def get_recent_events(self, topic: str | None = None) -> list[_LocalEventRecord]:
        if topic is None:
            return list(self._events)
        return [event for event in self._events if event.topic == topic]


@dataclass(frozen=True)
class ConnectorInfo:
    connector_id: str
    name: str
    manifest_path: str
    status: str
    certification: str


class ConnectorRegistry:
    def __init__(self, registry_path: Path = CONNECTOR_REGISTRY_PATH) -> None:
        self._registry_path = registry_path
        self._connectors = self._load_registry()

    def _load_registry(self) -> dict[str, ConnectorInfo]:
        payload = json.loads(self._registry_path.read_text())
        connectors = {}
        for entry in payload:
            connector = ConnectorInfo(
                connector_id=entry["id"],
                name=entry["name"],
                manifest_path=entry["manifest_path"],
                status=entry["status"],
                certification=entry["certification"],
            )
            connectors[connector.connector_id] = connector
        return connectors

    def list_connectors(self) -> list[ConnectorInfo]:
        return list(self._connectors.values())

    def get_connector(self, connector_id: str) -> ConnectorInfo | None:
        return self._connectors.get(connector_id)


class ConnectorActionClient:
    def __init__(
        self,
        registry: ConnectorRegistry,
        *,
        event_bus: EventBus | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        retry_initial_delay_seconds: float = 0.2,
        circuit_failure_threshold: int = 5,
        circuit_failure_window_seconds: int = 60,
        circuit_recovery_timeout_seconds: int = 30,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_initial_delay_seconds = retry_initial_delay_seconds
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_failure_window_seconds = circuit_failure_window_seconds
        self._circuit_recovery_timeout_seconds = circuit_recovery_timeout_seconds
        self._resilience: dict[str, ResilienceMiddleware] = {}

    def _resolve_entrypoint(self, connector: ConnectorInfo) -> Path:
        manifest_path = Path(connector.manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = REPO_ROOT / manifest_path
        connector_root = manifest_path.parent
        candidates = [
            connector_root / "src" / "main.py",
            connector_root / "main.py",
            connector_root / "src" / "runtime.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise ConnectorActionRuntimeError(
            code="not_found",
            connector_id=connector.connector_id,
            action="resolve_entrypoint",
            message=f"Connector entrypoint not found for {connector.connector_id}",
            http_status=404,
        )

    def _load_entrypoint_module(self, connector: ConnectorInfo) -> Any:
        module_path = self._resolve_entrypoint(connector)
        module_name = f"connector_entrypoint_{connector.connector_id}_{hash(module_path)}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ConnectorActionRuntimeError(
                code="not_found",
                connector_id=connector.connector_id,
                action="load_module",
                message=f"Unable to load connector module for {connector.connector_id}",
                http_status=404,
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _resolve_action_callable(self, module: Any, action: str) -> tuple[Any, str]:
        function_candidates = [
            "execute_action",
            action,
            f"run_{action}",
            "run_action",
        ]
        for function_name in function_candidates:
            handler = getattr(module, function_name, None)
            if callable(handler):
                return handler, function_name
        write_aliases = {"create", "write", "update", "delete", "create_record", "create_issue"}
        canonical = "run_write" if action.lower() in write_aliases else "run_sync"
        handler = getattr(module, canonical, None)
        if callable(handler):
            return handler, canonical
        raise AttributeError(f"No executable handler found for action '{action}'")

    def _invoke_action(
        self,
        handler: Any,
        handler_name: str,
        *,
        action: str,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        if handler_name == "run_write":
            return handler(
                fixture_path=None,
                tenant_id=context.get("tenant_id") or "default",
                live=True,
                data=payload.get("data") if isinstance(payload.get("data"), list) else [payload],
            )
        if handler_name == "run_sync":
            return handler(
                fixture_path=Path(payload["fixture_path"]) if payload.get("fixture_path") else None,
                tenant_id=context.get("tenant_id") or "default",
                live=bool(payload.get("live", False)),
                include_schema=bool(payload.get("include_schema", False)),
            )
        kwargs = {
            "action": action,
            "payload": payload,
            "context": context,
        }
        signature = inspect.signature(handler)
        accepts_kwargs = any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
        )
        accepted = {k: v for k, v in kwargs.items() if accepts_kwargs or k in signature.parameters}
        if accepted:
            return handler(**accepted)
        return handler(payload)

    async def _emit_event(self, topic: str, payload: dict[str, Any]) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(topic, payload)

    def _resilience_for(self, connector_id: str) -> ResilienceMiddleware:
        if connector_id not in self._resilience:
            self._resilience[connector_id] = ResilienceMiddleware(
                DependencyResilienceConfig(
                    dependency=f"connector_action_{connector_id}",
                    retry=RetryPolicy(
                        max_attempts=self._max_retries + 1,
                        initial_backoff_s=self._retry_initial_delay_seconds,
                    ),
                    timeout=TimeoutPolicy(timeout_s=self._timeout_seconds),
                    circuit_breaker=CircuitBreakerPolicy(
                        failure_threshold=self._circuit_failure_threshold,
                        failure_window_s=float(self._circuit_failure_window_seconds),
                        recovery_timeout_s=float(self._circuit_recovery_timeout_seconds),
                    ),
                )
            )
        return self._resilience[connector_id]

    def _normalize_output(
        self,
        *,
        connector_id: str,
        action: str,
        result: Any,
        duration_ms: int,
    ) -> dict[str, Any]:
        if isinstance(result, dict) and {"status", "data", "errors"}.issubset(result.keys()):
            output = {
                "status": result["status"],
                "data": result["data"],
                "errors": result["errors"],
            }
        else:
            output = {
                "status": "completed",
                "data": result if result is not None else {},
                "errors": [],
            }
        output.update(
            {
                "connector_id": connector_id,
                "action": action,
                "duration_ms": duration_ms,
            }
        )
        self._validate_output_contract(output)
        return output

    def _validate_output_contract(self, output: dict[str, Any]) -> None:
        required = {
            "status": str,
            "data": (dict, list, str, int, float, bool, type(None)),
            "errors": list,
            "connector_id": str,
            "action": str,
            "duration_ms": int,
        }
        for key, expected in required.items():
            if key not in output:
                raise ConnectorActionRuntimeError(
                    code="validation_failed",
                    connector_id=output.get("connector_id", "unknown"),
                    action=output.get("action", "unknown"),
                    message=f"Connector output missing required field '{key}'",
                    http_status=422,
                )
            if not isinstance(output[key], expected):
                raise ConnectorActionRuntimeError(
                    code="validation_failed",
                    connector_id=output.get("connector_id", "unknown"),
                    action=output.get("action", "unknown"),
                    message=f"Connector output field '{key}' has invalid type",
                    http_status=422,
                )

    def _map_exception(
        self, connector_id: str, action: str, exc: Exception
    ) -> ConnectorActionRuntimeError:
        lowered = str(exc).lower()
        if isinstance(exc, ConnectorActionRuntimeError):
            return exc
        if isinstance(exc, (FileNotFoundError, ModuleNotFoundError, AttributeError, KeyError)):
            return ConnectorActionRuntimeError(
                code="not_found",
                connector_id=connector_id,
                action=action,
                message=str(exc),
                http_status=404,
            )
        if isinstance(exc, (PermissionError,)) or any(
            token in lowered for token in ("auth", "unauthorized", "forbidden", "invalid token")
        ):
            return ConnectorActionRuntimeError(
                code="auth_failed",
                connector_id=connector_id,
                action=action,
                message=str(exc),
                http_status=401,
            )
        if isinstance(exc, (ValueError, TypeError, ConnectorSchemaValidationError)):
            return ConnectorActionRuntimeError(
                code="validation_failed",
                connector_id=connector_id,
                action=action,
                message=str(exc),
                http_status=422,
            )
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in lowered:
            return ConnectorActionRuntimeError(
                code="timeout",
                connector_id=connector_id,
                action=action,
                message=str(exc) or "Connector action timed out",
                http_status=504,
                retriable=True,
            )
        if isinstance(
            exc, (CircuitOpenError, CircuitBreakerOpenError, ConnectorCallFailedError, RuntimeError)
        ):
            return ConnectorActionRuntimeError(
                code="upstream_unavailable",
                connector_id=connector_id,
                action=action,
                message=str(exc),
                http_status=503,
                retriable=True,
            )
        return ConnectorActionRuntimeError(
            code="upstream_unavailable",
            connector_id=connector_id,
            action=action,
            message=str(exc),
            http_status=503,
        )

    async def execute(
        self,
        *,
        connector_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        execution_payload = payload or {}
        execution_context = {
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            **(context or {}),
        }
        await self._emit_event(
            "connector.action.started",
            {
                "connector_id": connector_id,
                "action": action,
                "category": "connector_action",
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            },
        )
        connector = self._registry.get_connector(connector_id)
        if not connector:
            error = ConnectorActionRuntimeError(
                code="not_found",
                connector_id=connector_id,
                action=action,
                message=f"Unknown connector: {connector_id}",
                http_status=404,
            )
            await self._emit_event(
                "connector.action.failed",
                {
                    "connector_id": connector_id,
                    "action": action,
                    "category": "connector_action",
                    "error": error.to_response(),
                },
            )
            raise error

        module = self._load_entrypoint_module(connector)
        handler, handler_name = self._resolve_action_callable(module, action)
        resilience = self._resilience_for(connector.connector_id)

        async def _operation() -> Any:
            result = self._invoke_action(
                handler,
                handler_name,
                action=action,
                payload=execution_payload,
                context=execution_context,
            )
            if hasattr(result, "__await__"):
                return await result
            return result

        try:
            result = await resilience.execute_async(_operation)
            duration_ms = int((time.perf_counter() - start) * 1000)
            normalized = self._normalize_output(
                connector_id=connector.connector_id,
                action=action,
                result=result,
                duration_ms=duration_ms,
            )
            await self._emit_event(
                "connector.action.succeeded",
                {
                    "connector_id": connector.connector_id,
                    "action": action,
                    "category": "connector_action",
                    "latency_ms": duration_ms,
                    "status": normalized["status"],
                },
            )
            return normalized
        except Exception as exc:  # noqa: BLE001
            mapped_error = self._map_exception(connector.connector_id, action, exc)
            duration_ms = int((time.perf_counter() - start) * 1000)
            await self._emit_event(
                "connector.action.failed",
                {
                    "connector_id": connector.connector_id,
                    "action": action,
                    "category": "connector_action",
                    "latency_ms": duration_ms,
                    "error": mapped_error.to_response(),
                },
            )
            raise mapped_error from exc


class ConnectorActionRuntimeError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        connector_id: str,
        action: str,
        message: str,
        http_status: int,
        retriable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.connector_id = connector_id
        self.action = action
        self.message = message
        self.http_status = http_status
        self.retriable = retriable

    def to_response(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "connector_id": self.connector_id,
            "action": self.action,
            "retriable": self.retriable,
        }


class WorkflowEngineClient:
    def __init__(self, agent: BaseAgent) -> None:
        self._agent = agent

    async def execute(self, *, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._agent.execute({"action": action, **payload})


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    path: Path
    config: dict[str, Any]
    class_name: str | None = None

    @property
    def fixture_dir(self) -> Path:
        return self.path.parent.parent / "demo-fixtures"


class AgentRuntime:
    def __init__(
        self,
        *,
        data_dir: Path | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._data_dir = data_dir or Path(
            os.getenv("AGENT_RUNTIME_DATA_DIR", "/tmp/agent-runtime-data")
        )
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus or self._build_event_bus()
        self._connector_registry = ConnectorRegistry()
        self._connector_client = ConnectorActionClient(
            self._connector_registry, event_bus=self._event_bus
        )
        self._agent_registry: dict[str, BaseAgent] = {}
        self._demo_mode = demo_mode_enabled()
        self._demo_fixtures: dict[str, dict[str, Any]] = {}
        self._orchestration_config: dict[str, Any] = {
            "default_routing": [],
            "last_updated_by": "system",
        }
        self._initialize_agents()
        self._event_bus.subscribe("agent.requested", self._handle_agent_request)

    def _build_event_bus(self) -> EventBus:
        try:
            return get_event_bus()
        except Exception:
            return _LocalEventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def connector_registry(self) -> ConnectorRegistry:
        return self._connector_registry

    @property
    def connector_client(self) -> ConnectorActionClient:
        return self._connector_client

    @property
    def agent_registry(self) -> dict[str, BaseAgent]:
        return self._agent_registry

    def list_agents(self) -> list[dict[str, Any]]:
        catalog_lookup = {entry.agent_id: entry for entry in AGENT_CATALOG}
        agents = []
        for agent_id, agent in self._agent_registry.items():
            entry = catalog_lookup.get(agent_id)
            agents.append(
                {
                    "agent_id": agent_id,
                    "catalog_id": entry.catalog_id if entry else agent_id,
                    "display_name": entry.display_name if entry else agent_id,
                    "component_name": entry.component_name if entry else agent_id,
                    "capabilities": agent.get_capabilities(),
                }
            )
        return sorted(agents, key=lambda item: item["agent_id"])

    def get_orchestration_config(self) -> dict[str, Any]:
        return self._orchestration_config

    def set_orchestration_config(self, config: dict[str, Any]) -> None:
        self._orchestration_config = config

    async def execute_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._demo_mode:
            demo_response = self._demo_fixtures.get(agent_id)
            if demo_response is not None:
                return demo_response

        agent = self._agent_registry.get(agent_id)
        if not agent:
            raise KeyError(f"Agent {agent_id} not registered")

        connector_actions = payload.pop("connector_actions", None)
        workflow_action = payload.pop("workflow_action", None)
        connector_results: list[dict[str, Any]] | None = None

        if connector_actions:
            connector_results = []
            for action in connector_actions:
                connector_results.append(
                    await self._connector_client.execute(
                        connector_id=action["connector_id"],
                        action=action["action"],
                        payload=action.get("payload", {}),
                        tenant_id=payload.get("tenant_id"),
                        correlation_id=payload.get("correlation_id"),
                        context=(
                            payload.get("context")
                            if isinstance(payload.get("context"), dict)
                            else None
                        ),
                    )
                )
            payload["connector_results"] = connector_results

        workflow_result: dict[str, Any] | None = None
        if workflow_action:
            workflow_agent = self._agent_registry.get("agent_024")
            if workflow_agent:
                workflow_client = WorkflowEngineClient(workflow_agent)
                workflow_result = await workflow_client.execute(
                    action=workflow_action["action"],
                    payload=workflow_action.get("payload", {}),
                )
                payload["workflow_result"] = workflow_result

        response = await agent.execute(payload)
        if connector_results and response.get("success") and isinstance(response.get("data"), dict):
            response["data"]["connector_results"] = connector_results
        if workflow_result and response.get("success") and isinstance(response.get("data"), dict):
            response["data"]["workflow_result"] = workflow_result
        return response

    async def _handle_agent_request(self, payload: dict[str, Any]) -> None:
        agent_id = payload.get("agent_id")
        if not agent_id:
            return
        agent = self._agent_registry.get(agent_id)
        if not agent:
            await self._event_bus.publish(
                "agent.failed",
                {"agent_id": agent_id, "error": "unknown_agent"},
            )
            return
        response = await self.execute_agent(agent_id, payload.get("payload", {}))
        await self._event_bus.publish(
            "agent.completed",
            {"agent_id": agent_id, "response": response},
        )

    def _load_agent_class(self, path: Path, class_name: str | None = None) -> type[BaseAgent]:
        if str(path.parent) not in sys.path:
            sys.path.insert(0, str(path.parent))
        module_name = f"agent_module_{path.stem}_{hash(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load agent module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        candidates = [
            obj
            for obj in module.__dict__.values()
            if isinstance(obj, type) and issubclass(obj, BaseAgent) and obj is not BaseAgent
        ]
        if class_name:
            for candidate in candidates:
                if candidate.__name__ == class_name:
                    return candidate
            names = ", ".join(sorted(cls.__name__ for cls in candidates))
            raise ImportError(f"Agent class {class_name} not found in {path}. Found: {names}")
        if len(candidates) != 1:
            names = ", ".join(sorted(cls.__name__ for cls in candidates))
            raise ImportError(f"Expected 1 agent class in {path}, found: {names}")
        return candidates[0]

    def _build_store_path(self, filename: str) -> str:
        return str(self._data_dir / filename)

    def _build_agent_specs(self) -> list[AgentSpec]:
        llm_provider = os.getenv("AGENT_RUNTIME_LLM_PROVIDER", "mock")
        base_config = {
            "event_bus": self._event_bus,
            "llm_provider": llm_provider,
        }
        specs: list[AgentSpec] = [
            AgentSpec(
                agent_id="intent-router",
                path=AGENTS_ROOT
                / "core-orchestration"
                / "agent-01-intent-router"
                / "src"
                / "intent_router_agent.py",
                config={
                    **base_config,
                    "routing_config_path": str(RUNTIME_CONFIG_DIR / "intent-routing.yaml"),
                },
            ),
            AgentSpec(
                agent_id="response-orchestration",
                path=AGENTS_ROOT
                / "core-orchestration"
                / "agent-02-response-orchestration"
                / "src"
                / "response_orchestration_agent.py",
                config={
                    **base_config,
                    "event_bus": self._event_bus,
                    "agent_registry": self._agent_registry,
                },
            ),
            AgentSpec(
                agent_id="agent_003_approval_workflow",
                path=AGENTS_ROOT
                / "core-orchestration"
                / "agent-03-approval-workflow"
                / "src"
                / "approval_workflow_agent.py",
                config={
                    **base_config,
                    "approval_store_path": self._build_store_path("approval_store.json"),
                },
            ),
            AgentSpec(
                agent_id="demand-intake",
                path=AGENTS_ROOT
                / "portfolio-management"
                / "agent-04-demand-intake"
                / "src"
                / "demand_intake_agent.py",
                config={
                    **base_config,
                    "demand_store_path": self._build_store_path("demand_intake_store.json"),
                },
            ),
            AgentSpec(
                agent_id="business-case-investment",
                path=AGENTS_ROOT
                / "portfolio-management"
                / "agent-05-business-case-investment"
                / "src"
                / "business_case_investment_agent.py",
                config={
                    **base_config,
                    "business_case_store_path": self._build_store_path("business_case_store.json"),
                },
            ),
            AgentSpec(
                agent_id="portfolio-strategy-optimization",
                path=AGENTS_ROOT
                / "portfolio-management"
                / "agent-06-portfolio-strategy-optimisation"
                / "src"
                / "portfolio_strategy_agent.py",
                config={
                    **base_config,
                    "portfolio_store_path": self._build_store_path("portfolio_strategy_store.json"),
                },
            ),
            AgentSpec(
                agent_id="program-management",
                path=AGENTS_ROOT
                / "portfolio-management"
                / "agent-07-program-management"
                / "src"
                / "program_management_agent.py",
                config={
                    **base_config,
                    "program_store_path": self._build_store_path("program_store.json"),
                    "program_roadmap_store_path": self._build_store_path(
                        "program_roadmap_store.json"
                    ),
                    "program_dependency_store_path": self._build_store_path(
                        "program_dependency_store.json"
                    ),
                },
            ),
            AgentSpec(
                agent_id="project-definition",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-08-project-definition-scope"
                / "src"
                / "project_definition_agent.py",
                config={
                    **base_config,
                    "charter_store_path": self._build_store_path("project_charters.json"),
                    "wbs_store_path": self._build_store_path("project_wbs.json"),
                },
                class_name="ProjectDefinitionAgent",
            ),
            AgentSpec(
                agent_id="project-lifecycle-governance",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-09-lifecycle-governance"
                / "src"
                / "project_lifecycle_agent.py",
                config={
                    **base_config,
                    "lifecycle_store_path": self._build_store_path("project_lifecycle.json"),
                    "health_store_path": self._build_store_path("project_health_history.json"),
                },
                class_name="ProjectLifecycleAgent",
            ),
            AgentSpec(
                agent_id="schedule-planning",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-10-schedule-planning"
                / "src"
                / "schedule_planning_agent.py",
                config={
                    **base_config,
                    "schedule_store_path": self._build_store_path("project_schedules.json"),
                    "schedule_baseline_store_path": self._build_store_path(
                        "schedule_baselines.json"
                    ),
                },
                class_name="SchedulePlanningAgent",
            ),
            AgentSpec(
                agent_id="resource-capacity-management",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-11-resource-capacity"
                / "src"
                / "resource_capacity_agent.py",
                config={
                    **base_config,
                    "resource_store_path": self._build_store_path("resource_pool.json"),
                    "allocation_store_path": self._build_store_path("resource_allocations.json"),
                },
            ),
            AgentSpec(
                agent_id="financial-management",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-12-financial-management"
                / "src"
                / "financial_management_agent.py",
                config={
                    **base_config,
                    "budget_store_path": self._build_store_path("financial_budgets.json"),
                    "actuals_store_path": self._build_store_path("financial_actuals.json"),
                    "forecast_store_path": self._build_store_path("financial_forecasts.json"),
                },
                class_name="FinancialManagementAgent",
            ),
            AgentSpec(
                agent_id="agent_013",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-13-vendor-procurement"
                / "src"
                / "vendor_procurement_agent.py",
                config={
                    **base_config,
                    "vendor_store_path": self._build_store_path("vendors.json"),
                    "contract_store_path": self._build_store_path("vendor_contracts.json"),
                    "invoice_store_path": self._build_store_path("vendor_invoices.json"),
                },
                class_name="VendorProcurementAgent",
            ),
            AgentSpec(
                agent_id="agent_014",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-14-quality-management"
                / "src"
                / "quality_management_agent.py",
                config={
                    **base_config,
                    "quality_plan_store_path": self._build_store_path("quality_plans.json"),
                    "test_case_store_path": self._build_store_path("quality_test_cases.json"),
                    "defect_store_path": self._build_store_path("quality_defects.json"),
                    "audit_store_path": self._build_store_path("quality_audits.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_015",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-15-risk-issue-management"
                / "src"
                / "risk_management_agent.py",
                config={
                    **base_config,
                    "risk_store_path": self._build_store_path("risk_register.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_016",
                path=AGENTS_ROOT
                / "delivery-management"
                / "agent-16-compliance-regulatory"
                / "src"
                / "compliance_regulatory_agent.py",
                config={
                    **base_config,
                    "evidence_store_path": self._build_store_path("compliance_evidence.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_017",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-17-change-configuration"
                / "src"
                / "change_configuration_agent.py",
                config={
                    **base_config,
                    "change_store_path": self._build_store_path("change_requests.json"),
                    "cmdb_store_path": self._build_store_path("cmdb.json"),
                },
                class_name="ChangeConfigurationAgent",
            ),
            AgentSpec(
                agent_id="agent_018",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-18-release-deployment"
                / "src"
                / "release_deployment_agent.py",
                config={
                    **base_config,
                    "release_store_path": self._build_store_path("release_calendar.json"),
                    "deployment_plan_store_path": self._build_store_path("deployment_plans.json"),
                },
                class_name="ReleaseDeploymentAgent",
            ),
            AgentSpec(
                agent_id="agent_019",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-19-knowledge-document-management"
                / "src"
                / "knowledge_management_agent.py",
                config={
                    **base_config,
                    "document_store_path": self._build_store_path("knowledge_documents.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_020",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-20-continuous-improvement-process-mining"
                / "src"
                / "process_mining_agent.py",
                config={
                    **base_config,
                    "event_log_store_path": self._build_store_path("process_event_logs.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_021",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-21-stakeholder-comms"
                / "src"
                / "stakeholder_communications_agent.py",
                config={
                    **base_config,
                    "stakeholder_store_path": self._build_store_path("stakeholders.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_022",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-22-analytics-insights"
                / "src"
                / "analytics_insights_agent.py",
                config={
                    **base_config,
                    "analytics_output_store_path": self._build_store_path("analytics_outputs.json"),
                    "analytics_alert_store_path": self._build_store_path("analytics_alerts.json"),
                    "analytics_lineage_store_path": self._build_store_path(
                        "analytics_lineage.json"
                    ),
                    "health_snapshot_store_path": self._build_store_path("health_snapshots.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_023",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-23-data-synchronisation-quality"
                / "src"
                / "data_sync_agent.py",
                config={
                    **base_config,
                    "master_record_store_path": self._build_store_path("master_records.json"),
                    "sync_event_store_path": self._build_store_path("sync_events.json"),
                    "sync_lineage_store_path": self._build_store_path("lineage/sync_lineage.json"),
                    "sync_audit_store_path": self._build_store_path("sync_audit_events.json"),
                },
            ),
            AgentSpec(
                agent_id="agent_024",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-24-workflow-process-engine"
                / "src"
                / "workflow_engine_agent.py",
                config={
                    **base_config,
                    "workflow_definition_store_path": self._build_store_path("workflows.json"),
                    "workflow_instance_store_path": self._build_store_path(
                        "workflow_instances.json"
                    ),
                    "workflow_task_store_path": self._build_store_path("workflow_tasks.json"),
                    "workflow_event_store_path": self._build_store_path("workflow_events.json"),
                    "workflow_subscription_store_path": self._build_store_path(
                        "workflow_subscriptions.json"
                    ),
                },
            ),
            AgentSpec(
                agent_id="agent_025",
                path=AGENTS_ROOT
                / "operations-management"
                / "agent-25-system-health-monitoring"
                / "src"
                / "system_health_agent.py",
                config={
                    **base_config,
                    "alert_store_path": self._build_store_path("alerts.json"),
                    "incident_store_path": self._build_store_path("incidents.json"),
                },
            ),
        ]
        return specs

    def _initialize_agents(self) -> None:
        specs = self._build_agent_specs()
        for spec in specs:
            fixture_payload = self._load_demo_fixture(spec.fixture_dir)
            if fixture_payload is not None:
                if isinstance(fixture_payload, dict) and "scripted_response" in fixture_payload:
                    self._demo_fixtures[spec.agent_id] = fixture_payload["scripted_response"]
                else:
                    self._demo_fixtures[spec.agent_id] = fixture_payload

        if self._demo_mode:
            return

        for spec in specs:
            if str(spec.path.parent) not in sys.path:
                sys.path.insert(0, str(spec.path.parent))

        for spec in specs:
            agent_cls = self._load_agent_class(spec.path, spec.class_name)
            agent = agent_cls(agent_id=spec.agent_id, config=spec.config)
            self._agent_registry[spec.agent_id] = agent

        response_agent = self._agent_registry.get("response-orchestration")
        if response_agent is not None:
            response_agent.agent_registry = self._agent_registry

        for agent_id in list(self._agent_registry):
            entry = get_catalog_entry(agent_id)
            if entry:
                self._agent_registry[agent_id].catalog_id = entry.catalog_id

    def _load_demo_fixture(self, fixture_dir: Path) -> dict[str, Any] | None:
        if not fixture_dir.exists():
            return None
        fixture_file = next(
            (
                candidate
                for candidate in [
                    "sample-response.json",
                    "sample-response.yaml",
                    "sample-response.yml",
                ]
                if (fixture_dir / candidate).exists()
            ),
            None,
        )
        if fixture_file is None:
            return None
        fixture_path = fixture_dir / fixture_file
        if fixture_path.suffix == ".json":
            return json.loads(fixture_path.read_text())
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PyYAML is required to parse YAML demo fixtures") from exc
        return yaml.safe_load(fixture_path.read_text())
