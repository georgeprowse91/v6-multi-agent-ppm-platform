"""
Agent 25: Analytics Insights Agent

Purpose:
Aggregates platform telemetry, computes KPIs, runs predictive analytics, and disseminates
recommendations and insights across the platform.

Specification: agents/operations-management/agent-25-analytics-insights/README.md
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

AGENT_22_SRC = (
    Path(__file__).resolve().parents[2]
    / "agent-22-analytics-insights"
    / "src"
)
AGENT_22_MODULE_PATH = AGENT_22_SRC / "analytics_insights_agent.py"
spec = importlib.util.spec_from_file_location("analytics_insights_agent_22", AGENT_22_MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError("Unable to load analytics_insights_agent_22 module")
analytics_insights_agent_22 = importlib.util.module_from_spec(spec)
sys.modules["analytics_insights_agent_22"] = analytics_insights_agent_22
spec.loader.exec_module(analytics_insights_agent_22)
BaseAnalyticsInsightsAgent = analytics_insights_agent_22.AnalyticsInsightsAgent


class AnalyticsInsightsAgent(BaseAnalyticsInsightsAgent):
    """Analytics Insights Agent for aggregated KPI and forecasting delivery."""

    def __init__(self, agent_id: str = "agent_025_analytics", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self._extend_kpi_definitions()

    def _extend_kpi_definitions(self) -> None:
        required_kpis = [
            {
                "name": "Schedule Adherence (%)",
                "metric_name": "schedule.adherence",
                "target": 0.95,
                "thresholds": {"min": 0.9},
                "event_types": ["schedule.baseline.locked", "schedule.delay"],
                "trend_direction": "higher_is_better",
            },
            {
                "name": "Cost Variance (%)",
                "metric_name": "cost.variance.pct",
                "target": 0.0,
                "thresholds": {"max": 0.1},
                "event_types": ["finance.cost.updated", "finance.budget.updated"],
                "trend_direction": "lower_is_better",
            },
            {
                "name": "Program Performance Index",
                "metric_name": "program.performance.index",
                "target": 0.85,
                "thresholds": {"min": 0.75},
                "event_types": ["program.status.updated", "project.health.updated"],
                "trend_direction": "higher_is_better",
            },
            {
                "name": "Defect Density",
                "metric_name": "quality.defect_density",
                "target": 0.5,
                "thresholds": {"max": 1.0},
                "event_types": ["quality.metrics.calculated"],
                "trend_direction": "lower_is_better",
            },
            {
                "name": "Compliance Level",
                "metric_name": "compliance.level.score",
                "target": 0.9,
                "thresholds": {"min": 0.85},
                "event_types": ["quality.audit.completed", "compliance.audit.completed"],
                "trend_direction": "higher_is_better",
            },
            {
                "name": "System Health Score",
                "metric_name": "system.health.score",
                "target": 0.9,
                "thresholds": {"min": 0.8},
                "event_types": ["system.health.updated", "system.health.metrics"],
                "trend_direction": "higher_is_better",
            },
        ]

        existing_names = {kpi.get("name") for kpi in self.kpi_definitions or []}
        existing_metrics = {kpi.get("metric_name") for kpi in self.kpi_definitions or []}
        for kpi in required_kpis:
            if kpi.get("name") in existing_names or kpi.get("metric_name") in existing_metrics:
                continue
            self.kpi_definitions.append(kpi)

    async def _calculate_kpi_value(self, kpi_config: dict[str, Any]) -> float:
        metric_name = kpi_config.get("metric_name")
        tenant_id = kpi_config.get("tenant_id", "default")
        events = await self._get_events_for_tenant(tenant_id)
        if metric_name == "schedule.adherence":
            adherence = [
                float(event.get("payload", {}).get("adherence", 0))
                for event in self._filter_events(events, {"schedule.baseline.locked", "schedule.delay"})
                if event.get("payload", {}).get("adherence") is not None
            ]
            if adherence:
                return sum(adherence) / len(adherence)
            delays = [
                float(event.get("payload", {}).get("delay_days", 0))
                for event in self._filter_events(events, {"schedule.delay"})
            ]
            return max(0.0, 1.0 - (sum(delays) / len(delays) / 10.0)) if delays else 1.0
        if metric_name == "cost.variance.pct":
            variances = []
            for event in self._filter_events(events, {"finance.cost.updated", "finance.budget.updated"}):
                payload = event.get("payload", {})
                if payload.get("variance_pct") is not None:
                    variances.append(float(payload.get("variance_pct")))
                    continue
                actual = payload.get("cost_actual")
                planned = payload.get("cost_planned") or payload.get("cost_budget")
                if actual is not None and planned:
                    variances.append((float(actual) - float(planned)) / float(planned))
            return sum(variances) / len(variances) if variances else 0.0
        if metric_name == "program.performance.index":
            scores = [
                float(event.get("payload", {}).get("performance_index", 0))
                for event in self._filter_events(events, {"program.status.updated", "project.health.updated"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        if metric_name == "quality.defect_density":
            densities = []
            for event in self._filter_events(events, {"quality.metrics.calculated"}):
                payload = event.get("payload", {})
                if payload.get("defect_density") is not None:
                    densities.append(float(payload.get("defect_density")))
                    continue
                defects = payload.get("defect_count")
                kloc = payload.get("kloc") or payload.get("thousand_lines_of_code")
                if defects is not None and kloc:
                    densities.append(float(defects) / float(kloc))
            return sum(densities) / len(densities) if densities else 0.0
        if metric_name == "compliance.level.score":
            scores = [
                float(event.get("payload", {}).get("compliance_score", 0))
                for event in self._filter_events(events, {"quality.audit.completed", "compliance.audit.completed"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        if metric_name == "system.health.score":
            scores = [
                float(event.get("payload", {}).get("health_score", 0))
                for event in self._filter_events(events, {"system.health.updated", "system.health.metrics"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        return await super()._calculate_kpi_value(kpi_config)

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        action = input_data.get("action", "")
        if action in {"ingest_metrics", "get_kpi_trends", "get_forecasts"}:
            return True
        return await super().validate_input(input_data)

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action", "get_insights")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        if action == "ingest_metrics":
            return await self._ingest_metrics(
                tenant_id,
                input_data.get("events", []),
                input_data.get("metrics", []),
            )
        if action == "get_kpi_trends":
            return await self._get_kpi_trends(
                tenant_id,
                input_data.get("kpi_ids"),
                input_data.get("lookback_days", 30),
            )
        if action == "get_forecasts":
            return await self._get_forecasts(tenant_id, input_data.get("forecast_requests", []))
        return await super().process(input_data)

    async def _ingest_metrics(
        self,
        tenant_id: str,
        events: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> dict[str, Any]:
        event_counts: dict[str, int] = {}
        for event in events:
            event_type = event.get("event_type", "analytics.event")
            payload = event.get("payload", {})
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            await self._handle_domain_event({"tenant_id": tenant_id, "payload": payload}, event_type)

        aggregated_payload = {
            "tenant_id": tenant_id,
            "event_counts": event_counts,
            "metrics": metrics,
            "ingested_at": datetime.utcnow().isoformat(),
        }
        synapse_result = self.synapse_manager.ingest_dataset(
            "analytics_aggregated", [aggregated_payload]
        )
        data_lake_paths = None
        if self.data_lake_manager:
            data_lake_paths = self.data_lake_manager.store_dataset(
                "analytics", "aggregated", [aggregated_payload]
            )
        return {
            "tenant_id": tenant_id,
            "event_counts": event_counts,
            "synapse": synapse_result,
            "data_lake": data_lake_paths,
            "metrics": metrics,
        }

    async def _get_kpi_trends(
        self,
        tenant_id: str,
        kpi_ids: list[str] | None,
        lookback_days: int,
    ) -> dict[str, Any]:
        cutoff = datetime.utcnow().timestamp() - (lookback_days * 86400)
        if not kpi_ids:
            kpi_ids = list(self.kpis.keys())
        trends = []
        for kpi_id in kpi_ids:
            history = await self._get_kpi_history(tenant_id, kpi_id)
            filtered = [
                entry
                for entry in history
                if datetime.fromisoformat(entry.get("recorded_at", "1970-01-01")).timestamp()
                >= cutoff
            ]
            current_value = filtered[-1]["value"] if filtered else 0.0
            trend = await self._calculate_kpi_trend(
                filtered, current_value, self.kpis.get(kpi_id, {}).get("trend_direction")
            )
            trends.append(
                {
                    "kpi_id": kpi_id,
                    "current_value": current_value,
                    "entries": filtered,
                    "trend": trend,
                }
            )
        return {"tenant_id": tenant_id, "trends": trends, "lookback_days": lookback_days}

    async def _get_forecasts(
        self, tenant_id: str, forecast_requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        forecasts = []
        for request in forecast_requests:
            model_type = request.get("model_type")
            input_payload = request.get("input_data", {})
            forecasts.append(await self._run_prediction(tenant_id, model_type, input_payload))
        return {
            "tenant_id": tenant_id,
            "forecasts": forecasts,
            "generated_at": datetime.utcnow().isoformat(),
        }
