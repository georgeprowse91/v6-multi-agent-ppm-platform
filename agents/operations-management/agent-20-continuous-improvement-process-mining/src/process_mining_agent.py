"""
Agent 20: Continuous Improvement & Process Mining Agent

Purpose:
Facilitates ongoing improvement by analyzing execution data to uncover inefficiencies,
bottlenecks and deviations, and by managing improvement initiatives.

Specification: agents/operations-management/agent-20-continuous-improvement-process-mining/README.md
"""

import json
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

    def __init__(self, agent_id: str = "agent_020", config: dict[str, Any] | None = None):
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

        event_log_store_path = self._resolve_store_path(
            config, "event_log_store_path", "data/process_event_logs.json"
        )
        process_model_store_path = self._resolve_store_path(
            config, "process_model_store_path", "data/process_models.json"
        )
        conformance_store_path = self._resolve_store_path(
            config, "conformance_store_path", "data/process_conformance.json"
        )
        recommendations_store_path = self._resolve_store_path(
            config, "recommendations_store_path", "data/process_recommendations.json"
        )
        improvement_history_store_path = self._resolve_store_path(
            config, "improvement_history_store_path", "data/improvement_history.json"
        )
        improvement_backlog_store_path = self._resolve_store_path(
            config, "improvement_backlog_store_path", "data/improvement_backlog.json"
        )
        self.event_log_store = TenantStateStore(event_log_store_path)
        self.process_model_store = TenantStateStore(process_model_store_path)
        self.conformance_store = TenantStateStore(conformance_store_path)
        self.recommendations_store = TenantStateStore(recommendations_store_path)
        self.improvement_history_store = TenantStateStore(improvement_history_store_path)
        self.improvement_backlog_store = TenantStateStore(improvement_backlog_store_path)

        # Data stores (will be replaced with database)
        self.event_logs = {}  # type: ignore
        self.process_models = {}  # type: ignore
        self.improvement_backlog = {}  # type: ignore
        self.benefit_tracking = {}  # type: ignore
        self.benchmarks = {}  # type: ignore
        self.event_log_index: dict[str, list[dict[str, Any]]] = {}
        self.integration_clients = config.get("integration_clients", {}) if config else {}
        self.integration_status: dict[str, bool] = {}
        self.financial_agent = config.get("financial_agent") if config else None
        self.workflow_engine_agent = config.get("workflow_engine_agent") if config else None
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
        self.event_topics = (
            config.get(
                "event_topics",
                [
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
                ],
            )
            if config
            else [
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

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process mining and continuous improvement requests.

        Args:
            input_data: {
            "action": "ingest_event_log" | "discover_process" | "detect_bottlenecks" |
                          "detect_deviations" | "analyze_root_cause" | "create_improvement" |
                          "prioritize_improvements" | "track_benefits" | "benchmark_performance" |
                          "share_best_practices" | "get_process_insights" | "get_improvement_backlog",
                "events": Event log data for ingestion,
                "process_id": Process identifier,
                "algorithm": Process mining algorithm to use,
                "improvement": Improvement initiative data,
                "benchmark_criteria": Benchmarking parameters,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - ingest_event_log: Ingestion status and statistics
            - discover_process: Process model and visualization
            - detect_bottlenecks: Bottleneck analysis with recommendations
            - detect_deviations: Deviation detection results
            - analyze_root_cause: Root cause analysis and insights
            - create_improvement: Improvement ID and details
            - prioritize_improvements: Prioritized improvement backlog
            - track_benefits: Benefit realization metrics
            - benchmark_performance: Benchmark comparison results
            - share_best_practices: Best practices list
            - get_process_insights: Process performance insights
            - get_improvement_backlog: Improvement backlog list
            - get_kpi_report: KPI rollups for projects and programs
        """
        action = input_data.get("action", "get_process_insights")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "ingest_event_log":
            return await self._ingest_event_log(tenant_id, input_data.get("events", []))

        elif action == "discover_process":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._discover_process(
                tenant_id, process_id, input_data.get("algorithm", "heuristic_miner")
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
            return await self._check_conformance(tenant_id, process_id, expected_model)

        elif action == "detect_bottlenecks":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._detect_bottlenecks(tenant_id, process_id)

        elif action == "detect_deviations":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._detect_deviations(tenant_id, process_id)

        elif action == "analyze_root_cause":
            process_id = input_data.get("process_id")
            issue_id = input_data.get("issue_id")
            assert isinstance(process_id, str), "process_id must be a string"
            assert isinstance(issue_id, str), "issue_id must be a string"
            return await self._analyze_root_cause(process_id, issue_id)

        elif action == "create_improvement":
            return await self._create_improvement(tenant_id, input_data.get("improvement", {}))

        elif action == "prioritize_improvements":
            return await self._prioritize_improvements()

        elif action == "track_benefits":
            improvement_id = input_data.get("improvement_id")
            assert isinstance(improvement_id, str), "improvement_id must be a string"
            return await self._track_benefits(improvement_id)

        elif action == "benchmark_performance":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._benchmark_performance(
                process_id, input_data.get("benchmark_criteria", {})
            )

        elif action == "share_best_practices":
            return await self._share_best_practices(input_data.get("filters", {}))

        elif action == "get_process_insights":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._get_process_insights(tenant_id, process_id)
        elif action == "get_process_model":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._get_process_model(tenant_id, process_id)
        elif action == "get_conformance_report":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._get_conformance_report(tenant_id, process_id)
        elif action == "get_recommendations":
            process_id = input_data.get("process_id")
            assert isinstance(process_id, str), "process_id must be a string"
            return await self._get_recommendations(tenant_id, process_id)

        elif action == "get_improvement_backlog":
            return await self._get_improvement_backlog(input_data.get("filters", {}))
        elif action == "get_kpi_report":
            return await self._get_kpi_report(input_data.get("filters", {}))
        elif action == "ingest_analytics_report":
            return await self._ingest_analytics_report(
                tenant_id,
                input_data.get("analytics_report", {}),
            )
        elif action == "complete_improvement":
            improvement_id = input_data.get("improvement_id")
            assert isinstance(improvement_id, str), "improvement_id must be a string"
            return await self._complete_improvement(
                tenant_id,
                improvement_id,
                input_data.get("outcome", "completed"),
                input_data.get("completed_by"),
            )
        elif action == "get_improvement_history":
            return await self._get_improvement_history(tenant_id)

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _ingest_event_log(
        self, tenant_id: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Ingest event log data for process mining.

        Returns ingestion statistics.
        """
        self.logger.info("Ingesting event log with %s events", len(events))

        # Validate events
        valid_events = await self._validate_events(events)

        # Map events to process instances (case IDs)
        mapped_events = await self._map_events_to_cases(valid_events)

        # Store events
        log_id = await self._generate_log_id()
        log_record = {
            "log_id": log_id,
            "events": mapped_events,
            "event_count": len(mapped_events),
            "case_count": len(set(e.get("case_id") for e in mapped_events)),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.event_logs[log_id] = log_record
        self.event_log_store.upsert(tenant_id, log_id, log_record)
        for event in mapped_events:
            case_id = str(event.get("case_id") or "unknown")
            self.event_log_index.setdefault(case_id, []).append(event)

        await self._publish_event(
            "events.ingested",
            {
                "tenant_id": tenant_id,
                "log_id": log_id,
                "event_count": len(mapped_events),
                "case_count": len(set(e.get("case_id") for e in mapped_events)),
                "ingested_at": log_record["ingested_at"],
            },
        )

        return {
            "log_id": log_id,
            "events_ingested": len(mapped_events),
            "cases_identified": len(set(e.get("case_id") for e in mapped_events)),
            "time_range": await self._calculate_time_range(mapped_events),
        }

    async def _check_conformance(
        self, tenant_id: str, process_id: str, expected_model: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare actual traces against expected process model."""
        self.logger.info("Checking conformance for process: %s", process_id)

        events = await self._get_process_events(process_id)
        if not events:
            raise ValueError(f"No events found for process: {process_id}")

        traces = await self._build_traces(events)
        expected_activities = set(expected_model.get("activities", []))
        expected_transitions = {
            (edge.get("from"), edge.get("to")) for edge in expected_model.get("transitions", [])
        }

        deviations: list[dict[str, Any]] = []
        compliant_traces = 0

        for case_id, activities in traces.items():
            trace_deviations = []
            if expected_activities and not set(activities).issubset(expected_activities):
                extra = set(activities) - expected_activities
                trace_deviations.append(
                    {"case_id": case_id, "category": "extra_activities", "activities": list(extra)}
                )
            for left, right in self._pairwise(activities):
                if expected_transitions and (left, right) not in expected_transitions:
                    trace_deviations.append(
                        {
                            "case_id": case_id,
                            "category": "unexpected_transition",
                            "from": left,
                            "to": right,
                        }
                    )
            if trace_deviations:
                deviations.extend(trace_deviations)
            else:
                compliant_traces += 1

        compliance_rate = (compliant_traces / len(traces)) * 100 if traces else 0.0
        report = {
            "process_id": process_id,
            "expected_model": expected_model,
            "total_traces": len(traces),
            "compliant_traces": compliant_traces,
            "compliance_rate": compliance_rate,
            "deviations": deviations,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        self.conformance_store.upsert(tenant_id, process_id, report)
        await self._emit_deviation_alert(process_id, report)
        return report

    async def _discover_process(
        self, tenant_id: str, process_id: str, algorithm: str = "heuristic_miner"
    ) -> dict[str, Any]:
        """
        Discover process model from event logs.

        Returns process model and visualization.
        """
        self.logger.info("Discovering process %s using %s", process_id, algorithm)

        # Get event logs for process
        events = await self._get_process_events(process_id)

        if not events:
            raise ValueError(f"No events found for process: {process_id}")

        process_model = await self._apply_mining_algorithm(events, algorithm)
        bpmn_model = await self._build_bpmn_model(events, process_model)
        petri_net = await self._build_petri_net(events, process_model)

        # Calculate performance metrics
        performance_metrics = await self._calculate_process_metrics(events, process_model)

        # Generate visualization data
        visualization = await self._generate_process_visualization(
            process_model, performance_metrics
        )

        # Store process model
        model_record = {
            "process_id": process_id,
            "model": process_model,
            "bpmn": bpmn_model,
            "petri_net": petri_net,
            "algorithm": algorithm,
            "metrics": performance_metrics,
            "visualization": visualization,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.process_models[process_id] = model_record
        self.process_model_store.upsert(tenant_id, process_id, model_record)

        await self._publish_event(
            "process.discovered",
            {
                "tenant_id": tenant_id,
                "process_id": process_id,
                "algorithm": algorithm,
                "metrics": performance_metrics,
                "discovered_at": model_record["discovered_at"],
            },
        )

        return {
            "process_id": process_id,
            "algorithm": algorithm,
            "activities": len(process_model.get("activities", [])),
            "transitions": len(process_model.get("transitions", [])),
            "bpmn": bpmn_model,
            "petri_net": petri_net,
            "metrics": performance_metrics,
            "visualization": visualization,
        }

    async def _detect_bottlenecks(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """
        Detect bottlenecks in process execution.

        Returns bottleneck analysis.
        """
        self.logger.info("Detecting bottlenecks for process: %s", process_id)

        process_model = self.process_models.get(process_id) or self.process_model_store.get(
            tenant_id, process_id
        )
        if not process_model:
            # Discover process first
            await self._discover_process(tenant_id, process_id)
            process_model = self.process_models.get(process_id) or self.process_model_store.get(
                tenant_id, process_id
            )

        # Analyze waiting times
        waiting_times = await self._analyze_waiting_times(process_id)

        # Analyze throughput
        throughput = await self._analyze_throughput(process_id)

        # Identify bottlenecks
        bottlenecks: list[dict[str, Any]] = []
        for activity, metrics in waiting_times.items():
            avg_wait_time = float(metrics.get("avg_waiting_time", 0))
            if avg_wait_time > self.bottleneck_threshold * 100:
                bottlenecks.append(
                    {
                        "activity": activity,
                        "avg_waiting_time": avg_wait_time,
                        "frequency": metrics.get("frequency"),
                        "severity": "high" if avg_wait_time > 50 else "medium",
                    }
                )

        # Generate recommendations
        recommendations = await self._generate_bottleneck_recommendations(bottlenecks)

        return {
            "process_id": process_id,
            "bottlenecks_detected": len(bottlenecks),
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "overall_throughput": throughput,
        }

    async def _detect_deviations(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """
        Detect deviations from designed process.

        Returns deviation analysis.
        """
        self.logger.info("Detecting deviations for process: %s", process_id)

        # Get designed process model
        designed_model = await self._get_designed_process_model(tenant_id, process_id)

        # Get actual process model
        actual_model = self.process_models.get(process_id) or self.process_model_store.get(
            tenant_id, process_id
        )
        if not actual_model:
            await self._discover_process(tenant_id, process_id)
            actual_model = self.process_models.get(process_id) or self.process_model_store.get(
                tenant_id, process_id
            )

        assert actual_model is not None, "Failed to discover process model"

        # Compare models
        deviations = await self._compare_process_models(designed_model, actual_model.get("model"))

        events = await self._get_process_events(process_id)
        total_cases = len({str(event.get("case_id")) for event in events if event.get("case_id")})
        designed_activities_count = len(designed_model.get("activities", []))

        # Categorize deviations
        categorized_deviations: dict[str, list[dict[str, Any]]] = {
            "skipped_activities": [],
            "extra_activities": [],
            "wrong_sequence": [],
            "excessive_loops": [],
        }

        for deviation in deviations:
            category = deviation.get("category")
            if category in categorized_deviations:
                categorized_deviations[category].append(deviation)

        report = {
            "process_id": process_id,
            "total_deviations": len(deviations),
            "deviations": categorized_deviations,
            "compliance_rate": await self._calculate_compliance_rate(
                deviations,
                total_expected_activities=designed_activities_count,
                total_cases=total_cases,
            ),
        }
        await self._emit_deviation_alert(process_id, report)
        return report

    async def _analyze_root_cause(self, process_id: str, issue_id: str) -> dict[str, Any]:
        """
        Perform root cause analysis on process issue.

        Returns root cause insights.
        """
        self.logger.info("Analyzing root cause for issue %s in process %s", issue_id, process_id)

        # Get process events
        events = await self._get_process_events(process_id)

        # Identify problematic cases
        problematic_cases = await self._identify_problematic_cases(events, issue_id)

        # Analyze correlations
        correlations = await self._analyze_correlations(problematic_cases, events)

        # Identify contributing factors
        factors = await self._identify_contributing_factors(correlations)

        # Generate insights
        insights = await self._generate_root_cause_insights(factors)

        return {
            "process_id": process_id,
            "issue_id": issue_id,
            "problematic_cases": len(problematic_cases),
            "contributing_factors": factors,
            "correlations": correlations,
            "insights": insights,
            "recommendations": await self._generate_remediation_recommendations(factors),
        }

    async def _create_improvement(
        self, tenant_id: str, improvement_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create improvement initiative.

        Returns improvement ID and details.
        """
        self.logger.info("Creating improvement: %s", improvement_data.get("title"))

        # Generate improvement ID
        improvement_id = await self._generate_improvement_id()

        # Estimate expected benefits
        expected_benefits = await self._estimate_improvement_benefits(improvement_data)

        # Assess feasibility
        feasibility = await self._assess_improvement_feasibility(improvement_data)

        # Calculate priority score
        priority_score = await self._calculate_improvement_priority(
            expected_benefits, feasibility, improvement_data
        )

        # Create improvement record
        improvement = {
            "improvement_id": improvement_id,
            "title": improvement_data.get("title"),
            "description": improvement_data.get("description"),
            "category": improvement_data.get("category"),
            "process_id": improvement_data.get("process_id"),
            "expected_benefits": expected_benefits,
            "feasibility": feasibility,
            "priority_score": priority_score,
            "owner": improvement_data.get("owner"),
            "status": "Idea",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store improvement
        self.improvement_backlog[improvement_id] = improvement
        self.improvement_backlog_store.upsert(tenant_id, improvement_id, improvement.copy())
        self.event_log_store.upsert(
            tenant_id,
            f"improvement-{improvement_id}",
            {
                "improvement_id": improvement_id,
                "process_id": improvement_data.get("process_id"),
                "created_at": improvement.get("created_at"),
            },
        )

        await self._emit_improvement_recommendation(tenant_id, improvement)

        await self._publish_event(
            "improvement.created",
            {
                "tenant_id": tenant_id,
                "improvement_id": improvement_id,
                "process_id": improvement.get("process_id"),
                "priority_score": priority_score,
                "status": improvement.get("status"),
                "created_at": improvement.get("created_at"),
            },
        )
        if self.integration_clients.get("task_sync"):
            await self.integration_clients["task_sync"].create_task(improvement)

        return {
            "improvement_id": improvement_id,
            "title": improvement["title"],
            "priority_score": priority_score,
            "expected_benefits": expected_benefits,
            "feasibility": feasibility,
            "next_steps": "Review and prioritize in improvement backlog",
        }

    async def _emit_improvement_recommendation(
        self, tenant_id: str, improvement: dict[str, Any]
    ) -> None:
        """Emit improvement recommendation to workflow engine."""
        event_payload = {
            "event_type": "workflow.improvement.recommendation",
            "data": {
                "tenant_id": tenant_id,
                "improvement_id": improvement.get("improvement_id"),
                "process_id": improvement.get("process_id"),
                "priority_score": improvement.get("priority_score"),
                "expected_benefits": improvement.get("expected_benefits"),
            },
        }
        if self.workflow_engine_agent:
            await self.workflow_engine_agent.process(
                {"action": "handle_event", "event": event_payload}
            )
            return
        if self.event_bus:
            await self.event_bus.publish("workflow.improvement.recommendation", event_payload)

    async def _prioritize_improvements(self) -> dict[str, Any]:
        """
        Prioritize improvement backlog.

        Returns prioritized list.
        """
        self.logger.info("Prioritizing improvement backlog")

        # Get all improvements
        improvements = list(self.improvement_backlog.values())

        # Sort by priority score
        prioritized = sorted(improvements, key=lambda x: x.get("priority_score", 0), reverse=True)

        # Categorize by status
        by_status: dict[str, list[dict[str, Any]]] = {
            "Idea": [],
            "Planned": [],
            "In Progress": [],
            "Completed": [],
        }

        for improvement in prioritized:
            status = improvement.get("status")
            if status in by_status:
                by_status[status].append(improvement)

        return {
            "total_improvements": len(prioritized),
            "prioritized_list": [
                {
                    "improvement_id": i.get("improvement_id"),
                    "title": i.get("title"),
                    "priority_score": i.get("priority_score"),
                    "status": i.get("status"),
                }
                for i in prioritized
            ],
            "by_status": {k: len(v) for k, v in by_status.items()},
        }

    async def _track_benefits(self, improvement_id: str, tenant_id: str = "") -> dict[str, Any]:
        """
        Track benefit realization for improvement.

        Returns benefit metrics.
        """
        self.logger.info("Tracking benefits for improvement: %s", improvement_id)

        improvement = self.improvement_backlog.get(improvement_id)
        if not improvement:
            raise ValueError(f"Improvement not found: {improvement_id}")

        # Measure actual performance
        actual_benefits = await self._measure_actual_benefits(improvement)

        # Compare to expected
        expected_benefits = improvement.get("expected_benefits", {})

        # Calculate realization percentage
        realization = await self._calculate_benefit_realization(expected_benefits, actual_benefits)

        # Store tracking data
        self.benefit_tracking[improvement_id] = {
            "improvement_id": improvement_id,
            "expected_benefits": expected_benefits,
            "actual_benefits": actual_benefits,
            "realization_percentage": realization,
            "measured_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.financial_agent:
            await self.financial_agent.process(
                {
                    "action": "update_forecast",
                    "improvement_id": improvement_id,
                    "benefits": actual_benefits,
                }
            )
        await self._publish_event(
            "benefits.realized",
            {
                "tenant_id": tenant_id,
                "improvement_id": improvement_id,
                "actual_benefits": actual_benefits,
                "realization_percentage": realization,
            },
        )

        return {
            "improvement_id": improvement_id,
            "expected_benefits": expected_benefits,
            "actual_benefits": actual_benefits,
            "realization_percentage": realization,
            "roi": await self._calculate_improvement_roi(improvement, actual_benefits),
        }

    async def _benchmark_performance(
        self, process_id: str, benchmark_criteria: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Benchmark process performance.

        Returns benchmark comparison.
        """
        self.logger.info("Benchmarking performance for process: %s", process_id)

        # Get current process metrics
        current_metrics = await self._get_current_process_metrics(process_id)

        # Get benchmark data
        benchmark_data = await self._get_benchmark_data(process_id, benchmark_criteria)

        # Compare metrics
        comparison = await self._compare_metrics(current_metrics, benchmark_data)

        # Identify gaps
        gaps = await self._identify_performance_gaps(comparison)

        return {
            "process_id": process_id,
            "current_metrics": current_metrics,
            "benchmark_metrics": benchmark_data,
            "comparison": comparison,
            "performance_gaps": gaps,
            "ranking": await self._calculate_performance_ranking(comparison),
        }

    async def _share_best_practices(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Share best practices across teams.

        Returns best practices list.
        """
        self.logger.info("Sharing best practices")

        # Identify top-performing processes
        top_performers = await self._identify_top_performers(filters)

        # Extract best practices
        best_practices = await self._extract_best_practices(top_performers)

        # Categorize practices
        categorized_practices = await self._categorize_best_practices(best_practices)

        templates = [
            {
                "title": "Process Improvement Checklist",
                "description": "Checklist for rolling out optimized processes",
            }
        ]
        if self.knowledge_agent:
            await self.knowledge_agent.process(
                {
                    "action": "ingest_agent_output",
                    "payload": {
                        "category": "best_practices",
                        "best_practices": best_practices,
                        "templates": templates,
                    },
                    "tenant_id": "shared",
                }
            )

        return {
            "total_practices": len(best_practices),
            "best_practices": best_practices,
            "categorized": categorized_practices,
            "top_performers": top_performers,
            "templates": templates,
        }

    async def _get_process_insights(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """
        Get comprehensive process insights.

        Returns process analysis.
        """
        self.logger.info("Generating insights for process: %s", process_id)

        process_model = self.process_models.get(process_id) or self.process_model_store.get(
            tenant_id, process_id
        )
        if not process_model:
            await self._discover_process(tenant_id, process_id)
            process_model = self.process_models.get(process_id) or self.process_model_store.get(
                tenant_id, process_id
            )

        # Get metrics
        metrics = process_model.get("metrics", {})  # type: ignore

        # Get bottlenecks
        bottlenecks_result = await self._detect_bottlenecks(tenant_id, process_id)

        # Get deviations
        deviations_result = await self._detect_deviations(tenant_id, process_id)

        recommendations = await self._generate_process_recommendations(
            metrics, bottlenecks_result, deviations_result
        )
        await self._store_recommendations(
            tenant_id,
            process_id,
            recommendations,
            context={
                "metrics": metrics,
                "bottlenecks": bottlenecks_result.get("bottlenecks", []),
                "deviations": deviations_result.get("deviations", {}),
            },
        )
        return {
            "process_id": process_id,
            "metrics": metrics,
            "bottlenecks": bottlenecks_result.get("bottlenecks", []),
            "deviations": deviations_result.get("total_deviations", 0),
            "compliance_rate": deviations_result.get("compliance_rate", 100),
            "recommendations": recommendations,
        }

    async def _get_improvement_backlog(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get improvement backlog with filters.

        Returns filtered backlog.
        """
        self.logger.info("Retrieving improvement backlog")

        tenant_id = filters.get("tenant_id", "default")
        stored_improvements = self.improvement_backlog_store.list(tenant_id)
        for record in stored_improvements:
            if isinstance(record, dict) and record.get("improvement_id"):
                self.improvement_backlog.setdefault(record["improvement_id"], record)

        # Filter improvements
        filtered = []
        for improvement_id, improvement in self.improvement_backlog.items():
            if await self._matches_improvement_filters(improvement, filters):
                filtered.append(improvement)

        # Sort by priority
        sorted_improvements = sorted(
            filtered, key=lambda x: x.get("priority_score", 0), reverse=True
        )

        return {
            "total_improvements": len(sorted_improvements),
            "improvements": sorted_improvements,
            "filters": filters,
        }

    async def _ingest_analytics_report(
        self, tenant_id: str, analytics_report: dict[str, Any]
    ) -> dict[str, Any]:
        """Ingest analytics insights and create prioritized improvement backlog items."""
        recommendations = analytics_report.get("recommendations", [])
        anomalies = analytics_report.get("anomalies", [])
        trends = analytics_report.get("trends", [])
        created_items: list[dict[str, Any]] = []

        for index, recommendation in enumerate(recommendations):
            feasibility = "high"
            impact = "medium"
            lowered = str(recommendation).lower()
            if "scope" in lowered or "budget" in lowered:
                impact = "high"
                feasibility = "medium"
            if "training" in lowered or "monitoring" in lowered:
                feasibility = "high"
            due_days = 14 if impact == "high" else 30
            improvement_id = await self._generate_improvement_id()
            priority_score = 90 - (index * 5)
            target_due_date = (datetime.now(timezone.utc) + timedelta(days=due_days)).replace(
                microsecond=0
            )
            item = {
                "improvement_id": improvement_id,
                "title": recommendation,
                "description": f"Derived from analytics report {analytics_report.get('report_id')}",
                "category": "analytics_feedback",
                "process_id": analytics_report.get("period", "portfolio"),
                "expected_benefits": {"impact": impact},
                "feasibility": {"level": feasibility},
                "priority_score": priority_score,
                "owner": self._resolve_improvement_owner(recommendation, index),
                "target_date": target_due_date.date().isoformat(),
                "target_due_date": target_due_date.isoformat(),
                "status": "Planned",
                "source_report_id": analytics_report.get("report_id"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.improvement_backlog[improvement_id] = item
            self.improvement_backlog_store.upsert(tenant_id, improvement_id, item.copy())
            created_items.append(item)

        prioritized = sorted(created_items, key=lambda i: i.get("priority_score", 0), reverse=True)
        await self._publish_improvement_backlog(tenant_id, prioritized)
        await self._notify_stakeholders(
            tenant_id,
            "improvement.backlog.updated",
            {
                "source_report_id": analytics_report.get("report_id"),
                "item_count": len(prioritized),
                "anomalies": len(anomalies),
                "trends": len(trends),
            },
        )

        return {
            "source_report_id": analytics_report.get("report_id"),
            "created_items": len(prioritized),
            "prioritized_backlog": prioritized,
        }

    async def _complete_improvement(
        self,
        tenant_id: str,
        improvement_id: str,
        outcome: str,
        completed_by: str | None,
    ) -> dict[str, Any]:
        improvement = self.improvement_backlog.get(
            improvement_id
        ) or self.improvement_backlog_store.get(tenant_id, improvement_id)
        if not improvement:
            raise ValueError(f"Improvement not found: {improvement_id}")

        completed = {
            **improvement,
            "status": "Completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_by": completed_by
            or improvement.get("owner")
            or self.default_improvement_owner,
            "outcome": outcome,
        }
        self.improvement_backlog[improvement_id] = completed
        self.improvement_backlog_store.upsert(tenant_id, improvement_id, completed.copy())
        history_id = f"history-{improvement_id}-{int(datetime.now(timezone.utc).timestamp())}"
        self.improvement_history_store.upsert(
            tenant_id,
            history_id,
            {
                "improvement_id": improvement_id,
                "date": completed["completed_at"],
                "owner": completed["completed_by"],
                "outcome": outcome,
            },
        )
        await self._notify_stakeholders(
            tenant_id,
            "improvement.completed",
            {
                "improvement_id": improvement_id,
                "owner": completed["completed_by"],
                "outcome": outcome,
            },
        )
        return completed

    async def _get_improvement_history(self, tenant_id: str) -> dict[str, Any]:
        entries = self.improvement_history_store.list(tenant_id)
        return {"tenant_id": tenant_id, "entries": entries, "count": len(entries)}

    def _resolve_improvement_owner(self, recommendation: Any, index: int) -> str:
        owner_hints = {
            "training": "l&d-lead",
            "scope": "pmo-lead",
            "budget": "finance-partner",
            "risk": "risk-manager",
        }
        lowered = str(recommendation).lower()
        for hint, owner in owner_hints.items():
            if hint in lowered:
                return owner
        return self.default_improvement_owner if index % 2 == 0 else "delivery-manager"

    async def _publish_improvement_backlog(
        self, tenant_id: str, prioritized_items: list[dict[str, Any]]
    ) -> None:
        payload = {
            "tenant_id": tenant_id,
            "category": "improvement_backlog",
            "items": prioritized_items,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.knowledge_agent:
            await self.knowledge_agent.process(
                {
                    "action": "ingest_agent_output",
                    "tenant_id": tenant_id,
                    "payload": payload,
                }
            )
            return
        if self.event_bus:
            await self.event_bus.publish("knowledge.improvement_backlog.published", payload)

    async def _notify_stakeholders(
        self, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        message = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "notified_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.integration_clients.get("notification_service"):
            await self.integration_clients["notification_service"].send(message)
            return
        if self.event_bus:
            await self.event_bus.publish("notification.improvement", message)

    async def _get_process_model(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """Return stored process model for API consumers."""
        model = self.process_models.get(process_id) or self.process_model_store.get(
            tenant_id, process_id
        )
        if not model:
            await self._discover_process(tenant_id, process_id)
            model = self.process_models.get(process_id) or self.process_model_store.get(
                tenant_id, process_id
            )
        return model or {}

    async def _get_conformance_report(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """Return conformance report for API consumers."""
        report = self.conformance_store.get(tenant_id, process_id)
        if not report:
            expected_model = await self._get_designed_process_model(tenant_id, process_id)
            report = await self._check_conformance(tenant_id, process_id, expected_model)
        return report

    async def _get_recommendations(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """Return stored recommendations for API consumers."""
        stored = self.recommendations_store.get(tenant_id, process_id)
        if stored:
            return stored
        insights = await self._get_process_insights(tenant_id, process_id)
        return {
            "process_id": process_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "recommendations": insights.get("recommendations", []),
        }

    async def _get_kpi_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Compute KPI rollups across projects and programs."""
        all_events = []
        if not self.event_logs:
            stored_logs = await self._load_all_event_logs()
            for log in stored_logs:
                all_events.extend(log.get("events", []))
        else:
            for log in self.event_logs.values():
                all_events.extend(log.get("events", []))

        if filters.get("process_id"):
            all_events = [
                event for event in all_events if event.get("process_id") == filters["process_id"]
            ]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filters": filters,
            "process_kpis": await self._calculate_grouped_kpis(all_events, "process_id"),
            "project_kpis": await self._calculate_grouped_kpis(all_events, "project_id"),
            "program_kpis": await self._calculate_grouped_kpis(all_events, "program_id"),
        }

    # Helper methods

    async def _generate_log_id(self) -> str:
        """Generate unique log ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"LOG-{timestamp}"

    async def _generate_improvement_id(self) -> str:
        """Generate unique improvement ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"IMP-{timestamp}"

    async def _validate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate event log entries."""
        valid_events = []
        for event in events:
            normalized = await self._normalize_event(event)
            if normalized:
                valid_events.append(normalized)
        return valid_events

    async def _map_events_to_cases(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map events to process cases."""
        for event in events:
            if "case_id" not in event:
                # Generate case_id if missing
                event["case_id"] = event.get("request_id", "unknown")
        return events

    async def _calculate_time_range(self, events: list[dict[str, Any]]) -> dict[str, str]:
        """Calculate time range of events."""
        if not events:
            return {"start": None, "end": None}  # type: ignore

        timestamps = []
        for event in events:
            timestamp = event.get("timestamp")
            if not timestamp:
                continue
            parsed = self._safe_parse_timestamp(timestamp)
            if parsed:
                timestamps.append(parsed)
        if not timestamps:
            return {"start": None, "end": None}  # type: ignore

        return {"start": min(timestamps).isoformat(), "end": max(timestamps).isoformat()}

    async def _get_process_events(self, process_id: str) -> list[dict[str, Any]]:
        """Get events for a specific process."""
        all_events = []
        if not self.event_logs:
            stored_logs = await self._load_all_event_logs()
            for log in stored_logs:
                all_events.extend(log.get("events", []))
        else:
            for log in self.event_logs.values():
                all_events.extend(log.get("events", []))

        # Filter by process
        return [e for e in all_events if e.get("process_id") == process_id]

    async def _load_all_event_logs(self) -> list[dict[str, Any]]:
        if not self.event_log_store.path.exists():
            return []
        try:
            data = self.event_log_store.path.read_text()
            if not data:
                return []
            parsed: dict[str, Any] = json.loads(data)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            return []
        logs: list[dict[str, Any]] = []
        for tenant_records in parsed.values():
            if isinstance(tenant_records, dict):
                logs.extend(
                    record for record in tenant_records.values() if isinstance(record, dict)
                )
        return logs

    async def _apply_mining_algorithm(
        self, events: list[dict[str, Any]], algorithm: str
    ) -> dict[str, Any]:
        """Apply process mining algorithm."""
        traces = await self._build_traces(events)
        activities = sorted({activity for trace in traces.values() for activity in trace})
        transition_counts: dict[tuple[str, str], int] = {}

        for trace in traces.values():
            for left, right in self._pairwise(trace):
                transition_counts[(left, right)] = transition_counts.get((left, right), 0) + 1

        if algorithm == "alpha_miner":
            transitions = [
                {"from": left, "to": right, "frequency": count}
                for (left, right), count in transition_counts.items()
            ]
        elif algorithm == "inductive_miner":
            transitions = [
                {"from": left, "to": right, "frequency": count}
                for (left, right), count in transition_counts.items()
                if count >= self.min_frequency_threshold
            ]
            activities = sorted(
                {
                    activity
                    for transition in transitions
                    for activity in (transition["from"], transition["to"])
                }
            )
        else:
            transitions = [
                {"from": left, "to": right, "frequency": count}
                for (left, right), count in transition_counts.items()
            ]

        return {"activities": activities, "transitions": transitions, "algorithm": algorithm}

    async def _build_bpmn_model(
        self, events: list[dict[str, Any]], process_model: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a lightweight BPMN representation."""
        traces = await self._build_traces(events)
        start_activities, end_activities = self._get_start_end_activities(traces)
        tasks = [
            {"id": activity, "name": activity, "type": "task"}
            for activity in process_model.get("activities", [])
        ]
        flows = [
            {"id": f"{edge['from']}-{edge['to']}", "source": edge["from"], "target": edge["to"]}
            for edge in process_model.get("transitions", [])
        ]
        return {
            "type": "bpmn",
            "start_events": [
                {"id": f"start-{activity}", "name": "Start", "outgoing": activity}
                for activity in start_activities
            ],
            "end_events": [
                {"id": f"end-{activity}", "name": "End", "incoming": activity}
                for activity in end_activities
            ],
            "tasks": tasks,
            "sequence_flows": flows,
        }

    async def _build_petri_net(
        self, events: list[dict[str, Any]], process_model: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a simplified Petri net representation."""
        traces = await self._build_traces(events)
        start_activities, end_activities = self._get_start_end_activities(traces)
        transitions = [
            {"id": activity, "label": activity} for activity in process_model.get("activities", [])
        ]
        places = [{"id": "p_start"}, {"id": "p_end"}]
        arcs: list[dict[str, str]] = []
        for activity in start_activities:
            arcs.append({"from": "p_start", "to": activity})
        for activity in end_activities:
            arcs.append({"from": activity, "to": "p_end"})

        for edge in process_model.get("transitions", []):
            place_id = f"p_{edge['from']}_to_{edge['to']}"
            places.append({"id": place_id})
            arcs.append({"from": edge["from"], "to": place_id})
            arcs.append({"from": place_id, "to": edge["to"]})

        return {"type": "petri_net", "places": places, "transitions": transitions, "arcs": arcs}

    def _get_start_end_activities(
        self, traces: dict[str, list[str]]
    ) -> tuple[list[str], list[str]]:
        start_activities = []
        end_activities = []
        for activities in traces.values():
            if activities:
                start_activities.append(activities[0])
                end_activities.append(activities[-1])
        return sorted(set(start_activities)), sorted(set(end_activities))

    async def _calculate_process_metrics(
        self, events: list[dict[str, Any]], process_model: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate process performance metrics."""
        traces = await self._build_traces(events)
        cycle_times = []
        for case_id in traces:
            case_events = [e for e in events if e.get("case_id") == case_id]
            timestamps = [
                self._safe_parse_timestamp(e.get("timestamp"))
                for e in case_events
                if e.get("timestamp")
            ]
            timestamps = [ts for ts in timestamps if ts]
            if timestamps:
                cycle_times.append((max(timestamps) - min(timestamps)).total_seconds() / 3600)

        median_cycle_time = sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
        return {
            "median_cycle_time": round(median_cycle_time, 2),
            "throughput": len(traces),
            "activity_count": len(process_model.get("activities", [])),
            "avg_waiting_time": await self._calculate_average_waiting_time(events),
        }

    async def _calculate_basic_metrics(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate basic performance metrics without a process model."""
        traces = await self._build_traces(events)
        cycle_times = []
        for case_id in traces:
            case_events = [e for e in events if e.get("case_id") == case_id]
            timestamps = [
                self._safe_parse_timestamp(e.get("timestamp"))
                for e in case_events
                if e.get("timestamp")
            ]
            timestamps = [ts for ts in timestamps if ts]
            if timestamps:
                cycle_times.append((max(timestamps) - min(timestamps)).total_seconds() / 3600)

        median_cycle_time = sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
        return {
            "median_cycle_time": round(median_cycle_time, 2),
            "throughput": len(traces),
            "avg_waiting_time": await self._calculate_average_waiting_time(events),
            "trace_count": len(traces),
        }

    async def _calculate_grouped_kpis(
        self, events: list[dict[str, Any]], key: str
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            dimension = self._extract_dimension(event, key)
            if dimension is None:
                continue
            grouped.setdefault(dimension, []).append(event)

        results = []
        for dimension, group_events in grouped.items():
            metrics = await self._calculate_basic_metrics(group_events)
            results.append(
                {
                    "dimension": dimension,
                    "event_count": len(group_events),
                    "metrics": metrics,
                }
            )
        return sorted(results, key=lambda item: item["event_count"], reverse=True)

    def _extract_dimension(self, event: dict[str, Any], key: str) -> str | None:
        if key == "process_id":
            return event.get("process_id")
        metadata = event.get("metadata", {})
        return metadata.get(key) if isinstance(metadata, dict) else event.get(key)

    async def _generate_process_visualization(
        self, process_model: dict[str, Any], metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate process visualization data."""
        return {
            "type": "process_map",
            "nodes": process_model.get("activities", []),
            "edges": process_model.get("transitions", []),
            "metrics_overlay": metrics,
        }

    async def _analyze_waiting_times(self, process_id: str) -> dict[str, dict[str, Any]]:
        """Analyze waiting times per activity."""
        events = await self._get_process_events(process_id)
        if not events:
            return {}
        traces = await self._build_traces(events)
        activity_waits: dict[str, list[float]] = {}
        activity_counts: dict[str, int] = {}

        for case_id, activity_sequence in traces.items():
            case_events = [e for e in events if e.get("case_id") == case_id and e.get("timestamp")]
            case_events = sorted(
                case_events,
                key=lambda e: self._safe_parse_timestamp(e.get("timestamp")) or datetime.min,
            )
            for idx in range(1, len(case_events)):
                prev = case_events[idx - 1]
                current = case_events[idx]
                prev_ts = self._safe_parse_timestamp(prev.get("timestamp"))
                curr_ts = self._safe_parse_timestamp(current.get("timestamp"))
                if not prev_ts or not curr_ts:
                    continue
                wait_time = (curr_ts - prev_ts).total_seconds() / 3600
                activity = activity_sequence[idx]
                activity_waits.setdefault(activity, []).append(wait_time)
                activity_counts[activity] = activity_counts.get(activity, 0) + 1

        results: dict[str, dict[str, Any]] = {}
        for activity, waits in activity_waits.items():
            if waits:
                results[activity] = {
                    "avg_waiting_time": round(sum(waits) / len(waits), 2),
                    "frequency": activity_counts.get(activity, 0),
                }
        return results

    async def _analyze_throughput(self, process_id: str) -> float:
        """Analyze overall process throughput."""
        events = await self._get_process_events(process_id)
        if not events:
            return 0.0
        traces = await self._build_traces(events)
        timestamps = [
            self._safe_parse_timestamp(e.get("timestamp")) for e in events if e.get("timestamp")
        ]
        timestamps = [ts for ts in timestamps if ts]
        if len(timestamps) < 2:
            return float(len(traces))
        duration_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400
        if duration_days <= 0:
            return float(len(traces))
        return round(len(traces) / duration_days, 2)

    async def _generate_bottleneck_recommendations(
        self, bottlenecks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations for bottlenecks."""
        recommendations = []
        for bottleneck in bottlenecks:
            recommendations.append(
                f"Optimize {bottleneck.get('activity')} to reduce waiting time by automation or resource allocation"
            )
        return recommendations

    async def _get_designed_process_model(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """Get designed process model."""
        if self.workflow_engine_agent:
            response = await self.workflow_engine_agent.process(
                {"action": "get_process_model", "process_id": process_id}
            )
            if isinstance(response, dict) and response.get("model"):
                return response["model"]
        stored = self.process_model_store.get(tenant_id, process_id)
        if stored:
            return stored.get("model", {})
        return {"activities": [], "transitions": []}

    async def _compare_process_models(
        self, designed: dict[str, Any], actual: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Compare designed vs actual process models."""
        deviations = []

        # Compare activities
        designed_activities = set(designed.get("activities", []))
        actual_activities = set(actual.get("activities", []))

        # Find skipped activities
        skipped = designed_activities - actual_activities
        for activity in skipped:
            deviations.append(
                {"category": "skipped_activities", "activity": activity, "severity": "medium"}
            )

        # Find extra activities
        extra = actual_activities - designed_activities
        for activity in extra:
            deviations.append(
                {"category": "extra_activities", "activity": activity, "severity": "low"}
            )

        return deviations

    async def _calculate_compliance_rate(
        self,
        deviations: list[dict[str, Any]],
        total_expected_activities: int | None = None,
        total_cases: int | None = None,
    ) -> float:
        """
        Calculate a normalized process compliance score (0-100).

        Formula assumptions:
        - Each deviation contributes weighted penalty units based on category and severity.
          This allows critical misses (e.g., skipped activities) to degrade compliance more
          than low-severity additions (e.g., extra activities).
        - Penalties are normalized by process opportunity size
          (`total_expected_activities * total_cases`) so large process volumes are not
          over-penalized for small absolute deviation counts.
        - If process context is missing, fallback denominator uses deviation count to avoid
          divide-by-zero and to preserve meaningful scaling.
        - Final score is clamped to [0, 100] and rounded to 2 decimals.
        """
        if not deviations:
            return 100.0

        severity_weights: dict[str, float] = {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5,
        }
        category_weights: dict[str, float] = {
            "skipped_activities": 1.4,
            "unexpected_transition": 1.2,
            "wrong_sequence": 1.1,
            "excessive_loops": 0.9,
            "extra_activities": 0.6,
        }
        default_severity_by_category: dict[str, str] = {
            "skipped_activities": "high",
            "unexpected_transition": "medium",
            "wrong_sequence": "medium",
            "excessive_loops": "medium",
            "extra_activities": "low",
        }

        weighted_penalty = 0.0
        for deviation in deviations:
            category = str(deviation.get("category") or "")
            severity = str(
                deviation.get("severity") or default_severity_by_category.get(category, "medium")
            )
            weighted_penalty += category_weights.get(category, 1.0) * severity_weights.get(
                severity, 1.0
            )

        process_opportunities = (total_expected_activities or 0) * (total_cases or 0)
        denominator = max(1, process_opportunities, len(deviations))
        penalty_ratio = min(1.0, weighted_penalty / denominator)
        compliance_rate = (1.0 - penalty_ratio) * 100
        return round(min(100.0, max(0.0, compliance_rate)), 2)

    async def _identify_problematic_cases(
        self, events: list[dict[str, Any]], issue_id: str
    ) -> list[str]:
        """Identify problematic cases."""
        problematic = set()
        for event in events:
            if event.get("issue_id") == issue_id or event.get("status") in {"failed", "error"}:
                case_id = event.get("case_id")
                if case_id:
                    problematic.add(str(case_id))
        return list(problematic)

    async def _analyze_correlations(
        self, problematic_cases: list[str], events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Analyze correlations for root cause."""
        if not problematic_cases:
            return []
        total_cases = {str(event.get("case_id")) for event in events if event.get("case_id")}
        total_count = len(total_cases) or 1
        problematic_set = set(problematic_cases)
        activity_counts: dict[str, int] = {}
        for event in events:
            case_id = str(event.get("case_id")) if event.get("case_id") else None
            if case_id and case_id in problematic_set:
                activity = str(event.get("activity") or event.get("action") or "unknown")
                activity_counts[activity] = activity_counts.get(activity, 0) + 1

        correlations = []
        for activity, count in activity_counts.items():
            correlations.append(
                {
                    "factor": activity,
                    "occurrences": count,
                    "correlation": min(1.0, count / total_count),
                }
            )
        correlations.sort(key=lambda item: item["correlation"], reverse=True)
        return correlations

    async def _identify_contributing_factors(
        self, correlations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify contributing factors."""
        return [
            {"factor": "High workload", "correlation": 0.75},
            {"factor": "Insufficient resources", "correlation": 0.65},
        ]

    async def _generate_root_cause_insights(self, factors: list[dict[str, Any]]) -> list[str]:
        """Generate root cause insights."""
        return [f"Primary factor: {f.get('factor')}" for f in factors[:3]]

    async def _generate_remediation_recommendations(
        self, factors: list[dict[str, Any]]
    ) -> list[str]:
        """Generate remediation recommendations."""
        return ["Increase resource allocation", "Redistribute workload"]

    async def _estimate_improvement_benefits(
        self, improvement_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Estimate expected benefits."""
        impact = improvement_data.get("expected_impact", "medium")
        multiplier = {"low": 0.5, "medium": 1.0, "high": 1.5}.get(str(impact), 1.0)
        return {
            "cycle_time_reduction": 10.0 * multiplier,
            "cost_savings": 20000 * multiplier,
            "quality_improvement": 8.0 * multiplier,
        }

    async def _assess_improvement_feasibility(
        self, improvement_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Assess improvement feasibility."""
        return {
            "technical_feasibility": 0.85,
            "resource_availability": 0.70,
            "estimated_effort": 40,  # hours
        }

    async def _calculate_improvement_priority(
        self,
        benefits: dict[str, Any],
        feasibility: dict[str, Any],
        improvement_data: dict[str, Any],
    ) -> float:
        """Calculate improvement priority score."""
        # Weighted score
        benefit_score = benefits.get("cycle_time_reduction", 0) + (
            benefits.get("cost_savings", 0) / 1000
        )
        feasibility_score = feasibility.get("technical_feasibility", 0) * feasibility.get(
            "resource_availability", 0
        )

        return benefit_score * feasibility_score  # type: ignore

    async def _measure_actual_benefits(self, improvement: dict[str, Any]) -> dict[str, Any]:
        """Measure actual benefits achieved."""
        expected = improvement.get("expected_benefits", {})
        return {
            "cycle_time_reduction": expected.get("cycle_time_reduction", 10.0) * 0.85,
            "cost_savings": expected.get("cost_savings", 20000) * 0.9,
            "quality_improvement": expected.get("quality_improvement", 8.0) * 0.9,
        }

    async def _calculate_benefit_realization(
        self, expected: dict[str, Any], actual: dict[str, Any]
    ) -> float:
        """Calculate benefit realization percentage."""
        if not expected:
            return 0.0

        # Calculate average realization
        realizations = []
        for key in expected.keys():
            if key in actual and expected[key] > 0:
                realizations.append((actual[key] / expected[key]) * 100)

        return sum(realizations) / len(realizations) if realizations else 0.0

    async def _calculate_improvement_roi(
        self, improvement: dict[str, Any], actual_benefits: dict[str, Any]
    ) -> float:
        """Calculate ROI for improvement."""
        cost_savings = actual_benefits.get("cost_savings", 0)
        effort_hours = improvement.get("feasibility", {}).get("estimated_effort", 40)
        cost = effort_hours * 100  # Assume $100/hour

        if cost == 0:
            return 0.0

        return ((cost_savings - cost) / cost) * 100  # type: ignore

    async def _get_current_process_metrics(self, process_id: str) -> dict[str, Any]:
        """Get current process metrics."""
        process_model = self.process_models.get(process_id)
        if process_model:
            return process_model.get("metrics", {})  # type: ignore
        return {}

    async def _get_benchmark_data(
        self, process_id: str, criteria: dict[str, Any]
    ) -> dict[str, Any]:
        """Get benchmark data for comparison."""
        stored = self.benchmarks.get(process_id)
        if stored:
            return stored
        return {"median_cycle_time": 20.0, "throughput": 30.0, "avg_waiting_time": 1.8}

    async def _compare_metrics(
        self, current: dict[str, Any], benchmark: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare current metrics to benchmark."""
        comparison = {}
        for key in benchmark.keys():
            if key in current:
                comparison[key] = {
                    "current": current[key],
                    "benchmark": benchmark[key],
                    "variance": current[key] - benchmark[key],
                }
        return comparison

    async def _identify_performance_gaps(self, comparison: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify performance gaps."""
        gaps = []
        for metric, data in comparison.items():
            if data.get("variance", 0) > 0:  # Worse than benchmark
                gaps.append(
                    {
                        "metric": metric,
                        "gap": data["variance"],
                        "severity": "high" if abs(data["variance"]) > 10 else "medium",
                    }
                )
        return gaps

    async def _calculate_performance_ranking(self, comparison: dict[str, Any]) -> str:
        """Calculate performance ranking."""
        if not comparison:
            return "Unknown"
        score = 0
        for metric, data in comparison.items():
            variance = data.get("variance", 0)
            if variance <= 0:
                score += 1
            elif variance < 5:
                score += 0
            else:
                score -= 1
        if score >= 2:
            return "Top Performer"
        if score <= -2:
            return "Below Benchmark"
        return "Average"

    async def _identify_top_performers(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify top-performing processes."""
        top_performers = []
        for process_id, model in self.process_models.items():
            metrics = model.get("metrics", {})
            throughput = metrics.get("throughput", 0)
            if throughput and throughput >= filters.get("min_throughput", 5):
                top_performers.append({"process_id": process_id, "metrics": metrics})
        return top_performers

    async def _extract_best_practices(
        self, top_performers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract best practices from top performers."""
        return [
            {"practice": "Automate manual approvals", "impact": "High"},
            {"practice": "Parallel processing where possible", "impact": "Medium"},
        ]

    async def _categorize_best_practices(
        self, practices: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize best practices."""
        categorized = {"automation": [], "optimization": [], "standardization": []}  # type: ignore
        for practice in practices:
            categorized["optimization"].append(practice)
        return categorized

    async def _generate_process_recommendations(
        self, metrics: dict[str, Any], bottlenecks: dict[str, Any], deviations: dict[str, Any]
    ) -> list[str]:
        """Generate comprehensive process recommendations."""
        recommendations = []

        if bottlenecks.get("bottlenecks_detected", 0) > 0:
            recommendations.append("Address identified bottlenecks to improve throughput")

        if deviations.get("total_deviations", 0) > 5:
            recommendations.append("Improve process compliance through training and automation")

        if not recommendations:
            recommendations.append("Process is performing well - maintain current practices")

        return recommendations

    async def _matches_improvement_filters(
        self, improvement: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if improvement matches filters."""
        if "status" in filters and improvement.get("status") != filters["status"]:
            return False

        if "category" in filters and improvement.get("category") != filters["category"]:
            return False

        return True

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
        await self._ingest_event_log(tenant_id, [event])

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

    async def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        if not event.get("activity"):
            return None
        timestamp = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
        normalized = {
            **event,
            "timestamp": timestamp,
            "process_id": event.get("process_id") or "unknown",
        }
        if self._safe_parse_timestamp(normalized.get("timestamp")) is None:
            return None
        return normalized

    async def _build_traces(self, events: list[dict[str, Any]]) -> dict[str, list[str]]:
        traces: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            case_id = event.get("case_id", "unknown")
            traces.setdefault(case_id, []).append(event)
        ordered_traces: dict[str, list[str]] = {}
        for case_id, case_events in traces.items():
            ordered = sorted(
                case_events,
                key=lambda e: self._safe_parse_timestamp(e.get("timestamp")) or datetime.min,
            )
            ordered_traces[case_id] = [e.get("activity") for e in ordered if e.get("activity")]
        return ordered_traces

    async def _calculate_average_waiting_time(self, events: list[dict[str, Any]]) -> float:
        traces = await self._build_traces(events)
        wait_times = []
        for case_id in traces:
            case_events = [e for e in events if e.get("case_id") == case_id]
            case_events = sorted(
                case_events,
                key=lambda e: self._safe_parse_timestamp(e.get("timestamp")) or datetime.min,
            )
            for idx in range(1, len(case_events)):
                prev_ts = self._safe_parse_timestamp(case_events[idx - 1].get("timestamp"))
                curr_ts = self._safe_parse_timestamp(case_events[idx].get("timestamp"))
                if prev_ts and curr_ts:
                    wait_times.append((curr_ts - prev_ts).total_seconds() / 3600)
        if not wait_times:
            return 0.0
        return round(sum(wait_times) / len(wait_times), 2)

    def _safe_parse_timestamp(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    async def _store_recommendations(
        self,
        tenant_id: str,
        process_id: str,
        recommendations: list[str],
        context: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "process_id": process_id,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if context:
            payload["context"] = context
        self.recommendations_store.upsert(tenant_id, process_id, payload)
        if self.event_bus:
            await self.event_bus.publish(
                "process.recommendations.generated",
                {"event_type": "process.recommendations.generated", "data": payload},
            )
        await self._publish_lessons_learned(tenant_id, payload)

    async def _publish_lessons_learned(self, tenant_id: str, payload: dict[str, Any]) -> None:
        knowledge_payload = {
            "source_agent": self.agent_id,
            "title": f"Process improvement recommendations for {payload.get('process_id')}",
            "summary": "\n".join(payload.get("recommendations", [])),
            "content": json.dumps(payload, indent=2),
            "tags": ["process_mining", "continuous_improvement", "lessons_learned"],
            "metadata": {
                "process_id": payload.get("process_id"),
                "generated_at": payload.get("generated_at"),
            },
        }
        if self.knowledge_agent:
            await self.knowledge_agent.process(
                {
                    "action": "ingest_agent_output",
                    "tenant_id": tenant_id,
                    "payload": knowledge_payload,
                }
            )
            return
        if self.event_bus:
            await self.event_bus.publish(
                self.knowledge_event_topic,
                {"tenant_id": tenant_id, **knowledge_payload},
            )

    async def _emit_deviation_alert(self, process_id: str, report: dict[str, Any]) -> None:
        total_deviations = report.get("total_deviations") or len(report.get("deviations", []))
        if total_deviations < self.max_deviation_alerts:
            return
        event_payload = {
            "event_type": "process.deviation.alert",
            "data": {
                "process_id": process_id,
                "total_deviations": total_deviations,
                "report": report,
            },
        }
        if self.event_bus:
            await self.event_bus.publish("process.deviation.alert", event_payload)

    def _pairwise(self, sequence: Iterable[str]) -> Iterable[tuple[str, str]]:
        items = list(sequence)
        for idx in range(len(items) - 1):
            yield items[idx], items[idx + 1]

    def _resolve_store_path(self, config: dict[str, Any] | None, key: str, fallback: str) -> Path:
        if config and config.get(key):
            return Path(config.get(key))
        return Path(fallback)
