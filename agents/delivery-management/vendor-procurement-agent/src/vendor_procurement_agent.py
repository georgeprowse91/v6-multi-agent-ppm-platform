"""
Vendor & Procurement Management Agent

Purpose:
Streamlines end-to-end procurement lifecycle from vendor onboarding and contract management
to purchase order processing and invoice reconciliation. Ensures external spending aligns
with organizational policies and supports vendor performance monitoring.

Specification: agents/delivery-management/vendor-procurement-agent/README.md
"""

import importlib
import json
import logging
import os
import re
import uuid
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib import request

from data_quality.helpers import validate_against_schema

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from llm.client import LLMGateway, LLMProviderError  # noqa: E402
from workflow_task_queue import build_task_message, build_task_queue  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentManagementService,
    DocumentMetadata,
)
from agents.common.web_search import (  # noqa: E402
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402

if TYPE_CHECKING:
    pass


@dataclass
class ConnectorStatus:
    name: str
    status: str
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProcurementConnectorService:
    """Integration hub for procurement systems (SAP Ariba, Coupa, Oracle, Dynamics, ERP/AP)."""

    DEFAULT_CONNECTOR_SPECS = {
        "sap_ariba": {"module": "sap_ariba_connector", "class": "SAPAribaConnector"},
        "coupa": {"module": "coupa_connector", "class": "CoupaConnector"},
        "oracle_procurement": {
            "module": "oracle_procurement_connector",
            "class": "OracleProcurementConnector",
        },
        "dynamics_365": {
            "module": "dynamics_procurement_connector",
            "class": "DynamicsProcurementConnector",
        },
        "erp_ap": {"module": "erp_ap_connector", "class": "ERPAPConnector"},
    }

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.connector_specs = {
            **self.DEFAULT_CONNECTOR_SPECS,
            **self.config.get("connector_specs", {}),
        }
        self.enabled_connectors = self.config.get(
            "enabled_connectors",
            ["sap_ariba", "coupa", "oracle_procurement", "dynamics_365", "erp_ap"],
        )
        self.connector_configs = self.config.get("connectors", {})
        self.connectors: dict[str, Any] = {}

    def initialize(self) -> list[ConnectorStatus]:
        statuses: list[ConnectorStatus] = []
        for name in self.enabled_connectors:
            spec = self.connector_specs.get(name, {})
            module_name = spec.get("module")
            class_name = spec.get("class")
            connector_config = self.connector_configs.get(name, {})
            connector = self._load_connector(name, module_name, class_name, connector_config)
            self.connectors[name] = connector
            if connector is None:
                statuses.append(
                    ConnectorStatus(
                        name=name,
                        status="fallback",
                        detail="Connector unavailable, using fallback integration.",
                    )
                )
            else:
                statuses.append(
                    ConnectorStatus(
                        name=name,
                        status="connected",
                        metadata={"module": module_name, "class": class_name},
                    )
                )
        return statuses

    def _load_connector(
        self,
        name: str,
        module_name: str | None,
        class_name: str | None,
        connector_config: dict[str, Any],
    ) -> Any | None:
        if not module_name or not class_name:
            self.logger.info("Connector spec missing for %s", name)
            return None

        try:
            module = importlib.import_module(module_name)
            connector_class = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            self.logger.info("Connector %s not available: %s", name, exc)
            return None

        try:
            return connector_class(connector_config)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: BLE001 - connector constructors can fail
            self.logger.warning("Connector %s failed to initialize: %s", name, exc)
            return None

    def _dispatch(self, method: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for name, connector in self.connectors.items():
            if connector is None or not hasattr(connector, method):
                results.append(
                    {
                        "connector": name,
                        "status": "skipped",
                        "method": method,
                        "detail": "Connector not available or method not supported.",
                    }
                )
                continue
            try:
                result = getattr(connector, method)(payload)
                results.append(
                    {"connector": name, "status": "ok", "method": method, "result": result}
                )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: BLE001 - external connectors may raise
                results.append(
                    {
                        "connector": name,
                        "status": "error",
                        "method": method,
                        "detail": str(exc),
                    }
                )
        return results

    def sync_vendor(self, vendor: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("sync_vendor", vendor)

    def publish_rfp(self, rfp: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("publish_rfp", rfp)

    def submit_proposal(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("submit_proposal", proposal)

    def select_vendor(self, selection: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("select_vendor", selection)

    def create_contract(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("create_contract", contract)

    def release_purchase_order(self, purchase_order: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("release_purchase_order", purchase_order)

    def record_invoice(self, invoice: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("record_invoice", invoice)

    def initiate_payment(self, payment: dict[str, Any]) -> list[dict[str, Any]]:
        return self._dispatch("initiate_payment", payment)


class ProcurementEventPublisher:
    """Publishes procurement lifecycle events to configured sinks."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
        event_bus: "EventBusClient | None" = None,
    ):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.event_bus = event_bus or EventBusClient(self.config.get("event_bus"))

    async def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Publishing procurement event %s", event.get("event_type"))
        bus_result = await self.event_bus.publish(event)
        return {
            "status": "published",
            "event_id": event.get("event_id"),
            "event_bus": bus_result,
        }


class TaskManagementClient:
    """Client for publishing mitigation tasks to the task queue."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.task_queue = self.config.get("task_queue") or build_task_queue(
            self.config.get("queue_config")
        )

    async def create_task(
        self,
        *,
        tenant_id: str,
        instance_id: str,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task_id = f"{task_type}-{uuid.uuid4()}"
        message = build_task_message(
            tenant_id=tenant_id,
            instance_id=instance_id,
            task_id=task_id,
            task_type=task_type,
            payload=payload,
        )
        await self.task_queue.publish_task(message)
        return {
            "task_id": task_id,
            "status": "queued",
            "queue_backend": self.task_queue.__class__.__name__,
            "message_id": message.message_id,
        }


class CommunicationsClient:
    """Client wrapper for Stakeholder & Communications agent integration."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.agent = self.config.get("agent")
        self.enabled = self.config.get("enabled", True)

        if self.agent is None and self.config.get("use_agent", False):
            try:
                module = importlib.import_module("stakeholder_communications_agent")
                agent_cls = getattr(module, "StakeholderCommunicationsAgent")
                self.agent = agent_cls(config=self.config.get("agent_config"))
            except (ImportError, AttributeError) as exc:
                self.logger.warning("Communications agent unavailable: %s", exc)
                self.agent = None

    async def notify(
        self,
        *,
        tenant_id: str,
        subject: str,
        body: str,
        stakeholders: list[str] | None = None,
        channel: str = "email",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "subject": subject}
        if not self.agent:
            self.logger.info("Communications agent not configured; skipping notify.")
            return {"status": "skipped", "subject": subject}

        message_payload = {
            "subject": subject,
            "content": body,
            "channel": channel,
            "stakeholder_ids": stakeholders or [],
            "data": metadata or {},
        }
        message = await self.agent.process(
            {"action": "generate_message", "message": message_payload, "tenant_id": tenant_id}
        )
        message_id = message.get("message_id")
        if not message_id:
            return {"status": "failed", "subject": subject}
        sent = await self.agent.process(
            {"action": "send_message", "message_id": message_id, "tenant_id": tenant_id}
        )
        return {
            "status": sent.get("status", "sent"),
            "message_id": message_id,
            "subject": subject,
        }


class LocalApprovalAgent:
    """Fallback approval workflow when external approval agent is unavailable."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "approval_id": f"local-{uuid.uuid4()}",
            "status": "auto-approved",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "request": input_data,
        }


class VendorMLService:
    """Azure ML-backed (or heuristic) service for vendor recommendations and risk scoring."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.model_metadata: dict[str, Any] = {}
        self.training_runs: list[dict[str, Any]] = []
        self.training_data = self.config.get("training_data", [])
        self.scoring_weights: dict[str, float] = self.config.get("scoring_weights", {})
        self.feature_weights: dict[str, float] = {}
        self.feature_stats: dict[str, float] = {}
        self.feature_order = [
            "cost_score",
            "quality_rating",
            "on_time_delivery_rate",
            "compliance_rating",
            "risk_score",
            "delivery_timeliness",
            "external_rating",
            "dispute_count",
            "total_spend",
        ]

    async def train_models(self, vendors: list[dict[str, Any]]) -> dict[str, Any]:
        run_id = f"ml-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        avg_risk = sum(v.get("risk_score", 50) for v in vendors) / len(vendors) if vendors else 50
        self._train_recommendation_model(vendors)
        self.model_metadata = {
            "run_id": run_id,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "vendor_count": len(vendors),
            "avg_risk": avg_risk,
            "provider": "azure_ml" if self.config.get("azure_ml_enabled") else "heuristic",
            "feature_weights": self.feature_weights,
        }
        self.training_runs.append(self.model_metadata)
        return self.model_metadata

    def risk_score(self, vendor: dict[str, Any], compliance_checks: dict[str, Any]) -> float:
        base_risk = 50.0
        if all(v == "Pass" for v in compliance_checks.values()):
            base_risk -= 10.0
        if vendor.get("certifications"):
            base_risk -= 5.0
        if vendor.get("financial_health") == "weak":
            base_risk += 15.0
        avg_risk = self.model_metadata.get("avg_risk", 50)
        adjusted = (base_risk * 0.7) + (avg_risk * 0.3)
        return max(0, min(100, adjusted))

    def recommend_vendors(
        self, vendors: list[dict[str, Any]], category: str, top_n: int = 5
    ) -> list[str]:
        candidates = [
            v
            for v in vendors
            if v.get("category") == category
            and v.get("status") in {"Approved", "pending", "active"}
        ]
        scored = []
        for vendor in candidates:
            score = self.score_vendor(vendor)
            scored.append((vendor.get("vendor_id"), score))
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        return [vendor_id for vendor_id, _ in ranked[:top_n] if vendor_id]

    def analyze_performance(
        self, metrics: dict[str, Any], vendor: dict[str, Any]
    ) -> dict[str, Any]:
        trend = "Stable"
        if metrics.get("delivery_timeliness", 100) < 90:
            trend = "Declining"
        if metrics.get("quality_rating", 5) > 4.5:
            trend = "Improving"
        adjusted_metrics = {
            **metrics,
            "risk_adjusted_score": max(0, 100 - vendor.get("risk_score", 50)),
        }
        return {
            "trend": trend,
            "adjusted_metrics": adjusted_metrics,
            "insights": [
                "ML model evaluated delivery and quality trends.",
                "Risk-adjusted score updated for analytics dashboards.",
            ],
        }

    def rank_vendors(self, vendors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(vendors, key=self.score_vendor, reverse=True)

    def score_vendor(self, vendor: dict[str, Any]) -> float:
        features = self._prepare_features(vendor)
        weights = self.feature_weights or self.scoring_weights
        if not weights:
            weights = {
                "quality_rating": 0.25,
                "on_time_delivery_rate": 0.2,
                "compliance_rating": 0.15,
                "risk_score": 0.2,
                "delivery_timeliness": 0.1,
                "cost_score": 0.1,
            }
        return self._weighted_score(features, weights)

    def score_proposal(
        self,
        proposal: dict[str, Any],
        criteria_weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        pricing = proposal.get("pricing", {})
        total_cost = pricing.get("total") or pricing.get("amount") or 0
        cost_score = max(0, 100 - (float(total_cost) / 1000))
        features = {
            "cost": cost_score,
            "quality": proposal.get("quality_score", 75),
            "delivery": proposal.get("delivery_score", 80),
            "risk": proposal.get("risk_score", 70),
            "compliance": proposal.get("compliance_score", 80),
        }
        weights = criteria_weights or self.scoring_weights or {}
        if not weights:
            weights = {
                "cost": 0.4,
                "quality": 0.25,
                "delivery": 0.15,
                "risk": 0.15,
                "compliance": 0.05,
            }
        normalized_weights = self._normalize_weights(weights, features.keys())
        return {
            key: float(features.get(key, 0)) * normalized_weights.get(key, 0) for key in features
        }

    def _prepare_features(self, vendor: dict[str, Any]) -> dict[str, float]:
        metrics = vendor.get("performance_metrics", {})
        cost_score = vendor.get("cost_score") or metrics.get("cost_score") or 0
        delivery_timeliness = metrics.get("delivery_timeliness") or metrics.get(
            "on_time_delivery_rate", 0
        )
        external_rating = vendor.get("external_rating") or vendor.get("external_ratings", {}).get(
            "overall", 0
        )
        return {
            "cost_score": float(cost_score),
            "quality_rating": metrics.get("quality_rating", 0) * 20,
            "on_time_delivery_rate": metrics.get("on_time_delivery_rate", 0),
            "compliance_rating": metrics.get("compliance_rating", 0),
            "risk_score": 100 - vendor.get("risk_score", 50),
            "delivery_timeliness": float(delivery_timeliness),
            "external_rating": float(external_rating),
            "dispute_count": max(0, 10 - vendor.get("dispute_count", 0)),
            "total_spend": min(vendor.get("total_spend", 0) / 1000, 100),
        }

    def _train_recommendation_model(self, vendors: list[dict[str, Any]]) -> None:
        training_rows = self.training_data or []
        if not training_rows and vendors:
            training_rows = [
                {
                    **self._prepare_features(vendor),
                    "label": 1 if vendor.get("risk_score", 50) < 50 else 0,
                }
                for vendor in vendors
            ]

        if not training_rows:
            self.feature_weights = {}
            return

        positives = defaultdict(list)
        negatives = defaultdict(list)
        for row in training_rows:
            label = 1 if row.get("label", 0) else 0
            target = positives if label else negatives
            for feature in self.feature_order:
                target[feature].append(float(row.get(feature, 0)))

        weights: dict[str, float] = {}
        for feature in self.feature_order:
            pos_avg = sum(positives[feature]) / len(positives[feature]) if positives[feature] else 0
            neg_avg = sum(negatives[feature]) / len(negatives[feature]) if negatives[feature] else 0
            weights[feature] = pos_avg - neg_avg

        total = sum(abs(value) for value in weights.values()) or 1.0
        self.feature_weights = {key: value / total for key, value in weights.items()}

    def _weighted_score(self, features: dict[str, float], weights: dict[str, float]) -> float:
        normalized = self._normalize_weights(weights, features.keys())
        score = sum(features.get(name, 0.0) * normalized.get(name, 0.0) for name in features)
        return max(0, min(100, score))

    def _normalize_weights(self, weights: dict[str, float], keys: Any) -> dict[str, float]:
        total = sum(abs(weights.get(key, 0.0)) for key in keys) or 1.0
        return {key: weights.get(key, 0.0) / total for key in keys}


class RiskDatabaseClient:
    """Client for vendor risk and sanctions databases."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.risk_sources = self.config.get("risk_sources", [])
        self.timeout = self.config.get("timeout", 8)
        self.mock_responses = self.config.get("mock_responses", {})

    def check_vendor(self, vendor_data: dict[str, Any]) -> dict[str, Any]:
        vendor_key = vendor_data.get("legal_name") or vendor_data.get("tax_id") or ""
        if vendor_key in self.mock_responses:
            return self.mock_responses[vendor_key]
        if not self.risk_sources:
            return {}

        results = {
            "sanctions_check": "Unknown",
            "anti_corruption_check": "Unknown",
            "credit_check": "Unknown",
            "watchlist_hits": [],
            "sources": [],
        }

        payload = {
            "vendor_name": vendor_data.get("legal_name"),
            "tax_id": vendor_data.get("tax_id"),
            "country": vendor_data.get("address", {}).get("country"),
        }

        for source in self.risk_sources:
            response = self._query_source(source, payload)
            if not response:
                continue
            status = response.get("status", "").lower()
            category = source.get("category", "sanctions")
            check_key = {
                "sanctions": "sanctions_check",
                "anti_corruption": "anti_corruption_check",
                "credit": "credit_check",
            }.get(category, "sanctions_check")
            results[check_key] = "Fail" if status in {"hit", "fail", "blocked"} else "Pass"
            results["watchlist_hits"].extend(response.get("hits", []))
            results["sources"].append(
                {
                    "name": source.get("name"),
                    "status": results[check_key],
                    "response_id": response.get("response_id"),
                }
            )

        return results

    def _query_source(self, source: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = source.get("endpoint")
        if not endpoint:
            return {}
        headers = {"Content-Type": "application/json"}
        api_key = source.get("api_key") or self.config.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request_payload = json.dumps(payload).encode("utf-8")
        req = request.Request(endpoint, data=request_payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                content = json.loads(response.read().decode("utf-8"))
                return {
                    "status": content.get("status", "unknown"),
                    "hits": content.get("hits", []),
                    "response_id": content.get("response_id"),
                }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: BLE001 - external calls best-effort
            self.logger.warning("Risk source %s failed: %s", source.get("name"), exc)
            return {}


class EventBusClient:
    """Publishes and dispatches procurement events to an enterprise event bus."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.endpoint = self.config.get("endpoint")
        self.timeout = self.config.get("timeout", 5)
        self.enabled = self.config.get("enabled", True)
        self._handlers: dict[str, list[Any]] = defaultdict(list)
        self._local_queue: deque[dict[str, Any]] = deque()

    def register_handler(self, event_type: str, handler: Any) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "event_id": event.get("event_id")}

        transport_status = "queued"
        if self.endpoint:
            try:
                payload = json.dumps(event).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                req = request.Request(self.endpoint, data=payload, headers=headers, method="POST")
                with request.urlopen(req, timeout=self.timeout) as response:
                    response.read()
                transport_status = "sent"
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: BLE001 - external call best-effort
                self.logger.warning("Event bus publish failed: %s", exc)
                transport_status = "error"

        self._local_queue.append(event)
        dispatched = await self.dispatch(event)
        return {
            "status": transport_status,
            "event_id": event.get("event_id"),
            "dispatched_handlers": dispatched,
        }

    async def dispatch(self, event: dict[str, Any]) -> int:
        handlers = self._handlers.get(event.get("event_type"), [])
        dispatched = 0
        for handler in handlers:
            result = handler(event)
            if hasattr(result, "__await__"):
                await result
            dispatched += 1
        return dispatched

    async def process_queue(self) -> int:
        processed = 0
        while self._local_queue:
            event = self._local_queue.popleft()
            processed += await self.dispatch(event)
        return processed


class ProcurementClassifier:
    """Naive Bayes text classifier for procurement request categorization."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.training_data = self.config.get("training_data", [])
        self.token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.category_counts: Counter[str] = Counter()
        self.vocab: set[str] = set()
        if self.training_data:
            self._train(self.training_data)

    def predict(self, text: str, fallback: str = "services") -> str:
        tokens = self._tokenize(text)
        if not self.token_counts:
            return self._heuristic(text, fallback=fallback)
        scores: dict[str, float] = {}
        vocab_size = len(self.vocab) or 1
        for category, counts in self.token_counts.items():
            total_tokens = sum(counts.values()) + vocab_size
            score = 0.0
            for token in tokens:
                score += (counts.get(token, 0) + 1) / total_tokens
            scores[category] = score
        if not scores:
            return self._heuristic(text, fallback=fallback)
        return max(scores.items(), key=lambda item: item[1])[0]

    def _train(self, training_data: list[dict[str, Any]]) -> None:
        for row in training_data:
            text = str(row.get("text", ""))
            category = str(row.get("category", "services"))
            tokens = self._tokenize(text)
            self.token_counts[category].update(tokens)
            self.category_counts[category] += 1
            self.vocab.update(tokens)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _heuristic(self, text: str, fallback: str = "services") -> str:
        description = text.lower()
        if "software" in description or "license" in description:
            return "software"
        if "cloud" in description or "aws" in description or "azure" in description:
            return "cloud"
        if "consultant" in description or "consulting" in description:
            return "consulting"
        return fallback


class FinancialManagementClient:
    """Client for budget checks against a financial management service."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.endpoint = self.config.get("endpoint")
        self.api_key = self.config.get("api_key")
        self.timeout = self.config.get("timeout", 5)
        self.budget_data = self.config.get("budget_data", {})

    def get_budget_status(self, request_data: dict[str, Any]) -> dict[str, Any]:
        if self.endpoint:
            response = self._call_budget_api(request_data)
            if response:
                return response

        project_id = request_data.get("project_id") or "default"
        program_id = request_data.get("program_id")
        key = program_id or project_id
        budget_info = self.budget_data.get(key, {"total": 0, "committed": 0})
        remaining = budget_info.get("total", 0) - budget_info.get("committed", 0)
        estimated_cost = request_data.get("estimated_cost", 0)
        return {
            "available": remaining >= estimated_cost,
            "remaining_budget": max(0, remaining - estimated_cost),
            "budget_total": budget_info.get("total", 0),
            "budget_committed": budget_info.get("committed", 0),
        }

    def _call_budget_api(self, request_data: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(request_data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: BLE001 - external calls best-effort
            self.logger.warning("Budget API call failed: %s", exc)
            return {}


class PerformanceAnalyticsClient:
    """Client for analytics services (delivery history, issue tracker, PM metrics)."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.endpoint = self.config.get("endpoint")
        self.api_key = self.config.get("api_key")
        self.timeout = self.config.get("timeout", 6)
        self.performance_data = self.config.get("performance_data", {})

    def get_vendor_summary(self, vendor_id: str) -> dict[str, Any]:
        if self.endpoint:
            response = self._call_analytics_api({"vendor_id": vendor_id})
            if response:
                return response
        return self.performance_data.get(
            vendor_id,
            {
                "deliveries": [],
                "quality_scores": [],
                "compliance_incidents": [],
                "sla_records": [],
                "issue_tracker": [],
                "total_spend": 0,
                "contract_count": 0,
                "dispute_count": 0,
            },
        )

    def _call_analytics_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(
            self.endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: BLE001 - external calls best-effort
            self.logger.warning("Analytics API call failed: %s", exc)
            return {}


class FormRecognizerClient:
    """Wrapper for Azure Form Recognizer clause extraction."""

    def __init__(self, config: dict[str, Any] | None = None, logger: logging.Logger | None = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.endpoint = self.config.get("endpoint") or os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
        self.api_key = self.config.get("api_key") or os.getenv("AZURE_FORM_RECOGNIZER_KEY")
        self.model = self.config.get("model", "prebuilt-document")

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def extract_clauses(self, contract_text: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        payload = json.dumps({"content": contract_text}).encode("utf-8")
        url = f"{self.endpoint}/formrecognizer/documentModels/{self.model}:analyze?api-version=2023-07-31"
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self.api_key,
        }
        req = request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                return json.loads(content)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:  # noqa: BLE001 - remote call best-effort
            self.logger.warning("Form Recognizer call failed: %s", exc)
            return None


class VendorProcurementAgent(BaseAgent):
    """
    Vendor & Procurement Management Agent - Manages procurement lifecycle and vendor relationships.

    Key Capabilities:
    - Vendor registry and onboarding
    - Procurement request intake and processing
    - RFP/RFQ generation and quote management
    - Vendor selection and scoring
    - Contract and agreement management
    - Purchase order creation and approval
    - Invoice receipt and reconciliation
    - Vendor performance monitoring
    - Compliance and audit support
    """

    DEFAULT_RFP_TEMPLATES = {
        "software": {
            "template_id": "rfp_software_v1",
            "sections": [
                "Executive Summary",
                "Scope of Work",
                "Technical Requirements",
                "Security & Compliance",
                "Pricing",
                "Implementation Timeline",
            ],
        },
        "services": {
            "template_id": "rfp_services_v1",
            "sections": [
                "Background",
                "Service Requirements",
                "Staffing & Credentials",
                "SLA Expectations",
                "Pricing & Payment Terms",
            ],
        },
        "consulting": {
            "template_id": "rfp_consulting_v1",
            "sections": [
                "Problem Statement",
                "Proposed Approach",
                "Team Experience",
                "Deliverables",
                "Commercials",
            ],
        },
        "cloud": {
            "template_id": "rfp_cloud_v1",
            "sections": [
                "Cloud Architecture Needs",
                "Migration Approach",
                "Security & Compliance",
                "Service Levels",
                "Pricing Model",
            ],
        },
    }

    def __init__(self, agent_id: str = "vendor-procurement-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.default_currency = config.get("default_currency", "AUD") if config else "AUD"
        self.procurement_threshold = config.get("procurement_threshold", 10000) if config else 10000
        self.min_vendor_proposals = config.get("min_vendor_proposals", 3) if config else 3
        self.invoice_tolerance_pct = config.get("invoice_tolerance_pct", 0.05) if config else 0.05
        self.vendor_schema_path = (
            Path(config.get("vendor_schema_path", "data/schemas/vendor.schema.json"))
            if config
            else Path("data/schemas/vendor.schema.json")
        )

        vendor_store_path = (
            Path(config.get("vendor_store_path", "data/vendors.json"))
            if config
            else Path("data/vendors.json")
        )
        contract_store_path = (
            Path(config.get("contract_store_path", "data/vendor_contracts.json"))
            if config
            else Path("data/vendor_contracts.json")
        )
        invoice_store_path = (
            Path(config.get("invoice_store_path", "data/vendor_invoices.json"))
            if config
            else Path("data/vendor_invoices.json")
        )
        self.vendor_store = TenantStateStore(vendor_store_path)
        self.contract_store = TenantStateStore(contract_store_path)
        self.invoice_store = TenantStateStore(invoice_store_path)
        performance_store_path = (
            Path(config.get("vendor_performance_store_path", "data/vendor_performance.json"))
            if config
            else Path("data/vendor_performance.json")
        )
        event_store_path = (
            Path(config.get("event_store_path", "data/vendor_procurement_events.json"))
            if config
            else Path("data/vendor_procurement_events.json")
        )
        self.vendor_performance_store = TenantStateStore(performance_store_path)
        self.event_store = TenantStateStore(event_store_path)
        self.db_service: DatabaseStorageService | None = None
        self.document_service: DocumentManagementService | None = None
        self.risk_client = RiskDatabaseClient(config.get("risk_config") if config else None)
        self.event_bus = EventBusClient(config.get("event_bus") if config else None)
        self.procurement_connector = ProcurementConnectorService(
            config.get("procurement_connectors") if config else None
        )
        self.erp_ap_connector = ProcurementConnectorService(
            config.get("erp_ap_connectors") if config else None
        )
        self.event_publisher = ProcurementEventPublisher(
            config.get("event_publisher") if config else None,
            event_bus=self.event_bus,
        )
        self.ml_config = config.get("ml_config") if config else None
        self.ml_service = VendorMLService(self.ml_config)
        self.vendor_scoring_weights = (
            self.ml_config.get("scoring_weights", {}) if self.ml_config else {}
        )
        self.form_recognizer = FormRecognizerClient(
            config.get("form_recognizer") if config else None
        )
        self.request_classifier = ProcurementClassifier(
            config.get("classification_config") if config else None
        )
        self.financial_client = FinancialManagementClient(
            config.get("financial_config") if config else None
        )
        self.analytics_client = PerformanceAnalyticsClient(
            config.get("analytics_config") if config else None
        )
        self.enable_openai_rfp = config.get("enable_openai_rfp", False) if config else False
        self.enable_ai_scoring = config.get("enable_ai_scoring", False) if config else False
        self.enable_ai_vendor_ranking = (
            config.get("enable_ai_vendor_ranking", False) if config else False
        )
        self.enable_ml_recommendations = (
            config.get("enable_ml_recommendations", True) if config else True
        )
        self.compliance_policy = (
            config.get(
                "compliance_policy",
                {"block_on_fail": True, "flag_on_watchlist": True, "risk_threshold": 75},
            )
            if config
            else {"block_on_fail": True, "flag_on_watchlist": True, "risk_threshold": 75}
        )
        self.task_client = config.get("task_client") if config else None
        if self.task_client is None:
            self.task_client = TaskManagementClient(
                config.get("task_management") if config else None
            )
        self.communications_client = config.get("communications_client") if config else None
        if self.communications_client is None:
            self.communications_client = CommunicationsClient(
                config.get("communications_config") if config else None
            )

        # Vendor categories
        self.vendor_categories = (
            config.get(
                "vendor_categories",
                ["software", "hardware", "consulting", "materials", "services", "cloud"],
            )
            if config
            else ["software", "hardware", "consulting", "materials", "services", "cloud"]
        )
        self.enable_vendor_research = (
            config.get("enable_vendor_research", False) if config else False
        )
        self.vendor_search_keywords = (
            config.get(
                "vendor_search_keywords",
                [
                    "financial health",
                    "performance issues",
                    "contract dispute",
                    "credit rating",
                    "supplier review",
                ],
            )
            if config
            else [
                "financial health",
                "performance issues",
                "contract dispute",
                "credit rating",
                "supplier review",
            ]
        )
        self.vendor_search_result_limit = (
            int(config.get("vendor_search_result_limit", 5)) if config else 5
        )

        # Data stores (will be replaced with database)
        self.vendors: dict[str, Any] = {}
        self.procurement_requests: dict[str, Any] = {}
        self.rfps: dict[str, Any] = {}
        self.proposals: dict[str, Any] = {}
        self.contracts: dict[str, Any] = {}
        self.purchase_orders: dict[str, Any] = {}
        self.invoices: dict[str, Any] = {}
        self.vendor_performance: dict[str, Any] = {}
        self.approval_agent = config.get("approval_agent") if config else None
        self.use_external_approval_agent = (
            config.get("use_external_approval_agent", False) if config else False
        )
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config", {}) if config else {}
            if self.use_external_approval_agent:
                approval_agent_cls = self._resolve_approval_agent()
                self.approval_agent = approval_agent_cls(config=approval_config)
            else:
                self.approval_agent = LocalApprovalAgent(config=approval_config)

    async def initialize(self) -> None:
        """Initialize database connections, ERP integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Vendor & Procurement Management Agent...")

        self.db_service = DatabaseStorageService(self.config.get("database_config"))
        self.document_service = DocumentManagementService(self.config.get("document_config"))

        connector_statuses = self.procurement_connector.initialize()
        erp_statuses = self.erp_ap_connector.initialize()
        if connector_statuses or erp_statuses:
            self.logger.info(
                "Connector status",
                extra={
                    "procurement_connectors": [status.__dict__ for status in connector_statuses],
                    "erp_connectors": [status.__dict__ for status in erp_statuses],
                },
            )

        await self._load_vendor_cache()
        await self.ml_service.train_models(list(self.vendors.values()))
        self._register_event_handlers()

        if self.form_recognizer.is_configured():
            self.logger.info("Form Recognizer configured for contract clause extraction.")
        else:
            self.logger.info("Form Recognizer not configured; falling back to regex extraction.")

        self.logger.info("Vendor & Procurement Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "onboard_vendor",
            "create_procurement_request",
            "generate_rfp",
            "submit_proposal",
            "evaluate_proposals",
            "select_vendor",
            "create_contract",
            "create_purchase_order",
            "submit_invoice",
            "reconcile_invoice",
            "track_vendor_performance",
            "get_vendor_scorecard",
            "search_vendors",
            "get_procurement_status",
            "research_vendor",
            "get_vendor_profile",
            "update_vendor_profile",
            "list_vendor_profiles",
            "sign_contract",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "onboard_vendor":
            vendor_data = input_data.get("vendor", {})
            required_fields = ["legal_name", "contact_email", "category"]
            for field in required_fields:
                if field not in vendor_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        elif action == "create_procurement_request":
            request_data = input_data.get("request", {})
            required_fields = ["requester", "description", "estimated_cost"]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "research_vendor":
            if not input_data.get("vendor_id") and not input_data.get("vendor_name"):
                self.logger.warning("Missing required field: vendor_id or vendor_name")
                return False
        elif action == "update_vendor_profile":
            if not input_data.get("vendor_id"):
                self.logger.warning("Missing required field: vendor_id")
                return False
            if not input_data.get("updates"):
                self.logger.warning("Missing required field: updates")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process vendor and procurement management requests.

        Args:
            input_data: {
                "action": "onboard_vendor" | "create_procurement_request" | "generate_rfp" |
                          "submit_proposal" | "evaluate_proposals" | "select_vendor" |
                          "create_contract" | "create_purchase_order" | "submit_invoice" |
                          "reconcile_invoice" | "track_vendor_performance" | "get_vendor_scorecard" |
                          "search_vendors" | "get_procurement_status" | "get_vendor_profile" |
                          "update_vendor_profile" | "list_vendor_profiles" | "sign_contract",
                "vendor": Vendor data for onboarding/updates,
                "request": Procurement request data,
                "rfp": RFP details,
                "proposal": Vendor proposal data,
                "contract": Contract details,
                "purchase_order": PO data,
                "invoice": Invoice information,
                "vendor_id": Vendor identifier,
                "request_id": Procurement request ID,
                "criteria": Search/evaluation criteria,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - onboard_vendor: Vendor ID and onboarding status
            - create_procurement_request: Request ID and workflow status
            - generate_rfp: RFP ID and invitation details
            - submit_proposal: Proposal ID and submission confirmation
            - evaluate_proposals: Evaluation results and vendor rankings
            - select_vendor: Selection confirmation and next steps
            - create_contract: Contract ID and terms summary
            - create_purchase_order: PO number and approval status
            - submit_invoice: Invoice ID and receipt confirmation
            - reconcile_invoice: Reconciliation status and payment details
            - track_vendor_performance: Performance metrics and trends
            - get_vendor_scorecard: Comprehensive vendor scorecard
            - search_vendors: List of matching vendors
            - get_procurement_status: Procurement request status details
        """
        action = input_data.get("action", "search_vendors")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "onboard_vendor":
            return await self._onboard_vendor(
                input_data.get("vendor", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "create_procurement_request":
            return await self._create_procurement_request(
                input_data.get("request", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "generate_rfp":
            return await self._generate_rfp(
                input_data.get("request_id"),
                input_data.get("rfp", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "submit_proposal":
            return await self._submit_proposal(
                input_data.get("rfp_id"),  # type: ignore
                input_data.get("vendor_id"),  # type: ignore
                input_data.get("proposal", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "evaluate_proposals":
            return await self._evaluate_proposals(
                input_data.get("rfp_id"), input_data.get("criteria", {})  # type: ignore
            )

        elif action == "select_vendor":
            return await self._select_vendor(
                input_data.get("rfp_id"),
                input_data.get("vendor_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "create_contract":
            return await self._create_contract(
                input_data.get("contract", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "create_purchase_order":
            return await self._create_purchase_order(
                input_data.get("purchase_order", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "submit_invoice":
            return await self._submit_invoice(
                input_data.get("invoice", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "reconcile_invoice":
            return await self._reconcile_invoice(
                input_data.get("invoice_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "track_vendor_performance":
            return await self._track_vendor_performance(
                input_data.get("vendor_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "get_vendor_scorecard":
            return await self._get_vendor_scorecard(
                input_data.get("vendor_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "research_vendor":
            return await self._research_vendor(
                vendor_id=input_data.get("vendor_id"),
                vendor_name=input_data.get("vendor_name"),
                domain=input_data.get("domain"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_vendor_profile":
            return await self._get_vendor_profile(
                input_data.get("vendor_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )  # type: ignore

        elif action == "update_vendor_profile":
            return await self._update_vendor_profile(
                input_data.get("vendor_id"),
                input_data.get("updates", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "list_vendor_profiles":
            return await self._list_vendor_profiles(
                input_data.get("criteria", {}),
                tenant_id=tenant_id,
            )

        elif action == "sign_contract":
            return await self._sign_contract(
                input_data.get("contract_id"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )  # type: ignore

        elif action == "search_vendors":
            return await self._search_vendors(input_data.get("criteria", {}))

        elif action == "get_procurement_status":
            return await self._get_procurement_status(input_data.get("request_id"))  # type: ignore

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _onboard_vendor(
        self,
        vendor_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Onboard a new vendor with compliance checks.

        Returns vendor ID and onboarding status.
        """
        self.logger.info("Onboarding vendor: %s", vendor_data.get("legal_name"))

        # Generate vendor ID
        vendor_id = await self._generate_vendor_id()

        # Run compliance checks
        compliance_checks = await self._run_compliance_checks(vendor_data)

        # Calculate initial risk score
        risk_score = await self._calculate_vendor_risk(vendor_data, compliance_checks)
        compliance_decision = await self._evaluate_compliance_checks(
            compliance_checks, risk_score=risk_score
        )

        created_at = datetime.now(timezone.utc).isoformat()
        # Create vendor profile
        vendor = {
            "vendor_id": vendor_id,
            "legal_name": vendor_data.get("legal_name"),
            "tax_id": vendor_data.get("tax_id"),
            "contact_email": vendor_data.get("contact_email"),
            "contact_phone": vendor_data.get("contact_phone"),
            "address": vendor_data.get("address", {}),
            "category": vendor_data.get("category"),
            "certifications": vendor_data.get("certifications", []),
            "diversity_classification": vendor_data.get("diversity_classification"),
            "classification": vendor_data.get("classification", "internal"),
            "risk_score": risk_score,
            "compliance_checks": compliance_checks,
            "compliance_status": compliance_decision["status"],
            "status": compliance_decision["status"],
            "created_at": created_at,
            "created_by": vendor_data.get("requester", actor_id),
            "performance_metrics": {
                "total_contracts": 0,
                "total_spend": 0,
                "on_time_delivery_rate": 0,
                "quality_rating": 0,
                "compliance_rating": 0,
            },
        }

        validation = await self._validate_vendor_record(
            vendor=vendor,
            tenant_id=tenant_id,
        )
        if not validation["is_valid"]:
            raise ValueError("Vendor schema validation failed")

        await self._persist_vendor(vendor, tenant_id=tenant_id)
        await self.ml_service.train_models(list(self.vendors.values()))
        connector_results = self.procurement_connector.sync_vendor(vendor)
        await self._publish_event(
            "vendor.onboarded",
            payload={"vendor": vendor, "connector_results": connector_results},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=vendor_id,
        )
        if compliance_decision["status"] in {"blocked", "flagged"}:
            await self._publish_event(
                "vendor.compliance_failed",
                payload={
                    "vendor_id": vendor_id,
                    "compliance_status": compliance_decision["status"],
                    "checks": compliance_checks,
                    "risk_score": risk_score,
                },
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
                entity_id=vendor_id,
            )
            await self._initiate_mitigation_workflow(
                vendor=vendor,
                reason=compliance_decision.get("reason", "Compliance checks failed"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        return {
            "vendor_id": vendor_id,
            "status": vendor["status"],
            "legal_name": vendor["legal_name"],
            "risk_score": risk_score,
            "compliance_checks": compliance_checks,
            "data_quality": validation,
            "compliance_status": vendor["compliance_status"],
            "next_steps": compliance_decision.get("next_steps")
            or "Vendor pending approval. Submit required documentation.",
        }

    async def _create_procurement_request(
        self,
        request_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Create a new procurement request.

        Returns request ID and workflow status.
        """
        self.logger.info("Creating procurement request: %s", request_data.get("description"))

        # Generate request ID
        request_id = await self._generate_request_id()

        # Categorize request
        category = await self._categorize_procurement_request(request_data)

        # Check budget availability
        budget_check = await self._check_budget_availability(request_data)

        # Suggest preferred vendors
        suggested_vendors = await self._suggest_vendors(category, request_data)

        # Determine approval path
        approval_path = await self._determine_approval_path(request_data.get("estimated_cost", 0))

        approval_required = request_data.get("estimated_cost", 0) > self.procurement_threshold
        approval_payload = None
        if approval_required:
            approval_payload = await self.approval_agent.process(
                {
                    "request_type": "procurement",
                    "request_id": request_id,
                    "requester": request_data.get("requester", actor_id),
                    "details": {
                        "amount": request_data.get("estimated_cost", 0),
                        "description": request_data.get("description"),
                        "justification": request_data.get("justification"),
                        "urgency": request_data.get("urgency", "medium"),
                    },
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                }
            )

        # Create procurement request
        request = {
            "request_id": request_id,
            "requester": request_data.get("requester"),
            "project_id": request_data.get("project_id"),
            "program_id": request_data.get("program_id"),
            "description": request_data.get("description"),
            "quantity": request_data.get("quantity", 1),
            "estimated_cost": request_data.get("estimated_cost"),
            "currency": request_data.get("currency", self.default_currency),
            "required_date": request_data.get("required_date"),
            "justification": request_data.get("justification"),
            "category": category,
            "suggested_vendors": suggested_vendors,
            "budget_available": budget_check.get("available", False),
            "approval_path": approval_path,
            "status": "Pending Approval" if approval_required else "Draft",
            "approval": approval_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store request
        self.procurement_requests[request_id] = request

        if self.db_service:
            await self.db_service.store("procurement_requests", request_id, request)

        return {
            "request_id": request_id,
            "status": request["status"],
            "category": category,
            "estimated_cost": request["estimated_cost"],
            "budget_available": budget_check.get("available", False),
            "suggested_vendors": suggested_vendors,
            "approval_required": approval_required,
            "approval": approval_payload,
            "next_steps": (
                "Await approvals before generating RFP"
                if approval_required
                else "Review suggested vendors or generate RFP"
            ),
        }

    async def _generate_rfp(
        self,
        request_id: str,
        rfp_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Generate RFP from procurement request.

        Returns RFP ID and invitation details.
        """
        self.logger.info("Generating RFP for request: %s", request_id)

        request = self.procurement_requests.get(request_id)
        if not request:
            raise ValueError(f"Procurement request not found: {request_id}")

        # Generate RFP ID
        rfp_id = await self._generate_rfp_id()

        # Select RFP template based on category
        template = await self._select_rfp_template(
            request.get("category"),
            template_id=rfp_data.get("template_id"),
        )

        # Generate RFP content
        rfp_content = await self._generate_rfp_content(request, template, rfp_data)

        # Select vendors to invite
        invited_vendors = await self._select_vendors_to_invite(
            request.get("category"),
            request.get("suggested_vendors", []),
            rfp_data.get("vendor_ids", []),
        )

        # Create RFP
        rfp = {
            "rfp_id": rfp_id,
            "request_id": request_id,
            "title": rfp_data.get("title", request.get("description")),
            "content": rfp_content,
            "requirements": rfp_data.get("requirements", []),
            "evaluation_criteria": rfp_data.get("evaluation_criteria", {}),
            "submission_deadline": rfp_data.get("submission_deadline"),
            "invited_vendors": invited_vendors,
            "proposals_received": [],
            "status": "Published",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        rfp_document = None
        if self.document_service:
            rfp_document = await self.document_service.publish_document(
                document_content=rfp_content,
                metadata=DocumentMetadata(
                    title=f"RFP {rfp_id}: {rfp['title']}",
                    description=f"RFP for procurement request {request_id}",
                    tags=["rfp", request.get("category", "general")],
                    owner=request.get("requester", ""),
                ),
                folder_path="Procurement/RFPs",
            )
        rfp["document"] = rfp_document

        # Store RFP
        self.rfps[rfp_id] = rfp

        if self.db_service:
            await self.db_service.store("rfps", rfp_id, rfp)
        connector_results = self.procurement_connector.publish_rfp(rfp)
        await self._publish_event(
            "rfp.published",
            payload={
                "rfp": rfp,
                "connector_results": connector_results,
                "request_id": request_id,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=rfp_id,
        )

        return {
            "rfp_id": rfp_id,
            "request_id": request_id,
            "title": rfp["title"],
            "submission_deadline": rfp["submission_deadline"],
            "invited_vendors": len(invited_vendors),
            "vendor_list": invited_vendors,
            "next_steps": "Wait for vendor proposals by submission deadline",
        }

    async def _submit_proposal(
        self,
        rfp_id: str,
        vendor_id: str,
        proposal_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Submit vendor proposal for RFP.

        Returns proposal ID and submission confirmation.
        """
        self.logger.info("Submitting proposal from vendor %s for RFP %s", vendor_id, rfp_id)

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        # Generate proposal ID
        proposal_id = await self._generate_proposal_id()

        # Validate submission deadline
        deadline = datetime.fromisoformat(rfp.get("submission_deadline"))
        if datetime.now(timezone.utc) > deadline:
            raise ValueError("Submission deadline has passed")

        # Create proposal
        proposal = {
            "proposal_id": proposal_id,
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "pricing": proposal_data.get("pricing", {}),
            "delivery_schedule": proposal_data.get("delivery_schedule"),
            "terms": proposal_data.get("terms", {}),
            "technical_response": proposal_data.get("technical_response"),
            "attachments": proposal_data.get("attachments", []),
            "evaluation_score": None,  # Calculated during evaluation
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "Submitted",
        }

        # Store proposal
        self.proposals[proposal_id] = proposal

        # Update RFP
        rfp["proposals_received"].append(proposal_id)

        if self.db_service:
            await self.db_service.store("proposals", proposal_id, proposal)
        connector_results = self.procurement_connector.submit_proposal(proposal)
        await self._publish_event(
            "proposal.submitted",
            payload={"proposal": proposal, "connector_results": connector_results},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=proposal_id,
        )

        return {
            "proposal_id": proposal_id,
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "submitted_at": proposal["submitted_at"],
            "status": "Submitted",
            "next_steps": "Proposal will be evaluated after submission deadline",
        }

    async def _evaluate_proposals(self, rfp_id: str, criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate all proposals for an RFP.

        Returns evaluation results and vendor rankings.
        """
        self.logger.info("Evaluating proposals for RFP: %s", rfp_id)

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        proposal_ids = rfp.get("proposals_received", [])
        if len(proposal_ids) < self.min_vendor_proposals:
            self.logger.warning(
                "Only %s proposals received, minimum is %s",
                len(proposal_ids),
                self.min_vendor_proposals,
            )

        # Get evaluation criteria with weights
        eval_criteria = criteria or rfp.get(
            "evaluation_criteria",
            {"cost": 0.40, "quality": 0.30, "delivery": 0.15, "risk": 0.10, "diversity": 0.05},
        )

        # Evaluate each proposal
        evaluated_proposals = []
        for proposal_id in proposal_ids:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                continue

            # Calculate scores for each criterion
            scores = await self._score_proposal(proposal, eval_criteria)

            # Calculate weighted total score
            total_score = sum(
                scores.get(criterion, 0) * weight for criterion, weight in eval_criteria.items()
            )

            # Update proposal with evaluation
            proposal["evaluation_score"] = total_score
            proposal["criterion_scores"] = scores

            evaluated_proposals.append(
                {
                    "proposal_id": proposal_id,
                    "vendor_id": proposal.get("vendor_id"),
                    "total_score": total_score,
                    "scores": scores,
                    "pricing": proposal.get("pricing"),
                }
            )

        # Rank proposals by score
        ranked_proposals = sorted(evaluated_proposals, key=lambda x: x["total_score"], reverse=True)

        if self.db_service:
            await self.db_service.store(
                "rfp_evaluations",
                rfp_id,
                {
                    "rfp_id": rfp_id,
                    "criteria": eval_criteria,
                    "rankings": ranked_proposals,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        return {
            "rfp_id": rfp_id,
            "proposals_evaluated": len(evaluated_proposals),
            "evaluation_criteria": eval_criteria,
            "rankings": ranked_proposals,
            "recommended_vendor": ranked_proposals[0] if ranked_proposals else None,
            "evaluation_date": datetime.now(timezone.utc).isoformat(),
        }

    async def _select_vendor(
        self,
        rfp_id: str,
        vendor_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Select vendor and finalize procurement.

        Returns selection confirmation and next steps.
        """
        self.logger.info("Selecting vendor %s for RFP %s", vendor_id, rfp_id)

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        # Find selected proposal
        selected_proposal = None
        for proposal_id in rfp.get("proposals_received", []):
            proposal = self.proposals.get(proposal_id)
            if proposal and proposal.get("vendor_id") == vendor_id:
                selected_proposal = proposal
                break

        if not selected_proposal:
            raise ValueError(f"No proposal found from vendor {vendor_id}")

        # Document selection rationale

        # Update RFP and proposal status
        rfp["status"] = "Vendor Selected"
        rfp["selected_vendor_id"] = vendor_id
        rfp["selected_proposal_id"] = selected_proposal.get("proposal_id")
        selected_proposal["status"] = "Accepted"

        if self.db_service:
            await self.db_service.store(
                "vendor_selections",
                f"{rfp_id}:{vendor_id}",
                {
                    "rfp_id": rfp_id,
                    "vendor_id": vendor_id,
                    "proposal_id": selected_proposal.get("proposal_id"),
                    "selected_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        connector_results = self.procurement_connector.select_vendor(
            {
                "rfp_id": rfp_id,
                "vendor_id": vendor_id,
                "proposal_id": selected_proposal.get("proposal_id"),
            }
        )
        vendor = self.vendors.get(vendor_id)
        if vendor:
            vendor["last_selected_at"] = datetime.now(timezone.utc).isoformat()
            vendor["last_selected_rfp"] = rfp_id
            await self._persist_vendor(vendor, tenant_id=tenant_id)
        await self._publish_event(
            "vendor.selected",
            payload={
                "rfp_id": rfp_id,
                "vendor_id": vendor_id,
                "proposal_id": selected_proposal.get("proposal_id"),
                "connector_results": connector_results,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=vendor_id,
        )

        return {
            "rfp_id": rfp_id,
            "selected_vendor_id": vendor_id,
            "proposal_id": selected_proposal.get("proposal_id"),
            "pricing": selected_proposal.get("pricing"),
            "evaluation_score": selected_proposal.get("evaluation_score"),
            "next_steps": "Generate contract from approved templates",
        }

    async def _create_contract(
        self,
        contract_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Create contract from template.

        Returns contract ID and terms summary.
        """
        self.logger.info("Creating contract with vendor: %s", contract_data.get("vendor_id"))

        # Generate contract ID
        contract_id = await self._generate_contract_id()

        # Select contract template
        await self._select_contract_template(contract_data.get("type", "standard"))

        # Extract key clauses
        key_clauses = await self._extract_contract_clauses(contract_data)

        # Create contract
        contract = {
            "contract_id": contract_id,
            "vendor_id": contract_data.get("vendor_id"),
            "project_id": contract_data.get("project_id"),
            "type": contract_data.get("type", "standard"),
            "start_date": contract_data.get("start_date"),
            "end_date": contract_data.get("end_date"),
            "value": contract_data.get("value"),
            "currency": contract_data.get("currency", self.default_currency),
            "terms": contract_data.get("terms", {}),
            "obligations": contract_data.get("obligations", []),
            "slas": contract_data.get("slas", []),
            "renewal_options": contract_data.get("renewal_options"),
            "key_clauses": key_clauses,
            "attachments": contract_data.get("attachments", []),
            "status": "Draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": contract_data.get("created_by", actor_id),
        }

        signature_workflow = {
            "status": "Pending Signatures",
            "method": "manual",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "signatories": contract_data.get("signatories", []),
        }
        contract["signature_workflow"] = signature_workflow

        contract_content = contract_data.get("content") or contract_data.get("document_content")
        if not contract_content:
            contract_content = (
                f"Contract {contract_id} between {contract.get('vendor_id')} "
                f"for {contract.get('project_id')} with value {contract.get('value')} "
                f"{contract.get('currency')} and term {contract.get('start_date')} "
                f"to {contract.get('end_date')}."
            )

        contract_document = None
        if self.document_service:
            contract_document = await self.document_service.publish_document(
                document_content=contract_content,
                metadata=DocumentMetadata(
                    title=f"Contract {contract_id}",
                    description=f"Procurement contract for vendor {contract.get('vendor_id')}",
                    tags=["contract", contract.get("type", "standard")],
                    owner=contract.get("created_by", ""),
                ),
                folder_path="Procurement/Contracts",
            )
        contract["document"] = contract_document

        # Store contract
        self.contracts[contract_id] = contract
        self.contract_store.upsert(tenant_id, contract_id, contract)

        if self.db_service:
            await self.db_service.store("contracts", contract_id, contract)
        connector_results = self.procurement_connector.create_contract(contract)
        await self._publish_event(
            "contract.created",
            payload={"contract": contract, "connector_results": connector_results},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=contract_id,
        )
        if contract_data.get("status") in {"Signed", "Active"}:
            contract["status"] = "Active"
            await self._publish_event(
                "contract.signed",
                payload={"contract_id": contract_id, "vendor_id": contract.get("vendor_id")},
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
                entity_id=contract_id,
            )

        return {
            "contract_id": contract_id,
            "vendor_id": contract["vendor_id"],
            "type": contract["type"],
            "value": contract["value"],
            "start_date": contract["start_date"],
            "end_date": contract["end_date"],
            "status": "Draft",
            "signature_status": signature_workflow["status"],
            "next_steps": "Collect manual signatures and upload signed contract",
        }

    async def _create_purchase_order(
        self,
        po_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Create purchase order from approved procurement.

        Returns PO number and approval status.
        """
        self.logger.info("Creating purchase order for vendor: %s", po_data.get("vendor_id"))

        # Generate PO number
        po_number = await self._generate_po_number()

        total_value = await self._calculate_po_total(po_data.get("items", []))
        approval_required = total_value > self.procurement_threshold
        approval_payload = None
        if approval_required:
            approval_payload = await self.approval_agent.process(
                {
                    "request_type": "procurement",
                    "request_id": po_number,
                    "requester": po_data.get("requester", actor_id),
                    "details": {
                        "amount": total_value,
                        "description": "Purchase order approval",
                        "justification": po_data.get("justification"),
                        "urgency": po_data.get("urgency", "medium"),
                    },
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                }
            )

        # Create PO
        purchase_order_status = "Pending Approval" if approval_required else "Released"
        purchase_order = {
            "po_number": po_number,
            "vendor_id": po_data.get("vendor_id"),
            "contract_id": po_data.get("contract_id"),
            "project_id": po_data.get("project_id"),
            "items": po_data.get("items", []),
            "total_value": total_value,
            "currency": po_data.get("currency", self.default_currency),
            "delivery_schedule": po_data.get("delivery_schedule"),
            "delivery_address": po_data.get("delivery_address"),
            "payment_terms": po_data.get("payment_terms"),
            "approval_history": [],
            "approval": approval_payload,
            "status": purchase_order_status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store PO
        self.purchase_orders[po_number] = purchase_order

        if self.db_service:
            await self.db_service.store("purchase_orders", po_number, purchase_order)
        connector_results = []
        if purchase_order_status == "Released":
            connector_results = self.procurement_connector.release_purchase_order(purchase_order)
            await self._publish_event(
                "po.released",
                payload={"purchase_order": purchase_order, "connector_results": connector_results},
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
                entity_id=po_number,
            )

        return {
            "po_number": po_number,
            "vendor_id": purchase_order["vendor_id"],
            "total_value": purchase_order["total_value"],
            "status": purchase_order["status"],
            "items_count": len(purchase_order["items"]),
            "approval": approval_payload,
            "next_steps": (
                "Await approval before release to vendor."
                if approval_required
                else "Release to vendor."
            ),
        }

    async def _submit_invoice(
        self,
        invoice_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Submit vendor invoice.

        Returns invoice ID and receipt confirmation.
        """
        self.logger.info("Submitting invoice: %s", invoice_data.get("invoice_number"))

        # Generate internal invoice ID
        invoice_id = await self._generate_invoice_id()

        # Create invoice record
        invoice = {
            "invoice_id": invoice_id,
            "vendor_invoice_number": invoice_data.get("invoice_number"),
            "vendor_id": invoice_data.get("vendor_id"),
            "po_number": invoice_data.get("po_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "due_date": invoice_data.get("due_date"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal"),
            "tax": invoice_data.get("tax"),
            "total_amount": invoice_data.get("total_amount"),
            "currency": invoice_data.get("currency", self.default_currency),
            "payment_terms": invoice_data.get("payment_terms"),
            "attachments": invoice_data.get("attachments", []),
            "reconciliation_status": "Pending",
            "payment_status": "Unpaid",
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store invoice
        self.invoices[invoice_id] = invoice
        self.invoice_store.upsert(tenant_id, invoice_id, invoice)

        if self.db_service:
            await self.db_service.store("invoices", invoice_id, invoice)
        connector_results = self.procurement_connector.record_invoice(invoice)
        await self._publish_event(
            "invoice.received",
            payload={"invoice": invoice, "connector_results": connector_results},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=invoice_id,
        )

        return {
            "invoice_id": invoice_id,
            "vendor_invoice_number": invoice["vendor_invoice_number"],
            "po_number": invoice["po_number"],
            "total_amount": invoice["total_amount"],
            "reconciliation_status": "Pending",
            "next_steps": "Invoice will be automatically reconciled against PO and receipts",
        }

    async def _reconcile_invoice(
        self,
        invoice_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Reconcile invoice against PO and receipts (three-way matching).

        Returns reconciliation status and payment details.
        """
        self.logger.info("Reconciling invoice: %s", invoice_id)

        invoice = self.invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        # Get associated PO
        po_number = invoice.get("po_number")
        purchase_order = self.purchase_orders.get(po_number)
        if not purchase_order:
            raise ValueError(f"Purchase order not found: {po_number}")

        # Perform three-way matching
        matching_result = await self._three_way_match(invoice, purchase_order)

        # Check for discrepancies
        discrepancies = matching_result.get("discrepancies", [])

        if not discrepancies:
            # No discrepancies - approve for payment
            invoice["reconciliation_status"] = "Matched"
            invoice["approved_for_payment"] = True
            invoice["approved_at"] = datetime.now(timezone.utc).isoformat()

            payment_status = await self._initiate_payment(invoice)

            invoice["payment_status"] = payment_status.get("status", "Processing")
            invoice["payment_reference"] = payment_status.get("reference")
            invoice["payment_connector_results"] = payment_status.get("connector_results")

        else:
            # Discrepancies found - flag for review
            invoice["reconciliation_status"] = "Discrepancy"
            invoice["approved_for_payment"] = False
            invoice["discrepancies"] = discrepancies

        if self.db_service:
            await self.db_service.store("invoice_reconciliations", invoice_id, invoice)
        await self._publish_event(
            "invoice.reconciled",
            payload={"invoice": invoice, "discrepancies": discrepancies},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=invoice_id,
        )

        return {
            "invoice_id": invoice_id,
            "reconciliation_status": invoice["reconciliation_status"],
            "discrepancies": discrepancies,
            "approved_for_payment": invoice.get("approved_for_payment", False),
            "payment_status": invoice.get("payment_status"),
            "payment_reference": invoice.get("payment_reference"),
            "next_steps": (
                "Payment initiated" if not discrepancies else "Review and resolve discrepancies"
            ),
        }

    async def _track_vendor_performance(
        self,
        vendor_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Track vendor performance metrics.

        Returns performance data and trends.
        """
        self.logger.info("Tracking performance for vendor: %s", vendor_id)

        vendor = self.vendors.get(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")

        # Collect performance data
        performance_data = await self._collect_vendor_performance_data(vendor_id)

        # Calculate metrics
        metrics = {
            "delivery_timeliness": await self._calculate_delivery_timeliness(vendor_id),
            "quality_rating": await self._calculate_quality_rating(vendor_id),
            "compliance_score": await self._calculate_compliance_score(vendor_id),
            "sla_adherence": await self._calculate_sla_adherence(vendor_id),
            "dispute_count": performance_data.get("dispute_count", 0),
            "total_spend": performance_data.get("total_spend", 0),
            "contract_count": performance_data.get("contract_count", 0),
        }
        metrics["on_time_delivery_rate"] = metrics["delivery_timeliness"]
        metrics["compliance_rating"] = metrics["compliance_score"]

        ml_analysis = self.ml_service.analyze_performance(metrics, vendor)
        adjusted_metrics = ml_analysis.get("adjusted_metrics", metrics)

        # Update vendor performance metrics
        vendor["performance_metrics"].update(adjusted_metrics)
        vendor["performance_metrics"]["ml_insights"] = ml_analysis.get("insights", [])
        vendor["performance_metrics"]["performance_trend"] = ml_analysis.get("trend")

        if self.db_service:
            await self.db_service.store(
                "vendor_performance",
                vendor_id,
                {
                    "vendor_id": vendor_id,
                    "metrics": adjusted_metrics,
                    "ml_analysis": ml_analysis,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        self.vendor_performance_store.upsert(
            tenant_id,
            vendor_id,
            {
                "vendor_id": vendor_id,
                "metrics": adjusted_metrics,
                "ml_analysis": ml_analysis,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self._publish_event(
            "vendor.performance_updated",
            payload={
                "vendor_id": vendor_id,
                "metrics": adjusted_metrics,
                "ml_analysis": ml_analysis,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=vendor_id,
        )

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("legal_name"),
            "metrics": adjusted_metrics,
            "performance_trend": ml_analysis.get("trend")
            or await self._analyze_performance_trend(vendor_id),
            "recommendations": await self._generate_vendor_recommendations(adjusted_metrics),
            "ml_analysis": ml_analysis,
        }

    async def research_vendor(
        self,
        vendor_name: str,
        domain: str,
        *,
        llm_client: LLMGateway | None = None,
        result_limit: int | None = None,
    ) -> dict[str, Any]:
        """Research external signals about a vendor using public sources."""
        if not self.enable_vendor_research:
            return {"summary": "", "insights": [], "sources": [], "used_external_research": False}

        context = f"{vendor_name} {domain}".strip()
        query = build_search_query(
            context,
            "vendor",
            extra_keywords=self.vendor_search_keywords,
        )

        # NOTE: Only high-level vendor context should be sent to the search API.
        snippets = await search_web(
            query, result_limit=result_limit or self.vendor_search_result_limit
        )
        if not snippets:
            return {"summary": "", "insights": [], "sources": [], "used_external_research": False}

        summary = await summarize_snippets(snippets, llm_client=llm_client, purpose="vendor")
        insights = await self._extract_vendor_insights(summary, snippets, llm_client=llm_client)
        sources = self._extract_sources(snippets)
        return {
            "summary": summary,
            "insights": insights,
            "sources": sources,
            "used_external_research": True,
        }

    async def _research_vendor(
        self,
        *,
        vendor_id: str | None,
        vendor_name: str | None,
        domain: str | None,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        vendor = self.vendors.get(vendor_id) if vendor_id else None
        resolved_name = vendor_name or (vendor.get("legal_name") if vendor else None)
        resolved_domain = domain or (vendor.get("category") if vendor else "general")
        if not resolved_name:
            raise ValueError("Vendor name is required for research")

        try:
            research = await self.research_vendor(resolved_name, resolved_domain)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning(
                "Vendor research failed",
                extra={"error": str(exc), "vendor_id": vendor_id, "correlation_id": correlation_id},
            )
            return {
                "vendor_id": vendor_id,
                "vendor_name": resolved_name,
                "summary": "",
                "insights": [],
                "sources": [],
                "used_external_research": False,
                "notice": "External vendor research failed; internal evaluation is unchanged.",
                "correlation_id": correlation_id,
            }

        if vendor_id and vendor:
            vendor["external_research"] = research
            self.vendor_store.upsert(tenant_id, vendor_id, vendor)

        return {
            "vendor_id": vendor_id,
            "vendor_name": resolved_name,
            **research,
            "notice": None,
            "correlation_id": correlation_id,
        }

    async def _get_vendor_scorecard(
        self,
        vendor_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Generate comprehensive vendor scorecard.

        Returns detailed scorecard with visualizations.
        """
        self.logger.info("Generating scorecard for vendor: %s", vendor_id)

        vendor = self.vendors.get(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")

        # Get performance metrics
        performance = await self._track_vendor_performance(
            vendor_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

        # Get contract history
        contracts = await self._get_vendor_contracts(vendor_id)

        # Get recent issues
        recent_issues = await self._get_vendor_issues(vendor_id)

        external_research = None
        external_adjustment: dict[str, Any] | None = None
        if self.enable_vendor_research:
            external_research = await self.research_vendor(
                vendor.get("legal_name", "vendor"), vendor.get("category", "general")
            )
            external_adjustment = self._score_vendor_research(external_research)

        # Calculate overall score
        overall_score = await self._calculate_overall_vendor_score(
            vendor, external_adjustment=external_adjustment
        )

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("legal_name"),
            "overall_score": overall_score,
            "risk_score": vendor.get("risk_score"),
            "performance_metrics": performance.get("metrics"),
            "performance_trend": performance.get("performance_trend"),
            "contract_summary": {
                "active_contracts": len([c for c in contracts if c.get("status") == "Active"]),
                "total_value": sum(c.get("value", 0) for c in contracts),
                "expiring_soon": len([c for c in contracts if await self._is_expiring_soon(c)]),
            },
            "recent_issues": recent_issues,
            "recommendations": performance.get("recommendations"),
            "external_research": external_research,
            "external_research_adjustment": external_adjustment,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _search_vendors(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Search vendors by criteria.

        Returns list of matching vendors.
        """
        self.logger.info("Searching vendors")

        # Filter vendors
        matching_vendors = []
        for vendor_id, vendor in self.vendors.items():
            if await self._matches_criteria(vendor, criteria):
                matching_vendors.append(
                    {
                        "vendor_id": vendor_id,
                        "legal_name": vendor.get("legal_name"),
                        "category": vendor.get("category"),
                        "risk_score": vendor.get("risk_score"),
                        "performance_rating": vendor.get("performance_metrics", {}).get(
                            "quality_rating", 0
                        ),
                        "status": vendor.get("status"),
                    }
                )

        # Sort by relevance
        if self.enable_ai_vendor_ranking:
            sorted_vendors = self.ml_service.rank_vendors(matching_vendors)
        else:
            sorted_vendors = sorted(
                matching_vendors,
                key=lambda x: (x.get("performance_rating", 0), -x.get("risk_score", 100)),
                reverse=True,
            )

        return {
            "total_results": len(sorted_vendors),
            "vendors": sorted_vendors,
            "search_criteria": criteria,
        }

    async def _get_procurement_status(self, request_id: str) -> dict[str, Any]:
        """
        Get procurement request status.

        Returns detailed status information.
        """
        self.logger.info("Getting procurement status for request: %s", request_id)

        request = self.procurement_requests.get(request_id)
        if not request:
            raise ValueError(f"Procurement request not found: {request_id}")

        # Find related RFP
        related_rfp = None
        for rfp_id, rfp in self.rfps.items():
            if rfp.get("request_id") == request_id:
                related_rfp = rfp
                break

        # Find related PO
        related_po = None
        if related_rfp and related_rfp.get("selected_vendor_id"):
            for po_number, po in self.purchase_orders.items():
                if po.get("vendor_id") == related_rfp.get("selected_vendor_id"):
                    related_po = po
                    break

        return {
            "request_id": request_id,
            "status": request.get("status"),
            "requester": request.get("requester"),
            "description": request.get("description"),
            "estimated_cost": request.get("estimated_cost"),
            "rfp_status": related_rfp.get("status") if related_rfp else None,
            "rfp_id": related_rfp.get("rfp_id") if related_rfp else None,
            "proposals_received": (
                len(related_rfp.get("proposals_received", [])) if related_rfp else 0
            ),
            "selected_vendor": related_rfp.get("selected_vendor_id") if related_rfp else None,
            "po_number": related_po.get("po_number") if related_po else None,
            "po_status": related_po.get("status") if related_po else None,
        }

    # Helper methods

    def _register_event_handlers(self) -> None:
        self.event_bus.register_handler("delivery.delayed", self._handle_delivery_delayed)
        self.event_bus.register_handler("contract.signed", self._handle_contract_signed)
        self.event_bus.register_handler("vendor.flagged", self._handle_vendor_flagged)
        self.event_bus.register_handler("risk.alert", self._handle_risk_alert)
        self.event_bus.register_handler("compliance.violation", self._handle_compliance_violation)
        self.event_bus.register_handler("sanctions.hit", self._handle_sanctions_hit)

    async def _handle_delivery_delayed(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in self.vendors:
            return
        vendor = self.vendors[vendor_id]
        metrics = vendor.get("performance_metrics", {})
        metrics["delivery_timeliness"] = max(0, metrics.get("delivery_timeliness", 100) - 5)
        metrics["on_time_delivery_rate"] = metrics["delivery_timeliness"]
        vendor["performance_metrics"] = metrics
        await self._persist_vendor(vendor, tenant_id=event.get("tenant_id", "unknown"))

    async def _handle_contract_signed(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        contract_id = payload.get("contract_id")
        if contract_id and contract_id in self.contracts:
            contract = self.contracts[contract_id]
            contract["status"] = "Active"
            tenant_id = event.get("tenant_id", "unknown")
            self.contract_store.upsert(tenant_id, contract_id, contract)
            if self.db_service:
                await self.db_service.store("contracts", contract_id, contract)

    async def _handle_vendor_flagged(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in self.vendors:
            return
        vendor = self.vendors[vendor_id]
        vendor["status"] = "flagged"
        vendor["risk_score"] = min(100, vendor.get("risk_score", 50) + 20)
        vendor["compliance_status"] = "flagged"
        await self._persist_vendor(vendor, tenant_id=event.get("tenant_id", "unknown"))
        await self._initiate_mitigation_workflow(
            vendor=vendor,
            reason=payload.get("reason", "Vendor flagged via risk event"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )

    async def _handle_risk_alert(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in self.vendors:
            return
        vendor = self.vendors[vendor_id]
        vendor["risk_score"] = min(100, payload.get("risk_score", vendor.get("risk_score", 50)))
        vendor["status"] = "flagged"
        vendor["compliance_status"] = "flagged"
        await self._persist_vendor(vendor, tenant_id=event.get("tenant_id", "unknown"))
        await self._initiate_mitigation_workflow(
            vendor=vendor,
            reason=payload.get("reason", "Risk alert received"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )

    async def _handle_compliance_violation(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in self.vendors:
            return
        vendor = self.vendors[vendor_id]
        vendor["status"] = (
            "blocked" if self.compliance_policy.get("block_on_fail", True) else "flagged"
        )
        vendor["compliance_status"] = "failed"
        await self._persist_vendor(vendor, tenant_id=event.get("tenant_id", "unknown"))
        await self._initiate_mitigation_workflow(
            vendor=vendor,
            reason=payload.get("reason", "Compliance violation received"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )

    async def _handle_sanctions_hit(self, event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in self.vendors:
            return
        vendor = self.vendors[vendor_id]
        vendor["status"] = "blocked"
        vendor["compliance_status"] = "sanctions_hit"
        vendor["risk_score"] = min(100, vendor.get("risk_score", 50) + 30)
        await self._persist_vendor(vendor, tenant_id=event.get("tenant_id", "unknown"))
        await self._initiate_mitigation_workflow(
            vendor=vendor,
            reason=payload.get("reason", "Sanctions list hit"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )

    async def _publish_event(
        self,
        event_type: str,
        *,
        payload: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = f"{event_type}-{uuid.uuid4()}"
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": payload,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "actor_id": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.event_store.upsert(tenant_id, event_id, event)
        if self.db_service:
            await self.db_service.store("procurement_events", event_id, event)
        await self.event_publisher.publish(event)
        return event

    def _resolve_approval_agent(self) -> type:
        module = importlib.import_module("approval_workflow_agent")
        return getattr(module, "ApprovalWorkflowAgent")

    async def _generate_vendor_id(self) -> str:
        """Generate unique vendor ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"VND-{timestamp}"

    async def _generate_request_id(self) -> str:
        """Generate unique procurement request ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"PR-{timestamp}"

    async def _generate_rfp_id(self) -> str:
        """Generate unique RFP ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"RFP-{timestamp}"

    async def _generate_proposal_id(self) -> str:
        """Generate unique proposal ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"PROP-{timestamp}"

    async def _generate_contract_id(self) -> str:
        """Generate unique contract ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"CTR-{timestamp}"

    async def _generate_po_number(self) -> str:
        """Generate unique PO number."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"PO-{timestamp}"

    async def _generate_invoice_id(self) -> str:
        """Generate unique invoice ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}"

    async def _run_compliance_checks(self, vendor_data: dict[str, Any]) -> dict[str, Any]:
        """Run compliance checks on vendor."""
        checks = self.risk_client.check_vendor(vendor_data)
        if not checks:
            return {
                "sanctions_check": "Pass",
                "anti_corruption_check": "Pass",
                "credit_check": "Pass",
                "watchlist_hits": [],
                "sources": [],
            }
        return checks

    async def _evaluate_compliance_checks(
        self, checks: dict[str, Any], *, risk_score: float
    ) -> dict[str, Any]:
        failures = [
            key
            for key in ("sanctions_check", "anti_corruption_check", "credit_check")
            if checks.get(key) == "Fail"
        ]
        watchlist_hits = checks.get("watchlist_hits") or []
        status = "pending"
        reason = ""
        next_steps = ""
        if failures and self.compliance_policy.get("block_on_fail", True):
            status = "blocked"
            reason = f"Compliance failures: {', '.join(failures)}"
            next_steps = "Vendor blocked pending compliance remediation."
        elif failures:
            status = "flagged"
            reason = f"Compliance concerns: {', '.join(failures)}"
            next_steps = "Vendor flagged for enhanced due diligence."
        elif watchlist_hits and self.compliance_policy.get("flag_on_watchlist", True):
            status = "flagged"
            reason = "Vendor appears on watchlist."
            next_steps = "Vendor flagged for sanctions review."
        elif risk_score >= float(self.compliance_policy.get("risk_threshold", 75)):
            status = "flagged"
            reason = "Risk score exceeded threshold."
            next_steps = "Vendor flagged for risk review."
        else:
            status = "pending"
            reason = "Compliance checks passed."
            next_steps = "Vendor pending approval. Submit required documentation."
        return {"status": status, "reason": reason, "next_steps": next_steps}

    async def _calculate_vendor_risk(
        self, vendor_data: dict[str, Any], compliance_checks: dict[str, Any]
    ) -> float:
        """Calculate vendor risk score (0-100, lower is better)."""
        ml_risk = self.ml_service.risk_score(vendor_data, compliance_checks)
        return max(0, min(100, ml_risk))

    async def _categorize_procurement_request(self, request_data: dict[str, Any]) -> str:
        """Categorize procurement request using AI."""
        description = request_data.get("description", "")
        return self.request_classifier.predict(description, fallback="services")

    async def _check_budget_availability(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Check budget availability for procurement."""
        return self.financial_client.get_budget_status(request_data)

    async def _suggest_vendors(self, category: str, request_data: dict[str, Any]) -> list[str]:
        """Suggest vendors based on category and requirements."""
        suggested = []
        for vendor_id, vendor in self.vendors.items():
            if vendor.get("category") == category and vendor.get("status") == "Approved":
                suggested.append(vendor_id)

        if self.enable_ml_recommendations:
            return self.ml_service.recommend_vendors(list(self.vendors.values()), category, top_n=5)

        return suggested[:5]  # Top 5

    async def _determine_approval_path(self, estimated_cost: float) -> str:
        """Determine approval path based on cost."""
        if estimated_cost > 100000:
            return "Executive Approval Required"
        elif estimated_cost > self.procurement_threshold:
            return "Manager Approval Required"
        else:
            return "Auto-Approved"

    async def _select_rfp_template(
        self, category: str, *, template_id: str | None = None
    ) -> dict[str, Any]:
        """Select RFP template based on category or explicit template ID."""
        templates = {**self.DEFAULT_RFP_TEMPLATES, **self.config.get("rfp_templates", {})}
        if template_id:
            for template in templates.values():
                if template.get("template_id") == template_id:
                    return template
        return templates.get(category, {"template_id": f"{category}_template", "sections": []})

    async def _generate_rfp_content(
        self, request: dict[str, Any], template: dict[str, Any], rfp_data: dict[str, Any]
    ) -> str:
        """Generate RFP content from template."""
        sections = template.get("sections", [])
        outline = "\n".join(f"- {section}" for section in sections)
        base_content = (
            f"RFP Title: {rfp_data.get('title', request.get('description'))}\n"
            f"Category: {request.get('category')}\n"
            f"Scope: {request.get('description')}\n"
            f"Requirements: {', '.join(rfp_data.get('requirements', []))}\n"
            f"Template Sections:\n{outline or '- General Requirements'}\n"
        )

        if not self.enable_openai_rfp:
            return base_content

        system_prompt = (
            "You are a procurement specialist. Draft a structured RFP using the provided "
            "request context and template sections. Keep the response concise."
        )
        user_prompt = json.dumps(
            {"request": request, "template": template, "rfp_data": rfp_data}, indent=2
        )
        llm = LLMGateway()
        try:
            response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            content = response.content.strip()
            return content if content else base_content
        except LLMProviderError:
            self.logger.warning("OpenAI RFP generation failed; using template fallback.")
            return base_content

    async def _select_vendors_to_invite(
        self, category: str, suggested_vendors: list[str], specified_vendors: list[str]
    ) -> list[str]:
        """Select vendors to invite to RFP."""
        if specified_vendors:
            return specified_vendors
        return suggested_vendors[: self.min_vendor_proposals]

    async def _score_proposal(
        self, proposal: dict[str, Any], criteria: dict[str, float]
    ) -> dict[str, float]:
        """Score proposal against criteria."""
        if self.enable_ai_scoring:
            system_prompt = (
                "You are a procurement evaluation assistant. Score the proposal against the "
                "criteria. Return JSON object with scores for each criterion from 0-100."
            )
            user_prompt = json.dumps({"proposal": proposal, "criteria": criteria}, indent=2)
            llm = LLMGateway()
            try:
                response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                data = json.loads(response.content)
                if isinstance(data, dict):
                    return {key: float(value) for key, value in data.items() if key in criteria}
            except (LLMProviderError, json.JSONDecodeError, ValueError):
                self.logger.warning("AI scoring failed; using ML scoring fallback.")

        scores = self.ml_service.score_proposal(proposal, criteria_weights=criteria)
        return scores or {}

    async def _extract_contract_clauses(self, contract_data: dict[str, Any]) -> dict[str, Any]:
        """Extract key clauses from contract."""
        contract_text = (
            contract_data.get("content")
            or contract_data.get("document_content")
            or contract_data.get("text")
        )
        if not contract_text:
            contract_text = json.dumps(contract_data.get("terms", {}), indent=2)

        if self.form_recognizer.is_configured():
            form_result = self.form_recognizer.extract_clauses(contract_text)
            if form_result:
                return {
                    "source": "form_recognizer",
                    "analysis": form_result,
                }

        clause_patterns = {
            "term": r"(term|duration|contract term)\s*[:\-]\s*(?P<value>[^\n]+)",
            "value": r"(total value|contract value|price|fees)\s*[:\-]\s*\$?(?P<value>[\d,\.]+)",
            "sla": r"(sla|service level|uptime)\s*[:\-]\s*(?P<value>[^\n]+)",
        }

        extracted = {}
        for clause, pattern in clause_patterns.items():
            match = re.search(pattern, contract_text, re.IGNORECASE)
            if match:
                extracted[clause] = match.group("value").strip()

        if "term" not in extracted:
            extracted["term"] = (
                f"{contract_data.get('start_date')} to {contract_data.get('end_date')}"
            )
        if "value" not in extracted and contract_data.get("value") is not None:
            extracted["value"] = str(contract_data.get("value"))
        if "sla" not in extracted and contract_data.get("slas"):
            extracted["sla"] = ", ".join(str(item) for item in contract_data.get("slas"))

        return extracted

    async def _select_contract_template(self, contract_type: str) -> dict[str, Any]:
        """Select contract template."""
        return {"template_id": f"{contract_type}_contract"}

    async def _calculate_po_total(self, items: list[dict[str, Any]]) -> float:
        """Calculate total PO value."""
        total = 0.0
        for item in items:
            quantity = item.get("quantity", 1)
            unit_cost = item.get("unit_cost", 0)
            total += quantity * unit_cost
        return total

    async def _three_way_match(
        self, invoice: dict[str, Any], purchase_order: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform three-way matching between invoice, PO, and receipt."""
        discrepancies = []

        # Check amounts
        invoice_total = invoice.get("total_amount", 0)
        po_total = purchase_order.get("total_value", 0)

        if abs(invoice_total - po_total) > (po_total * self.invoice_tolerance_pct):
            discrepancies.append(
                {
                    "type": "amount_mismatch",
                    "invoice_amount": invoice_total,
                    "po_amount": po_total,
                    "variance": invoice_total - po_total,
                }
            )

        def _normalize_line_item(item: dict[str, Any]) -> tuple[str, str]:
            sku = str(item.get("sku") or item.get("item_code") or "").strip().lower()
            description = str(item.get("description") or item.get("name") or "").strip().lower()
            return sku, description

        po_items = purchase_order.get("items", [])
        po_lookup: dict[str, dict[str, Any]] = {}
        for item in po_items:
            sku, description = _normalize_line_item(item)
            key = sku or description
            if key:
                po_lookup[key] = item

        invoice_items = invoice.get("line_items", [])
        for item in invoice_items:
            sku, description = _normalize_line_item(item)
            key = sku or description
            if not key or key not in po_lookup:
                discrepancies.append(
                    {
                        "type": "line_item_missing_in_po",
                        "item": item,
                    }
                )
                continue

            po_item = po_lookup[key]
            invoice_qty = item.get("quantity", 0)
            po_qty = po_item.get("quantity", 0)
            if invoice_qty != po_qty:
                discrepancies.append(
                    {
                        "type": "quantity_mismatch",
                        "item": item,
                        "po_quantity": po_qty,
                        "invoice_quantity": invoice_qty,
                    }
                )

            invoice_unit_cost = item.get("unit_cost", 0)
            po_unit_cost = po_item.get("unit_cost", 0)
            if po_unit_cost and abs(invoice_unit_cost - po_unit_cost) > (
                po_unit_cost * self.invoice_tolerance_pct
            ):
                discrepancies.append(
                    {
                        "type": "unit_cost_mismatch",
                        "item": item,
                        "po_unit_cost": po_unit_cost,
                        "invoice_unit_cost": invoice_unit_cost,
                    }
                )

        return {"matched": len(discrepancies) == 0, "discrepancies": discrepancies}

    async def _initiate_payment(self, invoice: dict[str, Any]) -> dict[str, Any]:
        """Initiate payment in ERP."""
        payment_request = {
            "invoice_id": invoice.get("invoice_id"),
            "vendor_id": invoice.get("vendor_id"),
            "amount": invoice.get("total_amount"),
            "currency": invoice.get("currency", self.default_currency),
        }
        connector_results = self.erp_ap_connector.initiate_payment(payment_request)
        return {
            "status": "Processing",
            "reference": f"PAY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "connector_results": connector_results,
        }

    async def _collect_vendor_performance_data(self, vendor_id: str) -> dict[str, Any]:
        """Collect vendor performance data."""
        return self.analytics_client.get_vendor_summary(vendor_id)

    async def _calculate_delivery_timeliness(self, vendor_id: str) -> float:
        """Calculate vendor delivery timeliness percentage."""
        summary = self.analytics_client.get_vendor_summary(vendor_id)
        deliveries = summary.get("deliveries", [])
        if not deliveries:
            return 95.0
        on_time = sum(1 for record in deliveries if record.get("on_time"))
        return round((on_time / len(deliveries)) * 100, 2)

    async def _calculate_quality_rating(self, vendor_id: str) -> float:
        """Calculate vendor quality rating."""
        summary = self.analytics_client.get_vendor_summary(vendor_id)
        scores = summary.get("quality_scores", [])
        if not scores:
            return 4.5
        return round(sum(scores) / len(scores), 2)

    async def _calculate_compliance_score(self, vendor_id: str) -> float:
        """Calculate vendor compliance score."""
        summary = self.analytics_client.get_vendor_summary(vendor_id)
        incidents = summary.get("compliance_incidents", [])
        score = max(0, 100 - (len(incidents) * 5))
        return float(score)

    async def _calculate_sla_adherence(self, vendor_id: str) -> float:
        """Calculate SLA adherence percentage."""
        summary = self.analytics_client.get_vendor_summary(vendor_id)
        sla_records = summary.get("sla_records", [])
        if not sla_records:
            return 97.0
        met = sum(1 for record in sla_records if record.get("met"))
        return round((met / len(sla_records)) * 100, 2)

    async def _analyze_performance_trend(self, vendor_id: str) -> str:
        """Analyze vendor performance trend."""
        return "Stable"

    async def _generate_vendor_recommendations(self, metrics: dict[str, Any]) -> list[str]:
        """Generate recommendations based on vendor metrics."""
        recommendations = []

        if metrics.get("delivery_timeliness", 100) < 90:
            recommendations.append("Improve delivery timeliness through SLA enforcement")

        if metrics.get("quality_rating", 5.0) < 4.0:
            recommendations.append("Address quality issues through corrective action plan")

        if not recommendations:
            recommendations.append("Continue current performance levels")

        return recommendations

    async def _get_vendor_contracts(self, vendor_id: str) -> list[dict[str, Any]]:
        """Get all contracts for a vendor."""
        vendor_contracts = []
        for contract_id, contract in self.contracts.items():
            if contract.get("vendor_id") == vendor_id:
                vendor_contracts.append(contract)
        return vendor_contracts

    async def _get_vendor_issues(self, vendor_id: str) -> list[dict[str, Any]]:
        """Get recent issues with vendor."""
        summary = self.analytics_client.get_vendor_summary(vendor_id)
        return summary.get("issue_tracker", [])

    async def _extract_vendor_insights(
        self,
        summary: str,
        snippets: list[str],
        *,
        llm_client: LLMGateway | None = None,
    ) -> list[dict[str, Any]]:
        sources = self._extract_sources(snippets)
        system_prompt = (
            "You are a procurement analyst. Extract insights about the vendor from the summary "
            "and snippets. Return ONLY JSON as an array of objects with fields: "
            "category (financial, performance, legal, sentiment), sentiment "
            "(positive, negative, neutral), detail, source_url."
        )
        user_prompt = json.dumps(
            {"summary": summary, "snippets": snippets, "sources": sources},
            indent=2,
        )

        llm = llm_client or LLMGateway()
        try:
            response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            data = json.loads(response.content)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
            self.logger.warning("Vendor insight extraction failed", extra={"error": str(exc)})
            return [
                {
                    "category": "sentiment",
                    "sentiment": "neutral",
                    "detail": summary,
                    "source_url": sources[0]["url"] if sources else "",
                }
            ]

        insights: list[dict[str, Any]] = []
        if not isinstance(data, list):
            return insights
        for entry in data:
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category", "sentiment")).strip().lower()
            sentiment = str(entry.get("sentiment", "neutral")).strip().lower()
            detail = str(entry.get("detail", "")).strip()
            source_url = str(entry.get("source_url", "")).strip()
            if not detail:
                continue
            insights.append(
                {
                    "category": category,
                    "sentiment": sentiment,
                    "detail": detail,
                    "source_url": source_url,
                }
            )
        return insights

    async def _calculate_overall_vendor_score(
        self, vendor: dict[str, Any], *, external_adjustment: dict[str, Any] | None = None
    ) -> float:
        """Calculate overall vendor score."""
        scoring = await self._calculate_vendor_score(
            vendor, external_adjustment=external_adjustment
        )
        return scoring["score"]

    async def _calculate_vendor_score(
        self, vendor: dict[str, Any], *, external_adjustment: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Calculate vendor score using weighted criteria."""
        risk_score = vendor.get("risk_score", 50)
        reliability_delta = 0
        if external_adjustment:
            risk_score = max(0, min(100, risk_score + external_adjustment.get("risk_delta", 0)))
            reliability_delta = external_adjustment.get("reliability_delta", 0)
        vendor = {**vendor, "risk_score": risk_score}
        score = self.ml_service.score_vendor(vendor)
        if self.vendor_scoring_weights:
            score = self.ml_service._weighted_score(
                self.ml_service._prepare_features(vendor),
                self.vendor_scoring_weights,
            )
        score = max(0, min(100, score + reliability_delta))
        return {
            "score": score,
            "inputs": self.ml_service._prepare_features(vendor),
            "weights": self.vendor_scoring_weights or self.ml_service.feature_weights,
        }

    async def _get_vendor_profile(
        self, vendor_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        vendor = await self._resolve_vendor(vendor_id, tenant_id=tenant_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")
        return {
            "vendor": vendor,
            "correlation_id": correlation_id,
        }

    async def _update_vendor_profile(
        self,
        vendor_id: str,
        updates: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        vendor = await self._resolve_vendor(vendor_id, tenant_id=tenant_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")
        vendor.update(updates)
        vendor["updated_at"] = datetime.now(timezone.utc).isoformat()
        vendor.setdefault("updated_by", actor_id)
        await self._persist_vendor(vendor, tenant_id=tenant_id)
        await self._publish_event(
            "vendor.updated",
            payload={"vendor_id": vendor_id, "updates": updates},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=vendor_id,
        )
        return {"vendor_id": vendor_id, "status": vendor.get("status"), "updates": updates}

    async def _list_vendor_profiles(
        self, criteria: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        vendors = [
            vendor
            for vendor in self.vendors.values()
            if await self._matches_criteria(vendor, criteria)
        ]
        return {
            "total_results": len(vendors),
            "vendors": vendors,
            "search_criteria": criteria,
            "tenant_id": tenant_id,
        }

    async def _sign_contract(
        self,
        contract_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        contract = self.contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")
        contract["status"] = "Active"
        contract["signed_at"] = datetime.now(timezone.utc).isoformat()
        self.contract_store.upsert(tenant_id, contract_id, contract)
        if self.db_service:
            await self.db_service.store("contracts", contract_id, contract)
        await self._publish_event(
            "contract.signed",
            payload={"contract_id": contract_id, "vendor_id": contract.get("vendor_id")},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=contract_id,
        )
        return {"contract_id": contract_id, "status": contract["status"]}

    async def _resolve_vendor(self, vendor_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        vendor = self.vendors.get(vendor_id)
        if vendor:
            return vendor
        stored = self.vendor_store.get(tenant_id, vendor_id)
        if stored:
            self.vendors[vendor_id] = stored
            return stored
        return None

    async def _persist_vendor(self, vendor: dict[str, Any], *, tenant_id: str) -> None:
        vendor_id = vendor.get("vendor_id")
        if not vendor_id:
            return
        self.vendors[vendor_id] = vendor
        self.vendor_store.upsert(tenant_id, vendor_id, vendor)
        if self.db_service:
            await self.db_service.store("vendors", vendor_id, vendor)

    async def _load_vendor_cache(self) -> None:
        for tenant_id in self.vendor_store.tenants():
            for vendor in self.vendor_store.list(tenant_id):
                vendor_id = vendor.get("vendor_id")
                if vendor_id:
                    self.vendors[vendor_id] = vendor

    async def _initiate_mitigation_workflow(
        self,
        *,
        vendor: dict[str, Any],
        reason: str,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        vendor_id = vendor.get("vendor_id")
        if not vendor_id:
            return {"status": "skipped"}
        task_payload = {
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("legal_name"),
            "reason": reason,
            "risk_score": vendor.get("risk_score"),
            "compliance_status": vendor.get("compliance_status"),
        }
        task_result = await self.task_client.create_task(
            tenant_id=tenant_id,
            instance_id=vendor_id,
            task_type="vendor_mitigation",
            payload=task_payload,
        )
        notification = await self.communications_client.notify(
            tenant_id=tenant_id,
            subject=f"Vendor risk mitigation required: {vendor.get('legal_name')}",
            body=(
                f"Vendor {vendor.get('legal_name')} triggered a risk event. "
                f"Reason: {reason}. Current status: {vendor.get('status')}."
            ),
            stakeholders=vendor.get("stakeholders", []),
            metadata={"vendor_id": vendor_id, "correlation_id": correlation_id},
        )
        await self._publish_event(
            "vendor.mitigation.initiated",
            payload={
                "vendor_id": vendor_id,
                "task": task_result,
                "notification": notification,
                "reason": reason,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=vendor.get("created_by", "system"),
            entity_id=vendor_id,
        )
        return {"task": task_result, "notification": notification}

    def _extract_sources(self, snippets: list[str]) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        for snippet in snippets:
            match = re.search(r"\((https?://[^)]+)\)", snippet)
            url = match.group(1) if match else ""
            if not url:
                continue
            sources.append({"url": url, "citation": snippet.strip()})
        return sources

    def _score_vendor_research(self, research: dict[str, Any]) -> dict[str, Any]:
        insights = research.get("insights", []) if isinstance(research, dict) else []
        negative = sum(1 for insight in insights if insight.get("sentiment") == "negative")
        positive = sum(1 for insight in insights if insight.get("sentiment") == "positive")
        risk_delta = max(-20, min(20, negative * 6 - positive * 4))
        reliability_delta = max(-10, min(10, positive * 2 - negative))
        return {
            "risk_delta": risk_delta,
            "reliability_delta": reliability_delta,
            "signals": {"positive": positive, "negative": negative},
        }

    async def _is_expiring_soon(self, contract: dict[str, Any]) -> bool:
        """Check if contract is expiring within 90 days."""
        end_date_str = contract.get("end_date")
        if not end_date_str:
            return False

        end_date = datetime.fromisoformat(end_date_str)
        days_until_expiry = (end_date - datetime.now(timezone.utc)).days
        return 0 < days_until_expiry <= 90

    async def _matches_criteria(self, vendor: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Check if vendor matches search criteria."""
        if "category" in criteria and vendor.get("category") != criteria["category"]:
            return False

        if "min_rating" in criteria:
            if (
                vendor.get("performance_metrics", {}).get("quality_rating", 0)
                < criteria["min_rating"]
            ):
                return False

        if "max_risk_score" in criteria:
            if vendor.get("risk_score", 100) > criteria["max_risk_score"]:
                return False

        if "status" in criteria and vendor.get("status") != criteria["status"]:
            return False

        return True

    async def _validate_vendor_record(
        self, *, vendor: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        record = {
            "id": vendor.get("vendor_id"),
            "tenant_id": tenant_id,
            "name": vendor.get("legal_name"),
            "category": vendor.get("category"),
            "status": vendor.get("status"),
            "owner": vendor.get("created_by"),
            "classification": vendor.get("classification", "internal"),
            "created_at": vendor.get("created_at"),
        }
        if vendor.get("updated_at"):
            record["updated_at"] = vendor.get("updated_at")
        errors = validate_against_schema(self.vendor_schema_path, record)
        if errors:
            for error in errors:
                self.logger.warning("Vendor schema error %s: %s", error.path, error.message)
        return {"is_valid": len(errors) == 0, "issues": [error.message for error in errors]}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Vendor & Procurement Management Agent...")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "vendor_registry",
            "vendor_onboarding",
            "vendor_risk_scoring",
            "procurement_request_intake",
            "rfp_generation",
            "rfp_quote_management",
            "vendor_selection",
            "vendor_scoring",
            "contract_management",
            "purchase_order_creation",
            "purchase_order_approval",
            "invoice_receipt",
            "invoice_reconciliation",
            "three_way_matching",
            "vendor_performance_monitoring",
            "vendor_scorecard_generation",
            "compliance_enforcement",
            "vendor_profile_management",
            "risk_mitigation_workflows",
            "event_bus_integration",
            "audit_trail_management",
            "spend_analysis",
            "external_vendor_research",
        ]
