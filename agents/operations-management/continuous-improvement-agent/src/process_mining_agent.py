"""
Continuous Improvement & Process Mining Agent

Purpose:
Facilitates ongoing improvement by analyzing execution data to uncover inefficiencies,
bottlenecks and deviations, and by managing improvement initiatives.

Specification: agents/operations-management/continuous-improvement-agent/README.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Action handlers ---------------------------------------------------------
from ci_actions.benchmarking import benchmark_performance, share_best_practices
from ci_actions.conformance import (
    check_conformance,
    detect_bottlenecks,
    detect_deviations,
)
from ci_actions.discovery import discover_process
from ci_actions.improvement import (
    complete_improvement,
    create_improvement,
    get_improvement_backlog,
    get_improvement_history,
    prioritize_improvements,
    track_benefits,
)
from ci_actions.ingest import ingest_analytics_report, ingest_event_log
from ci_actions.insights import (
    get_conformance_report,
    get_kpi_report,
    get_process_insights,
    get_process_model,
    get_recommendations,
)
from ci_actions.root_cause import analyze_root_cause

# Utilities ---------------------------------------------------------------
from mining_utils import calculate_compliance_rate, resolve_store_path

from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class ProcessMiningAgent(BaseAgent):
    """
    Continuous Improvement & Process Mining Agent - Analyzes processes for optimization.

    Key Capabilities:
    - Process discovery and visualization
    - Bottleneck and deviation detection
    - Root cause analysis and recommendations
    - Improvement backlog management
    - Benefit realization tracking
    - Benchmarking and best practices
    - Improvement culture enablement
    """

    def __init__(
        self, agent_id: str = "continuous-improvement-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.bottleneck_threshold = config.get("bottleneck_threshold", 0.20) if config else 0.20
        self.deviation_threshold = config.get("deviation_threshold", 0.15) if config else 0.15
        self.min_frequency_threshold = config.get("min_frequency_threshold", 5) if config else 5

        # Process mining algorithms
        self.mining_algorithms = (
            config.get(
                "mining_algorithms",
                ["alpha_miner", "inductive_miner", "heuristic_miner", "fuzzy_miner"],
            )
            if config
            else ["alpha_miner", "inductive_miner", "heuristic_miner", "fuzzy_miner"]
        )

        event_log_store_path = resolve_store_path(
            config, "event_log_store_path", "data/process_event_logs.json"
        )
        process_model_store_path = resolve_store_path(
            config, "process_model_store_path", "data/process_models.json"
        )
        conformance_store_path = resolve_store_path(
            config, "conformance_store_path", "data/process_conformance.json"
        )
        recommendations_store_path = resolve_store_path(
            config, "recommendations_store_path", "data/process_recommendations.json"
        )
        improvement_history_store_path = resolve_store_path(
            config, "improvement_history_store_path", "data/improvement_history.json"
        )
        improvement_backlog_store_path = resolve_store_path(
            config, "improvement_backlog_store_path", "data/improvement_backlog.json"
        )

        self.event_log_store = TenantStateStore(event_log_store_path)
        self.process_model_store = TenantStateStore(process_model_store_path)
        self.conformance_store = TenantStateStore(conformance_store_path)
        self.recommendations_store = TenantStateStore(recommendations_store_path)
        self.improvement_history_store = TenantStateStore(improvement_history_store_path)
        self.improvement_backlog_store = TenantStateStore(improvement_backlog_store_path)

        # Data stores (will be replaced with database)
        self.event_logs: dict[str, Any] = {}
        self.process_models: dict[str, Any] = {}
        self.improvement_backlog: dict[str, Any] = {}
        self.benefit_tracking: dict[str, Any] = {}
        self.benchmarks: dict[str, Any] = {}
        self.event_log_index: dict[str, list[dict[str, Any]]] = {}
        self.integration_clients = config.get("integration_clients", {}) if config else {}
        self.integration_status: dict[str, bool] = {}
        self.financial_agent = config.get("financial_agent") if config else None
        self.approval_workflow_agent = config.get("approval_workflow_agent") if config else None
        self.knowledge_agent = config.get("knowledge_agent") if config else None
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                self.event_bus = None
        _default_topics = [
            "schedule.created",
            "schedule.updated",
            "task.started",
            "task.completed",
            "deployment.started",
            "deployment.succeeded",
            "deployment.failed",
            "risk.triggered",
            "risk.mitigated",
            "quality.finding.created",
            "quality.finding.closed",
            "approval.requested",
            "approval.granted",
            "approval.rejected",
            "change.requested",
            "change.approved",
            "workflow.step.started",
            "workflow.step.completed",
            "incident.created",
            "incident.resolved",
        ]
        self.event_topics = (
            config.get("event_topics", _default_topics) if config else _default_topics
        )
        self.max_deviation_alerts = config.get("max_deviation_alerts", 5) if config else 5
        self.knowledge_event_topic = (
            config.get("knowledge_event_topic", "agent.summary.created")
            if config
            else "agent.summary.created"
        )
        self.default_improvement_owner = (
            config.get("default_improvement_owner", "continuous-improvement-lead")
            if config
            else "continuous-improvement-lead"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize process mining tools, analytics, and data sources."""
        await super().initialize()
        self.logger.info("Initializing Continuous Improvement & Process Mining Agent...")

        self._register_integrations()
        await self._subscribe_to_event_bus()
        self.logger.info("Continuous Improvement & Process Mining Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "ingest_event_log",
            "discover_process",
            "check_conformance",
            "detect_bottlenecks",
            "detect_deviations",
            "analyze_root_cause",
            "create_improvement",
            "prioritize_improvements",
            "track_benefits",
            "benchmark_performance",
            "share_best_practices",
            "get_process_insights",
            "get_process_model",
            "get_conformance_report",
            "get_recommendations",
            "get_improvement_backlog",
            "get_kpi_report",
            "ingest_analytics_report",
            "complete_improvement",
            "get_improvement_history",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "ingest_event_log":
            if "events" not in input_data:
                self.logger.warning("Missing events data")
                return False

        elif action == "discover_process":
            if "process_id" not in input_data:
                self.logger.warning("Missing process_id")
                return False
        elif action == "check_conformance":
            if "process_id" not in input_data:
                self.logger.warning("Missing process_id")
                return False
            if "expected_model" not in input_data and "process_model_id" not in input_data:
                self.logger.warning("Missing expected_model or process_model_id")
                return False

        return True

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Route ``input_data["action"]`` to the appropriate action handler."""
        action = input_data.get("action", "get_process_insights")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "ingest_event_log":
            return await ingest_event_log(self, tenant_id, input_data.get("events", []))

        elif action == "discover_process":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await discover_process(
                self, tenant_id, process_id, input_data.get("algorithm", "heuristic_miner")
            )
        elif action == "check_conformance":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            expected_model = input_data.get("expected_model")
            process_model_id = input_data.get("process_model_id")
            if expected_model is None and process_model_id:
                expected_model = self.process_models.get(process_model_id, {}).get("model")
            if expected_model is None:
                expected_model = await self._get_designed_process_model(tenant_id, process_id)
            return await check_conformance(self, tenant_id, process_id, expected_model)

        elif action == "detect_bottlenecks":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await detect_bottlenecks(self, tenant_id, process_id)

        elif action == "detect_deviations":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await detect_deviations(self, tenant_id, process_id)

        elif action == "analyze_root_cause":
            process_id = input_data.get("process_id")
            issue_id = input_data.get("issue_id")
            assert isinstance(process_id, str), "process_id must be a string"
            assert isinstance(issue_id, str), "issue_id must be a string"
            return await analyze_root_cause(self, process_id, issue_id)

        elif action == "create_improvement":
            return await create_improvement(self, tenant_id, input_data.get("improvement", {}))

        elif action == "prioritize_improvements":
            return await prioritize_improvements(self)

        elif action == "track_benefits":
            improvement_id = input_data.get("improvement_id")
            assert isinstance(improvement_id, str), "improvement_id must be a string"
            return await track_benefits(self, improvement_id)

        elif action == "benchmark_performance":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await benchmark_performance(
                self, process_id, input_data.get("benchmark_criteria", {})
            )

        elif action == "share_best_practices":
            return await share_best_practices(self, input_data.get("filters", {}))

        elif action == "get_process_insights":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await get_process_insights(self, tenant_id, process_id)
        elif action == "get_process_model":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await get_process_model(self, tenant_id, process_id)
        elif action == "get_conformance_report":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await get_conformance_report(self, tenant_id, process_id)
        elif action == "get_recommendations":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await get_recommendations(self, tenant_id, process_id)

        elif action == "get_improvement_backlog":
            return await get_improvement_backlog(self, input_data.get("filters", {}))
        elif action == "get_kpi_report":
            return await get_kpi_report(self, input_data.get("filters", {}))
        elif action == "ingest_analytics_report":
            return await ingest_analytics_report(
                self,
                tenant_id,
                input_data.get("analytics_report", {}),
            )
        elif action == "complete_improvement":
            improvement_id = input_data.get("improvement_id")
            assert isinstance(improvement_id, str), "improvement_id must be a string"
            return await complete_improvement(
                self,
                tenant_id,
                improvement_id,
                input_data.get("outcome", "completed"),
                input_data.get("completed_by"),
            )
        elif action == "get_improvement_history":
            return await get_improvement_history(self, tenant_id)

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Delegated private methods (preserve backward-compatibility for tests
    # and any code that calls agent._method_name directly)
    # ------------------------------------------------------------------

    async def _ingest_event_log(
        self, tenant_id: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await ingest_event_log(self, tenant_id, events)

    async def _discover_process(
        self, tenant_id: str, process_id: str, algorithm: str = "heuristic_miner"
    ) -> dict[str, Any]:
        return await discover_process(self, tenant_id, process_id, algorithm)

    async def _check_conformance(
        self, tenant_id: str, process_id: str, expected_model: dict[str, Any]
    ) -> dict[str, Any]:
        return await check_conformance(self, tenant_id, process_id, expected_model)

    async def _detect_bottlenecks(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await detect_bottlenecks(self, tenant_id, process_id)

    async def _detect_deviations(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await detect_deviations(self, tenant_id, process_id)

    async def _analyze_root_cause(self, process_id: str, issue_id: str) -> dict[str, Any]:
        return await analyze_root_cause(self, process_id, issue_id)

    async def _create_improvement(
        self, tenant_id: str, improvement_data: dict[str, Any]
    ) -> dict[str, Any]:
        return await create_improvement(self, tenant_id, improvement_data)

    async def _prioritize_improvements(self) -> dict[str, Any]:
        return await prioritize_improvements(self)

    async def _track_benefits(self, improvement_id: str, tenant_id: str = "") -> dict[str, Any]:
        return await track_benefits(self, improvement_id, tenant_id)

    async def _benchmark_performance(
        self, process_id: str, benchmark_criteria: dict[str, Any]
    ) -> dict[str, Any]:
        return await benchmark_performance(self, process_id, benchmark_criteria)

    async def _share_best_practices(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await share_best_practices(self, filters)

    async def _get_process_insights(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await get_process_insights(self, tenant_id, process_id)

    async def _get_process_model(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await get_process_model(self, tenant_id, process_id)

    async def _get_conformance_report(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await get_conformance_report(self, tenant_id, process_id)

    async def _get_recommendations(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        return await get_recommendations(self, tenant_id, process_id)

    async def _get_improvement_backlog(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await get_improvement_backlog(self, filters)

    async def _get_kpi_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await get_kpi_report(self, filters)

    async def _ingest_analytics_report(
        self, tenant_id: str, analytics_report: dict[str, Any]
    ) -> dict[str, Any]:
        return await ingest_analytics_report(self, tenant_id, analytics_report)

    async def _complete_improvement(
        self, tenant_id: str, improvement_id: str, outcome: str, completed_by: str | None
    ) -> dict[str, Any]:
        return await complete_improvement(self, tenant_id, improvement_id, outcome, completed_by)

    async def _get_improvement_history(self, tenant_id: str) -> dict[str, Any]:
        return await get_improvement_history(self, tenant_id)

    async def _calculate_compliance_rate(
        self,
        deviations: list[dict[str, Any]],
        total_expected_activities: int | None = None,
        total_cases: int | None = None,
    ) -> float:
        return await calculate_compliance_rate(deviations, total_expected_activities, total_cases)

    async def _get_designed_process_model(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        from ci_actions.conformance import _get_designed_process_model

        return await _get_designed_process_model(self, tenant_id, process_id)

    # ------------------------------------------------------------------
    # Event bus integration
    # ------------------------------------------------------------------

    def _register_integrations(self) -> None:
        self.integration_status = {
            "event_hubs": bool(self.integration_clients.get("event_hubs")),
            "data_lake": bool(self.integration_clients.get("data_lake")),
            "databricks": bool(self.integration_clients.get("databricks")),
            "synapse": bool(self.integration_clients.get("synapse")),
            "ml": bool(self.integration_clients.get("ml")),
            "data_factory": bool(self.integration_clients.get("data_factory")),
            "power_bi": bool(self.integration_clients.get("power_bi")),
            "backlog_store": bool(self.integration_clients.get("backlog_store")),
            "task_sync": bool(self.integration_clients.get("task_sync")),
            "service_bus": bool(self.integration_clients.get("service_bus")),
            "cognitive_services": bool(self.integration_clients.get("cognitive_services")),
        }

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            await self.event_bus.publish(topic, payload)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Continuous Improvement & Process Mining Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "process_discovery",
            "process_visualization",
            "process_conformance",
            "bottleneck_detection",
            "deviation_detection",
            "root_cause_analysis",
            "improvement_management",
            "benefit_tracking",
            "benchmarking",
            "best_practice_sharing",
            "process_optimization",
            "event_log_analysis",
            "performance_metrics",
            "continuous_improvement",
        ]

    async def _subscribe_to_event_bus(self) -> None:
        if not self.event_bus or not hasattr(self.event_bus, "subscribe"):
            return
        for topic in self.event_topics:
            self.event_bus.subscribe(topic, self._handle_event_bus_event)
        if hasattr(self.event_bus, "start"):
            await self.event_bus.start()

    async def _handle_event_bus_event(self, payload: dict[str, Any]) -> None:
        event, tenant_id = await self._convert_bus_payload(payload)
        if not event:
            return
        await ingest_event_log(self, tenant_id, [event])

    async def _convert_bus_payload(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        event_type = payload.get("event_type") or payload.get("type") or payload.get("activity")
        data = payload.get("data", {})
        tenant_id = payload.get("tenant_id") or data.get("tenant_id") or "default"
        if not event_type and isinstance(payload.get("event"), str):
            event_type = payload.get("event")
        event = {
            "timestamp": payload.get("timestamp")
            or payload.get("time")
            or data.get("timestamp")
            or datetime.now(timezone.utc).isoformat(),
            "activity": event_type or "unknown",
            "process_id": payload.get("process_id")
            or data.get("process_id")
            or data.get("workflow_id")
            or "unknown",
            "case_id": payload.get("case_id")
            or data.get("case_id")
            or data.get("request_id")
            or data.get("task_id")
            or "unknown",
            "metadata": data,
        }
        return event, tenant_id
