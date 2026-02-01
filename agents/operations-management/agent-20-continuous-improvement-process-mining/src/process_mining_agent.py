"""
Agent 20: Continuous Improvement & Process Mining Agent

Purpose:
Facilitates ongoing improvement by analyzing execution data to uncover inefficiencies,
bottlenecks and deviations, and by managing improvement initiatives.

Specification: agents/operations-management/agent-20-continuous-improvement-process-mining/README.md
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

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
        self.event_log_store = TenantStateStore(event_log_store_path)
        self.process_model_store = TenantStateStore(process_model_store_path)
        self.conformance_store = TenantStateStore(conformance_store_path)
        self.recommendations_store = TenantStateStore(recommendations_store_path)

        # Data stores (will be replaced with database)
        self.event_logs = {}  # type: ignore
        self.process_models = {}  # type: ignore
        self.improvement_backlog = {}  # type: ignore
        self.benefit_tracking = {}  # type: ignore
        self.benchmarks = {}  # type: ignore
        self.workflow_engine_agent = config.get("workflow_engine_agent") if config else None
        self.knowledge_agent = config.get("knowledge_agent") if config else None
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except Exception:
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

    async def initialize(self) -> None:
        """Initialize process mining tools, analytics, and data sources."""
        await super().initialize()
        self.logger.info("Initializing Continuous Improvement & Process Mining Agent...")

        # Future work: Initialize Azure Event Hubs for event log ingestion
        # Future work: Set up Azure Data Lake Storage Gen2 for event log storage
        # Future work: Connect to Azure Databricks for process mining algorithms
        # Future work: Initialize Azure Synapse Analytics for event log analysis
        # Future work: Set up Azure Machine Learning for anomaly detection
        # Future work: Connect to Azure Data Factory for ETL orchestration
        # Future work: Initialize Power BI for process visualization dashboards
        # Future work: Set up Azure SQL Database for improvement backlog
        # Future work: Connect to Jira/Azure DevOps for improvement task sync
        # Future work: Initialize Azure Service Bus for process insights events
        # Future work: Set up Azure Cognitive Services for root cause analysis

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
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
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

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _ingest_event_log(
        self, tenant_id: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Ingest event log data for process mining.

        Returns ingestion statistics.
        """
        self.logger.info(f"Ingesting event log with {len(events)} events")

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
            "ingested_at": datetime.utcnow().isoformat(),
        }
        self.event_logs[log_id] = log_record
        self.event_log_store.upsert(tenant_id, log_id, log_record)

        # Future work: Store in Azure Data Lake Storage
        # Future work: Index for querying
        # Future work: Publish events.ingested event

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
        self.logger.info(f"Checking conformance for process: {process_id}")

        events = await self._get_process_events(process_id)
        if not events:
            raise ValueError(f"No events found for process: {process_id}")

        traces = await self._build_traces(events)
        expected_activities = set(expected_model.get("activities", []))
        expected_transitions = {
            (edge.get("from"), edge.get("to"))
            for edge in expected_model.get("transitions", [])
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

        compliance_rate = (
            (compliant_traces / len(traces)) * 100 if traces else 0.0
        )
        report = {
            "process_id": process_id,
            "expected_model": expected_model,
            "total_traces": len(traces),
            "compliant_traces": compliant_traces,
            "compliance_rate": compliance_rate,
            "deviations": deviations,
            "checked_at": datetime.utcnow().isoformat(),
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
        self.logger.info(f"Discovering process {process_id} using {algorithm}")

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
            "discovered_at": datetime.utcnow().isoformat(),
        }
        self.process_models[process_id] = model_record
        self.process_model_store.upsert(tenant_id, process_id, model_record)

        # Future work: Store in database
        # Future work: Publish process.discovered event

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
        self.logger.info(f"Detecting bottlenecks for process: {process_id}")

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
        self.logger.info(f"Detecting deviations for process: {process_id}")

        # Get designed process model
        # Future work: Get from Workflow & Process Engine Agent
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
            "compliance_rate": await self._calculate_compliance_rate(deviations),
        }
        await self._emit_deviation_alert(process_id, report)
        return report

    async def _analyze_root_cause(self, process_id: str, issue_id: str) -> dict[str, Any]:
        """
        Perform root cause analysis on process issue.

        Returns root cause insights.
        """
        self.logger.info(f"Analyzing root cause for issue {issue_id} in process {process_id}")

        # Get process events
        events = await self._get_process_events(process_id)

        # Identify problematic cases
        problematic_cases = await self._identify_problematic_cases(events, issue_id)

        # Analyze correlations
        # Future work: Use decision trees or clustering
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
        self.logger.info(f"Creating improvement: {improvement_data.get('title')}")

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
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store improvement
        self.improvement_backlog[improvement_id] = improvement
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

        # Future work: Store in database
        # Future work: Sync with Jira/Azure DevOps
        # Future work: Publish improvement.created event

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

    async def _track_benefits(self, improvement_id: str) -> dict[str, Any]:
        """
        Track benefit realization for improvement.

        Returns benefit metrics.
        """
        self.logger.info(f"Tracking benefits for improvement: {improvement_id}")

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
            "measured_at": datetime.utcnow().isoformat(),
        }

        # Future work: Store in database
        # Future work: Update Financial Management Agent forecasts
        # Future work: Publish benefits.realized event

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
        self.logger.info(f"Benchmarking performance for process: {process_id}")

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

        # Future work: Push to Knowledge Management Agent
        # Future work: Generate templates and guidelines

        return {
            "total_practices": len(best_practices),
            "best_practices": best_practices,
            "categorized": categorized_practices,
            "top_performers": top_performers,
        }

    async def _get_process_insights(self, tenant_id: str, process_id: str) -> dict[str, Any]:
        """
        Get comprehensive process insights.

        Returns process analysis.
        """
        self.logger.info(f"Generating insights for process: {process_id}")

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
            "generated_at": datetime.utcnow().isoformat(),
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
            "generated_at": datetime.utcnow().isoformat(),
            "filters": filters,
            "process_kpis": await self._calculate_grouped_kpis(all_events, "process_id"),
            "project_kpis": await self._calculate_grouped_kpis(all_events, "project_id"),
            "program_kpis": await self._calculate_grouped_kpis(all_events, "program_id"),
        }

    # Helper methods

    async def _generate_log_id(self) -> str:
        """Generate unique log ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"LOG-{timestamp}"

    async def _generate_improvement_id(self) -> str:
        """Generate unique improvement ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
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
        except Exception:
            return []
        logs: list[dict[str, Any]] = []
        for tenant_records in parsed.values():
            if isinstance(tenant_records, dict):
                logs.extend(
                    record
                    for record in tenant_records.values()
                    if isinstance(record, dict)
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
            {"id": activity, "label": activity}
            for activity in process_model.get("activities", [])
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

        median_cycle_time = (
            sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
        )
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

        median_cycle_time = (
            sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
        )
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
        return (
            metadata.get(key)
            if isinstance(metadata, dict)
            else event.get(key)
        )

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
            case_events = [
                e for e in events if e.get("case_id") == case_id and e.get("timestamp")
            ]
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
            self._safe_parse_timestamp(e.get("timestamp"))
            for e in events
            if e.get("timestamp")
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

    async def _get_designed_process_model(
        self, tenant_id: str, process_id: str
    ) -> dict[str, Any]:
        """Get designed process model."""
        # Future work: Query from Workflow & Process Engine Agent
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

    async def _calculate_compliance_rate(self, deviations: list[dict[str, Any]]) -> float:
        """Calculate process compliance rate."""
        if not deviations:
            return 100.0

        # Simple calculation (replace with actual algorithm)
        return max(0, 100 - (len(deviations) * 5))

    async def _identify_problematic_cases(
        self, events: list[dict[str, Any]], issue_id: str
    ) -> list[str]:
        """Identify problematic cases."""
        # Future work: Identify cases with issues
        return []

    async def _analyze_correlations(
        self, problematic_cases: list[str], events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Analyze correlations for root cause."""
        # Future work: Use statistical analysis
        return []

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
        # Future work: Use regression models
        return {
            "cycle_time_reduction": 15.0,  # percent
            "cost_savings": 25000,  # dollars
            "quality_improvement": 10.0,  # percent
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
        # Future work: Measure from actual process data
        return {"cycle_time_reduction": 12.0, "cost_savings": 22000, "quality_improvement": 8.5}

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
        # Future work: Calculate actual ROI
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
        # Future work: Query benchmark database
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
        # Future work: Calculate actual ranking
        return "Average"

    async def _identify_top_performers(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify top-performing processes."""
        # Future work: Identify from benchmarks
        return []

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

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Continuous Improvement & Process Mining Agent...")
        # Future work: Close database connections
        # Future work: Close analytics connections
        # Future work: Flush pending events

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
        if not self.event_bus:
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
            or datetime.utcnow().isoformat(),
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
        timestamp = event.get("timestamp") or datetime.utcnow().isoformat()
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
            "generated_at": datetime.utcnow().isoformat(),
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

    async def _publish_lessons_learned(
        self, tenant_id: str, payload: dict[str, Any]
    ) -> None:
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
                {"action": "ingest_agent_output", "tenant_id": tenant_id, "payload": knowledge_payload}
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

    def _resolve_store_path(
        self, config: dict[str, Any] | None, key: str, fallback: str
    ) -> Path:
        if config and config.get(key):
            return Path(config.get(key))
        return Path(fallback)
