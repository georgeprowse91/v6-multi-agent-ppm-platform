"""
Risk Management Agent

Purpose:
Proactively identifies, assesses and monitors risks across projects, programs and portfolios.
Maintains a central risk register, quantifies probability and impact, recommends mitigation
strategies and continuously tracks risk status.

Specification: agents/delivery-management/risk-management-agent/README.md
"""

import importlib.util
import json
import os
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as url_error
from urllib import request as url_request

from data_quality.helpers import validate_against_schema
from data_quality.rules import evaluate_quality_rules

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from analytics_insights_agent import DataLakeManager, SynapseManager  # noqa: E402
from llm.client import LLMGateway, LLMProviderError  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentationPublishingService,
    DocumentManagementService,
    DocumentMetadata,
    GRCIntegrationService,
    GRCRisk,
    MLPredictionService,
    ProjectManagementService,
)
from agents.common.web_search import (  # noqa: E402
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent, get_event_bus  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.policy import evaluate_compliance_controls  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402


class CognitiveSearchService:
    """Lightweight Azure Cognitive Search helper for risk extraction."""

    def __init__(
        self,
        endpoint: str | None,
        api_key: str | None,
        index_name: str | None,
        api_version: str = "2023-11-01",
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name
        self.api_version = api_version

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.index_name)

    def search(
        self, query: str, *, top: int = 5, filter_expression: str | None = None
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        url = (
            f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        )
        payload: dict[str, Any] = {"search": query, "top": top}
        if filter_expression:
            payload["filter"] = filter_expression
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key or "",
        }
        req = url_request.Request(url, data=data, headers=headers, method="POST")
        try:
            with url_request.urlopen(req) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body)
                return parsed.get("value", [])
        except (url_error.URLError, json.JSONDecodeError, ValueError):
            return []

    def extract_risks(self, documents: list[dict[str, Any] | str]) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        if not documents:
            return extracted
        if self.is_configured():
            queries = []
            for document in documents:
                if isinstance(document, dict):
                    queries.append(
                        str(
                            document.get("title")
                            or document.get("query")
                            or document.get("content")
                            or ""
                        )
                    )
                else:
                    queries.append(str(document))
            for query in [q.strip() for q in queries if q.strip()]:
                results = self.search(f"{query} risk", top=3)
                for result in results:
                    title = result.get("title") or result.get("id") or "Risk signal"
                    description = result.get("content") or result.get("description") or str(result)
                    extracted.append(
                        {
                            "title": title,
                            "description": description,
                            "category": "document",
                            "source": result.get("source") or "cognitive_search",
                        }
                    )
            if extracted:
                return extracted
        for document in documents:
            text = document.get("content") if isinstance(document, dict) else str(document)
            for line in str(text).splitlines():
                if "risk" in line.lower():
                    extracted.append(
                        {
                            "title": line.strip()[:80] or "Document risk",
                            "description": line.strip(),
                            "category": "document",
                            "source": "heuristic",
                        }
                    )
        return extracted


class KnowledgeBaseQueryService:
    """Query SharePoint/Confluence for mitigation guidance."""

    def __init__(
        self,
        document_service: DocumentManagementService,
        documentation_service: DocumentationPublishingService,
    ) -> None:
        self.document_service = document_service
        self.documentation_service = documentation_service

    async def query_mitigations(self, risk: dict[str, Any]) -> list[dict[str, Any]]:
        query = f"{risk.get('category', '')} mitigation {risk.get('title', '')}".strip()
        results: list[dict[str, Any]] = []

        confluence_connector = self.documentation_service._get_confluence_connector()
        if confluence_connector and hasattr(confluence_connector, "read"):
            try:
                pages = confluence_connector.read(
                    "pages",
                    filters={"query": query},
                    limit=5,
                )
                for page in pages or []:
                    results.append(
                        {
                            "title": page.get("title"),
                            "strategy": page.get("excerpt") or page.get("title"),
                            "source": "confluence",
                        }
                    )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                results = results

        sharepoint_connector = self.document_service._get_connector()
        if sharepoint_connector and hasattr(sharepoint_connector, "read"):
            try:
                documents = sharepoint_connector.read(
                    "documents",
                    filters={"search": query},
                    limit=5,
                )
                for document in documents or []:
                    results.append(
                        {
                            "title": document.get("Title") or document.get("title"),
                            "strategy": document.get("Description") or document.get("summary"),
                            "source": "sharepoint",
                        }
                    )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                results = results

        return [item for item in results if item.get("strategy")]


class RiskNLPExtractor:
    """Extract risks from text using a transformer model with fallback heuristics."""

    def __init__(
        self,
        *,
        model_name: str = "bert-base-uncased",
        pipeline_task: str = "zero-shot-classification",
        labels: list[str] | None = None,
        threshold: float = 0.6,
        max_sentences: int = 80,
        training_keywords: tuple[str, ...] | None = None,
    ) -> None:
        self.model_name = model_name
        self.pipeline_task = pipeline_task
        self.labels = labels or ["risk", "no risk"]
        self.threshold = threshold
        self.max_sentences = max_sentences
        self.training_keywords = training_keywords or (
            "risk",
            "delay",
            "overrun",
            "issue",
            "compliance",
            "shortage",
            "failure",
            "defect",
            "breach",
        )
        self._pipeline = None
        self._sklearn_model = None
        self._vectorizer = None
        self._trained = False

    def is_available(self) -> bool:
        return importlib.util.find_spec("transformers") is not None

    def is_sklearn_available(self) -> bool:
        return importlib.util.find_spec("sklearn") is not None

    def train(self, documents: list[dict[str, Any] | str]) -> bool:
        sentences = self._collect_sentences(documents)
        if not sentences or not self.is_sklearn_available():
            return False

        labeled: list[tuple[str, int]] = []
        for sentence in sentences:
            label = 1 if self._is_risk_sentence(sentence) else 0
            labeled.append((sentence, label))

        if len(labeled) < 4:
            return False
        if len({label for _, label in labeled}) < 2:
            return False

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

            texts = [text for text, _ in labeled]
            labels = [label for _, label in labeled]
            vectorizer = TfidfVectorizer(stop_words="english")
            features = vectorizer.fit_transform(texts)
            model = LogisticRegression(max_iter=200)
            model.fit(features, labels)
            self._vectorizer = vectorizer
            self._sklearn_model = model
            self._trained = True
            return True
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            self._sklearn_model = None
            self._vectorizer = None
            self._trained = False
            return False

    def extract_risks(self, documents: list[dict[str, Any] | str]) -> list[dict[str, Any]]:
        sentences = self._collect_sentences(documents)
        if not sentences:
            return []
        if self._trained and self._sklearn_model and self._vectorizer:
            return self._sklearn_risks(sentences)
        self._ensure_pipeline()
        if self._pipeline is None:
            return self._heuristic_risks(sentences)
        return self._model_risks(sentences)

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None or not self.is_available():
            return
        from transformers import pipeline

        try:
            self._pipeline = pipeline(self.pipeline_task, model=self.model_name)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            self._pipeline = None

    def _collect_sentences(self, documents: list[dict[str, Any] | str]) -> list[str]:
        sentences: list[str] = []
        for document in documents:
            if isinstance(document, dict):
                text = str(document.get("content") or document.get("text") or document)
            else:
                text = str(document)
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                cleaned = sentence.strip()
                if cleaned:
                    sentences.append(cleaned)
            if len(sentences) >= self.max_sentences:
                break
        return sentences[: self.max_sentences]

    def _heuristic_risks(self, sentences: list[str]) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        for sentence in sentences:
            if self._is_risk_sentence(sentence):
                extracted.append(
                    {
                        "title": sentence[:80],
                        "description": sentence,
                        "category": "nlp",
                        "source": "heuristic_nlp",
                    }
                )
        return extracted

    def _sklearn_risks(self, sentences: list[str]) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        if not self._trained or not self._sklearn_model or not self._vectorizer:
            return extracted
        try:
            features = self._vectorizer.transform(sentences)
            probabilities = self._sklearn_model.predict_proba(features)[:, 1]
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            return self._heuristic_risks(sentences)
        for sentence, probability in zip(sentences, probabilities):
            if probability >= self.threshold:
                extracted.append(
                    {
                        "title": sentence[:80],
                        "description": sentence,
                        "category": "nlp",
                        "source": "sklearn",
                        "confidence": float(round(probability, 4)),
                    }
                )
        return extracted

    def _model_risks(self, sentences: list[str]) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        for sentence in sentences:
            if self.pipeline_task == "zero-shot-classification":
                result = self._pipeline(sentence, self.labels)
                scores = dict(zip(result.get("labels", []), result.get("scores", [])))
                risk_score = scores.get(self.labels[0], 0.0)
                if risk_score >= self.threshold:
                    extracted.append(
                        {
                            "title": sentence[:80],
                            "description": sentence,
                            "category": "nlp",
                            "source": "transformer",
                            "confidence": risk_score,
                        }
                    )
            else:
                result = self._pipeline(sentence)
                if isinstance(result, list):
                    result = result[0] if result else {}
                label = str(result.get("label", "")).lower()
                score = float(result.get("score", 0.0))
                if "risk" in label or score >= self.threshold:
                    extracted.append(
                        {
                            "title": sentence[:80],
                            "description": sentence,
                            "category": "nlp",
                            "source": "transformer",
                            "confidence": score,
                        }
                    )
        return extracted

    def _is_risk_sentence(self, sentence: str) -> bool:
        lowered = sentence.lower()
        return any(keyword in lowered for keyword in self.training_keywords)


class RiskManagementAgent(BaseAgent):
    """
    Risk Management Agent - Identifies, assesses and monitors risks.

    Key Capabilities:
    - Risk identification and capture
    - Risk classification and scoring
    - Risk prioritization and ranking
    - Mitigation and response planning
    - Trigger and threshold monitoring
    - Risk reporting and dashboards
    - Integration with other disciplines
    - Monte Carlo simulation
    """

    def __init__(self, agent_id: str = "risk-management-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.risk_categories = (
            config.get(
                "risk_categories",
                ["technical", "schedule", "financial", "compliance", "external", "resource"],
            )
            if config
            else ["technical", "schedule", "financial", "compliance", "external", "resource"]
        )
        self.enable_external_risk_research = (
            config.get("enable_external_risk_research", False) if config else False
        )
        self.risk_search_keywords = (
            config.get(
                "risk_search_keywords",
                [
                    "risk",
                    "failure",
                    "incident",
                    "disruption",
                    "regulatory change",
                    "supplier",
                ],
            )
            if config
            else [
                "risk",
                "failure",
                "incident",
                "disruption",
                "regulatory change",
                "supplier",
            ]
        )
        self.risk_search_result_limit = (
            int(config.get("risk_search_result_limit", 5)) if config else 5
        )

        self.probability_scale = (
            config.get("probability_scale", [1, 2, 3, 4, 5]) if config else [1, 2, 3, 4, 5]
        )
        self.impact_scale = (
            config.get("impact_scale", [1, 2, 3, 4, 5]) if config else [1, 2, 3, 4, 5]
        )
        self.high_risk_threshold = config.get("high_risk_threshold", 15) if config else 15
        self.risk_schema_path = (
            Path(config.get("risk_schema_path", "data/schemas/risk.schema.json"))
            if config
            else Path("data/schemas/risk.schema.json")
        )

        risk_store_path = (
            Path(config.get("risk_store_path", "data/risk_register.json"))
            if config
            else Path("data/risk_register.json")
        )
        self.risk_store = TenantStateStore(risk_store_path)

        # Data stores (will be replaced with database)
        self.risk_register: dict[str, Any] = {}
        self.mitigation_plans: dict[str, Any] = {}
        self.triggers: dict[str, Any] = {}
        self.risk_histories: dict[str, Any] = {}
        self.db_service: DatabaseStorageService | None = None
        self.grc_service: GRCIntegrationService | None = None
        self.document_service: DocumentManagementService | None = None
        self.documentation_service: DocumentationPublishingService | None = None
        self.ml_service: MLPredictionService | None = None
        self.project_management_services: dict[str, ProjectManagementService] = {}
        self.cognitive_search_service: CognitiveSearchService | None = None
        self.knowledge_base_service: KnowledgeBaseQueryService | None = None
        self.resource_management_service = (
            config.get("resource_management_service") if config else None
        )
        self.data_lake_manager: DataLakeManager | None = None
        self.synapse_manager: SynapseManager | None = None
        self.event_bus = None
        self.risk_events: list[dict[str, Any]] = []
        self.risk_trigger_thresholds = (
            config.get(
                "risk_trigger_thresholds",
                {
                    "cost_overrun_pct": 0.1,
                    "schedule_delay_days": 10,
                    "quality_defect_rate": 0.05,
                    "resource_utilization": 0.9,
                },
            )
            if config
            else {
                "cost_overrun_pct": 0.1,
                "schedule_delay_days": 10,
                "quality_defect_rate": 0.05,
                "resource_utilization": 0.9,
            }
        )
        self.risk_nlp_extractor = config.get("risk_nlp_extractor") if config else None
        if not self.risk_nlp_extractor:
            self.risk_nlp_extractor = RiskNLPExtractor(
                model_name=(config.get("risk_nlp_model_name") if config else "bert-base-uncased"),
                pipeline_task=(
                    config.get("risk_nlp_pipeline_task") if config else "zero-shot-classification"
                ),
                labels=(config.get("risk_nlp_labels") if config else None),
                threshold=float(config.get("risk_nlp_threshold", 0.6)) if config else 0.6,
                max_sentences=int(config.get("risk_nlp_max_sentences", 80)) if config else 80,
                training_keywords=(
                    tuple(config.get("risk_nlp_training_keywords"))
                    if config and config.get("risk_nlp_training_keywords")
                    else None
                ),
            )
        self.schedule_agent_endpoint = (
            config.get("schedule_agent_endpoint") if config else None
        ) or (config.get("related_agent_endpoints", {}).get("schedule") if config else None)
        self.financial_agent_endpoint = (
            config.get("financial_agent_endpoint") if config else None
        ) or (config.get("related_agent_endpoints", {}).get("financial") if config else None)
        self.schedule_baseline_fixture = (
            config.get("schedule_baseline_fixture", {}) if config else {}
        )
        self.financial_distribution_fixture = (
            config.get("financial_distribution_fixture", {}) if config else {}
        )
        self.simulation_offload = config.get("simulation_offload", {}) if config else {}
        self.latest_schedule_signals: dict[str, Any] = {}
        self.latest_financial_signals: dict[str, Any] = {}
        self._local_probability_model = None
        self._local_impact_model = None

    async def initialize(self) -> None:
        """Initialize database connections, analytics tools, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Risk Management Agent...")

        self.db_service = DatabaseStorageService(self.config)
        self.grc_service = GRCIntegrationService(self.config)
        self.document_service = DocumentManagementService(self.config)
        self.documentation_service = DocumentationPublishingService(self.config)
        self.ml_service = self.config.get("ml_service") or MLPredictionService(self.config)
        self.cognitive_search_service = self.config.get(
            "cognitive_search_service"
        ) or CognitiveSearchService(
            endpoint=self.config.get("cognitive_search_endpoint")
            or os.getenv("AZURE_COG_SEARCH_ENDPOINT"),
            api_key=self.config.get("cognitive_search_key")
            or os.getenv("AZURE_COG_SEARCH_API_KEY"),
            index_name=self.config.get("cognitive_search_index")
            or os.getenv("AZURE_COG_SEARCH_INDEX"),
        )
        self.knowledge_base_service = self.config.get(
            "knowledge_base_service"
        ) or KnowledgeBaseQueryService(
            self.document_service,
            self.documentation_service,
        )
        self.project_management_services = self._initialize_project_management_services()
        self.data_lake_manager = self.config.get("data_lake_manager") or DataLakeManager(
            file_system_name=self.config.get("data_lake_file_system")
            or os.getenv("AZURE_DATA_LAKE_FILE_SYSTEM"),
            service_client=self.config.get("data_lake_client"),
        )
        self.synapse_manager = self.config.get("synapse_manager") or SynapseManager(
            workspace_name=self.config.get("synapse_workspace")
            or os.getenv("AZURE_SYNAPSE_WORKSPACE"),
            sql_pool_name=self.config.get("synapse_sql_pool")
            or os.getenv("AZURE_SYNAPSE_SQL_POOL"),
            spark_pool_name=self.config.get("synapse_spark_pool")
            or os.getenv("AZURE_SYNAPSE_SPARK_POOL"),
            synapse_client=self.config.get("synapse_client"),
        )
        self.event_bus = self.config.get("event_bus")
        if not self.event_bus:
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
        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe(
                "schedule.baseline.locked", self._handle_schedule_baseline_event
            )
            self.event_bus.subscribe("schedule.delay", self._handle_schedule_delay_event)
            self.event_bus.subscribe(
                "financial.budget.updated", self._handle_financial_update_event
            )
            self.event_bus.subscribe("financial.cost_overrun", self._handle_cost_overrun_event)
            self.event_bus.subscribe(
                "schedule.milestone.missed", self._handle_milestone_missed_event
            )
            self.event_bus.subscribe("quality.defect_rate", self._handle_quality_event)
            self.event_bus.subscribe(
                "resource.utilization", self._handle_resource_utilization_event
            )

        if self.synapse_manager:
            self.synapse_manager.ensure_pools()

        await self._prime_risk_extractor()

        self.logger.info("Risk Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "identify_risk",
            "assess_risk",
            "prioritize_risks",
            "create_mitigation_plan",
            "monitor_triggers",
            "update_risk_status",
            "run_monte_carlo",
            "generate_risk_matrix",
            "get_risk_dashboard",
            "generate_risk_report",
            "perform_sensitivity_analysis",
            "get_top_risks",
            "research_risks",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "identify_risk":
            risk_data = input_data.get("risk", {})
            required_fields = ["title", "description", "category"]
            for field in required_fields:
                if field not in risk_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "research_risks":
            if not input_data.get("domain"):
                self.logger.warning("Missing required field: domain")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process risk management requests.

        Args:
            input_data: {
                "action": "identify_risk" | "assess_risk" | "prioritize_risks" |
                          "create_mitigation_plan" | "monitor_triggers" | "update_risk_status" |
                          "run_monte_carlo" | "generate_risk_matrix" | "get_risk_dashboard" |
                          "generate_risk_report" | "perform_sensitivity_analysis" | "get_top_risks",
                "risk": Risk data,
                "mitigation": Mitigation plan data,
                "trigger": Trigger definition,
                "risk_id": Risk identifier,
                "project_id": Project identifier,
                "portfolio_id": Portfolio identifier,
                "iterations": Monte Carlo iterations,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - identify_risk: Risk ID and initial assessment
            - assess_risk: Risk score and classification
            - prioritize_risks: Ranked risk list
            - create_mitigation_plan: Mitigation plan ID and tasks
            - monitor_triggers: Trigger alerts and risk updates
            - update_risk_status: Updated risk status
            - run_monte_carlo: Probabilistic analysis results
            - generate_risk_matrix: Risk matrix visualization data
            - get_risk_dashboard: Dashboard data and visualizations
            - generate_risk_report: Risk report data
            - perform_sensitivity_analysis: Sensitivity analysis results
            - get_top_risks: Top ranked risks
        """
        action = input_data.get("action", "get_risk_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        compliance_decision = evaluate_compliance_controls(
            {
                "personal_data": input_data.get("personal_data", {}),
                "consent": input_data.get("consent", {}),
            }
        )
        if compliance_decision.decision == "deny":
            emit_audit_event(
                build_audit_event(
                    tenant_id=tenant_id,
                    action="risk.data_processing.denied",
                    outcome="denied",
                    actor_id=self.agent_id,
                    actor_type="service",
                    actor_roles=[],
                    resource_id=input_data.get("project_id") or "unknown",
                    resource_type="risk_processing",
                    metadata={"reasons": list(compliance_decision.reasons)},
                    legal_basis="consent",
                    retention_period="P1Y",
                    correlation_id=correlation_id,
                )
            )
            return {
                "status": "error",
                "error": "Consent is required before processing personal data.",
                "reasons": list(compliance_decision.reasons),
            }

        input_data["personal_data"] = compliance_decision.sanitized_payload.get("personal_data", {})
        emit_audit_event(
            build_audit_event(
                tenant_id=tenant_id,
                action="risk.data_processing.allowed",
                outcome="success",
                actor_id=self.agent_id,
                actor_type="service",
                actor_roles=[],
                resource_id=input_data.get("project_id") or "unknown",
                resource_type="risk_processing",
                metadata={
                    "masked_fields": list(compliance_decision.masked_fields),
                    "reasons": list(compliance_decision.reasons),
                },
                legal_basis="consent",
                retention_period="P1Y",
                correlation_id=correlation_id,
            )
        )

        if action == "identify_risk":
            return await self._identify_risk(
                input_data.get("risk", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "assess_risk":
            return await self._assess_risk(input_data.get("risk_id"))  # type: ignore

        elif action == "prioritize_risks":
            return await self._prioritize_risks(
                input_data.get("project_id"), input_data.get("portfolio_id")
            )

        elif action == "create_mitigation_plan":
            return await self._create_mitigation_plan(
                input_data.get("risk_id"), input_data.get("mitigation", {})  # type: ignore
            )

        elif action == "monitor_triggers":
            return await self._monitor_triggers(input_data.get("risk_id"))

        elif action == "update_risk_status":
            return await self._update_risk_status(
                input_data.get("risk_id"),  # type: ignore
                input_data.get("updates", {}),
                tenant_id=tenant_id,
            )

        elif action == "run_monte_carlo":
            return await self._run_monte_carlo(
                input_data.get("project_id"), input_data.get("iterations", 10000)  # type: ignore
            )

        elif action == "generate_risk_matrix":
            return await self._generate_risk_matrix(
                input_data.get("project_id"), input_data.get("portfolio_id")
            )

        elif action == "get_risk_dashboard":
            return await self._get_risk_dashboard(
                input_data.get("project_id"),
                input_data.get("portfolio_id"),
                tenant_id=tenant_id,
                external_context=input_data.get("external_context"),
            )

        elif action == "generate_risk_report":
            return await self._generate_risk_report(
                input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        elif action == "perform_sensitivity_analysis":
            return await self._perform_sensitivity_analysis(input_data.get("project_id"))  # type: ignore

        elif action == "get_top_risks":
            return await self._get_top_risks(  # type: ignore
                input_data.get("project_id"), input_data.get("limit", 10)
            )

        elif action == "research_risks":
            return await self._research_risks(
                project_id=input_data.get("project_id"),
                domain=input_data.get("domain", ""),
                region=input_data.get("region"),
                categories=input_data.get("categories", []),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _identify_risk(
        self,
        risk_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Identify and capture a new risk.

        Returns risk ID and initial assessment.
        """
        self.logger.info("Identifying risk: %s", risk_data.get("title"))

        # Generate risk ID
        risk_id = await self._generate_risk_id()

        # Extract risks from documents if provided
        documents = risk_data.get("documents", [])
        if documents:
            await self._train_risk_extractor(documents)
        extracted_risks = await self._extract_risks_from_documents(documents)

        # Perform initial classification and scoring
        initial_assessment = await self._initial_risk_assessment(risk_data)

        created_at = datetime.now(timezone.utc).isoformat()
        # Create risk entry
        risk = {
            "risk_id": risk_id,
            "project_id": risk_data.get("project_id"),
            "program_id": risk_data.get("program_id"),
            "portfolio_id": risk_data.get("portfolio_id"),
            "task_id": risk_data.get("task_id"),
            "title": risk_data.get("title"),
            "description": risk_data.get("description"),
            "category": risk_data.get("category"),
            "probability": initial_assessment.get("probability"),
            "impact": initial_assessment.get("impact"),
            "score": initial_assessment.get("score"),
            "proximity": risk_data.get("proximity", "medium_term"),
            "detectability": risk_data.get("detectability", "medium"),
            "owner": risk_data.get("owner") or "unassigned",
            "status": "open",
            "created_at": created_at,
            "created_by": risk_data.get("created_by", "unknown"),
            "triggers": risk_data.get("triggers", []),
            "mitigation_plan_id": None,
            "residual_risk": None,
            "classification": risk_data.get("classification", "internal"),
            "extracted_risks": extracted_risks,
        }

        validation = await self._validate_risk_record(risk=risk, tenant_id=tenant_id)
        if not validation["is_valid"]:
            raise ValueError("Risk schema validation failed")

        # Store risk
        self.risk_register[risk_id] = risk
        self.risk_store.upsert(tenant_id, risk_id, risk)
        if risk.get("triggers"):
            await self._register_triggers(risk_id, risk.get("triggers") or [])

        if self.db_service:
            await self.db_service.store("risks", risk_id, risk)
        await self._store_risk_dataset("risks", [risk], domain="risk_register")
        await self._publish_risk_event(
            "risk.identified",
            {
                "risk_id": risk_id,
                "title": risk.get("title"),
                "category": risk.get("category"),
                "score": risk.get("score"),
                "status": risk.get("status"),
            },
        )
        grc_sync = None
        if self.grc_service:
            grc_risk = GRCRisk(
                risk_id=risk_id,
                title=risk["title"],
                description=risk["description"],
                category=risk["category"],
                likelihood=self._map_rating_to_label(risk.get("probability")),
                impact=self._map_rating_to_label(risk.get("impact")),
                status=risk.get("status", "open"),
                owner=risk.get("owner") or "",
                mitigation_plan=risk.get("mitigation_plan_id") or "",
            )
            grc_sync = await self.grc_service.sync_risk(grc_risk)
            risk["grc_sync"] = grc_sync

        document_results = []
        if self.document_service and risk_data.get("documents"):
            for index, document in enumerate(risk_data.get("documents", []), start=1):
                if isinstance(document, dict):
                    content = str(document.get("content") or document.get("text") or document)
                    title = document.get("title") or f"{risk['title']} Document {index}"
                else:
                    content = str(document)
                    title = f"{risk['title']} Document {index}"
                metadata = DocumentMetadata(
                    title=title,
                    description=f"Risk document for {risk['title']}",
                    classification=risk.get("classification", "internal"),
                    tags=[risk.get("category", "risk"), "risk-register"],
                    owner=risk.get("owner") or "",
                )
                result = await self.document_service.publish_document(
                    document_content=content,
                    metadata=metadata,
                    folder_path="Risk Management",
                )
                document_results.append(result)
            risk["document_refs"] = document_results
        await self._publish_risk_event(
            "risk.identified",
            {"risk_id": risk_id, "title": risk["title"], "category": risk["category"]},
        )

        return {
            "risk_id": risk_id,
            "title": risk["title"],
            "category": risk["category"],
            "initial_score": risk["score"],
            "probability": risk["probability"],
            "impact": risk["impact"],
            "risk_level": await self._classify_risk_level(risk["score"]),
            "extracted_risks": extracted_risks,
            "data_quality": validation,
            "grc_sync": grc_sync,
            "documents": document_results,
            "next_steps": "Create mitigation plan for high-priority risks",
        }

    async def _assess_risk(self, risk_id: str) -> dict[str, Any]:
        """
        Perform detailed risk assessment.

        Returns risk score and classification.
        """
        self.logger.info("Assessing risk: %s", risk_id)

        risk = self.risk_register.get(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        # Use predictive models for probability and impact
        await self._ensure_local_risk_models()
        predicted_assessment = await self._predict_risk_metrics(risk)

        # Calculate quantitative impact
        quantitative_impact = await self._calculate_quantitative_impact(risk)

        # Update risk with detailed assessment
        risk["probability"] = predicted_assessment.get("probability", risk["probability"])
        risk["impact"] = predicted_assessment.get("impact", risk["impact"])
        risk["score"] = risk["probability"] * risk["impact"]
        risk["quantitative_impact"] = quantitative_impact
        risk["last_assessed"] = datetime.now(timezone.utc).isoformat()

        if self.db_service:
            await self.db_service.store("risks", risk_id, risk)
            await self.db_service.store(
                "risk_assessments",
                f"{risk_id}-{risk['last_assessed'].replace(':', '-')}",
                {
                    "risk_id": risk_id,
                    "assessment": predicted_assessment,
                    "score": risk["score"],
                    "assessed_at": risk["last_assessed"],
                },
            )
            await self.db_service.store(
                "risk_impacts",
                f"{risk_id}-{risk['last_assessed'].replace(':', '-')}",
                {
                    "risk_id": risk_id,
                    "quantitative_impact": quantitative_impact,
                    "assessed_at": risk["last_assessed"],
                },
            )
        await self._store_risk_dataset("risks", [risk], domain="risk_register")
        await self._publish_risk_event(
            "risk.assessed",
            {
                "risk_id": risk_id,
                "score": risk["score"],
                "probability": risk["probability"],
                "impact": risk["impact"],
            },
        )

        return {
            "risk_id": risk_id,
            "title": risk["title"],
            "probability": risk["probability"],
            "impact": risk["impact"],
            "score": risk["score"],
            "risk_level": await self._classify_risk_level(risk["score"]),
            "quantitative_impact": quantitative_impact,
            "assessment_date": risk["last_assessed"],
        }

    async def _prioritize_risks(
        self, project_id: str | None, portfolio_id: str | None
    ) -> dict[str, Any]:
        """
        Prioritize and rank risks.

        Returns ranked risk list.
        """
        self.logger.info(
            "Prioritizing risks for project=%s, portfolio=%s", project_id, portfolio_id
        )

        # Filter risks
        risks_to_prioritize = []
        for risk_id, risk in self.risk_register.items():
            if project_id and risk.get("project_id") != project_id:
                continue
            if portfolio_id and risk.get("portfolio_id") != portfolio_id:
                continue
            risks_to_prioritize.append(risk)

        # Calculate risk exposure (probability × impact)
        for risk in risks_to_prioritize:
            risk["exposure"] = risk.get("probability", 0) * risk.get("impact", 0)

        # Rank by exposure
        ranked_risks = sorted(risks_to_prioritize, key=lambda x: x.get("exposure", 0), reverse=True)

        # Categorize by risk level
        high_risks = [r for r in ranked_risks if r["exposure"] >= self.high_risk_threshold]
        medium_risks = [r for r in ranked_risks if 5 <= r["exposure"] < self.high_risk_threshold]
        low_risks = [r for r in ranked_risks if r["exposure"] < 5]

        return {
            "total_risks": len(ranked_risks),
            "high_risks": len(high_risks),
            "medium_risks": len(medium_risks),
            "low_risks": len(low_risks),
            "ranked_risks": [
                {
                    "risk_id": r["risk_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "score": r["exposure"],
                    "probability": r.get("probability"),
                    "impact": r.get("impact"),
                    "status": r.get("status"),
                    "risk_level": await self._classify_risk_level(float(r.get("exposure", 0) or 0)),
                    "project_id": r.get("project_id"),
                    "task_id": r.get("task_id"),
                }
                for r in ranked_risks
            ],
        }

    async def _create_mitigation_plan(
        self, risk_id: str, mitigation_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create mitigation plan for risk.

        Returns mitigation plan ID and tasks.
        """
        self.logger.info("Creating mitigation plan for risk: %s", risk_id)

        risk = self.risk_register.get(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        # Generate plan ID
        plan_id = await self._generate_mitigation_plan_id()

        # Recommend mitigation strategies
        recommended_strategies = await self._recommend_mitigation_strategies(risk)
        mitigation_owner = await self._resolve_mitigation_owner(risk, mitigation_data)
        tasks = mitigation_data.get("tasks", [])
        if not tasks:
            tasks = [
                {
                    "title": strategy,
                    "description": f"Mitigation action for risk {risk_id}: {strategy}",
                    "priority": (
                        "High" if risk.get("score", 0) >= self.high_risk_threshold else "Medium"
                    ),
                    "due_date": mitigation_data.get("due_date"),
                    "owner": mitigation_owner,
                }
                for strategy in recommended_strategies[:3]
            ]
        created_tasks = await self._create_mitigation_tasks(
            risk,
            tasks,
            mitigation_owner,
        )

        # Create mitigation plan
        mitigation_plan = {
            "plan_id": plan_id,
            "risk_id": risk_id,
            "strategy": mitigation_data.get(
                "strategy", "mitigate"
            ),  # avoid, mitigate, transfer, accept
            "tasks": tasks,
            "created_tasks": created_tasks,
            "budget": mitigation_data.get("budget"),
            "responsible_person": mitigation_owner,
            "due_date": mitigation_data.get("due_date"),
            "status": "Planned",
            "recommended_strategies": recommended_strategies,
            "effectiveness": mitigation_data.get("effectiveness"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store plan
        self.mitigation_plans[plan_id] = mitigation_plan

        # Update risk with mitigation plan
        risk["mitigation_plan_id"] = plan_id

        # Calculate residual risk
        residual_risk = await self._calculate_residual_risk(risk, mitigation_plan)
        risk["residual_risk"] = residual_risk
        if mitigation_plan.get("effectiveness") is None:
            mitigation_plan["effectiveness"] = round(
                max(0.0, 1 - (residual_risk / max(risk.get("score", 1), 1))), 2
            )

        if self.db_service:
            await self.db_service.store("mitigation_plans", plan_id, mitigation_plan)
            await self.db_service.store("risks", risk_id, risk)
            await self.db_service.store(
                "mitigation_tasks",
                f"{plan_id}-tasks",
                {"plan_id": plan_id, "risk_id": risk_id, "tasks": created_tasks},
            )
        await self._store_risk_dataset("mitigation_plans", [mitigation_plan], domain="mitigation")
        await self._publish_risk_event(
            "risk.mitigation_plan_created",
            {"risk_id": risk_id, "plan_id": plan_id, "strategy": mitigation_plan["strategy"]},
        )
        await self._publish_risk_event(
            "risk.mitigation.created",
            {"risk_id": risk_id, "plan_id": plan_id, "task_count": len(created_tasks)},
        )

        return {
            "plan_id": plan_id,
            "risk_id": risk_id,
            "strategy": mitigation_plan["strategy"],
            "tasks": mitigation_plan["tasks"],
            "created_tasks": created_tasks,
            "task_count": len(mitigation_plan["tasks"]),
            "budget": mitigation_plan["budget"],
            "residual_risk": residual_risk,
            "recommended_strategies": recommended_strategies,
        }

    async def _monitor_triggers(self, risk_id: str | None) -> dict[str, Any]:
        """
        Monitor risk triggers and early warnings.

        Returns trigger alerts and risk updates.
        """
        self.logger.info("Monitoring triggers for risk: %s", risk_id)

        # Get risks to monitor
        risks_to_monitor = []
        if risk_id:
            risk = self.risk_register.get(risk_id)
            if risk:
                risks_to_monitor.append(risk)
        else:
            risks_to_monitor = list(self.risk_register.values())

        # Check triggers
        triggered_risks = []
        for risk in risks_to_monitor:
            trigger_status = await self._check_risk_triggers(risk)

            if trigger_status.get("triggered"):
                # Update risk probability/impact
                await self._update_risk_from_trigger(risk, trigger_status)
                triggered_risks.append(
                    {
                        "risk_id": risk["risk_id"],
                        "title": risk["title"],
                        "trigger": trigger_status.get("trigger"),
                        "old_score": risk.get("score"),
                        "new_score": trigger_status.get("new_score"),
                    }
                )

        if self.db_service and triggered_risks:
            await self.db_service.store(
                "risk_triggers",
                f"trigger-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                {
                    "risks": triggered_risks,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if triggered_risks:
            await self._store_risk_dataset("risk_triggers", triggered_risks, domain="triggers")
            for triggered in triggered_risks:
                await self._publish_risk_event("risk.triggered", triggered)
                await self._publish_risk_event("risk.trigger_activated", triggered)

        return {
            "risks_monitored": len(risks_to_monitor),
            "risks_triggered": len(triggered_risks),
            "triggered_risks": triggered_risks,
        }

    async def _update_risk_status(
        self, risk_id: str, updates: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Update risk status and details.

        Returns updated risk status.
        """
        self.logger.info("Updating risk status: %s", risk_id)

        risk = self.risk_register.get(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        # Track history
        if risk_id not in self.risk_histories:
            self.risk_histories[risk_id] = []

        # Record current state before update
        self.risk_histories[risk_id].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": risk.get("status"),
                "probability": risk.get("probability"),
                "impact": risk.get("impact"),
                "score": risk.get("score"),
            }
        )

        # Apply updates
        for key, value in updates.items():
            if key in risk:
                risk[key] = value

        # Recalculate score if probability or impact changed
        if "probability" in updates or "impact" in updates:
            risk["score"] = risk.get("probability", 0) * risk.get("impact", 0)

        risk["last_updated"] = datetime.now(timezone.utc).isoformat()

        validation = await self._validate_risk_record(risk=risk, tenant_id=tenant_id)
        self.risk_store.upsert(tenant_id, risk_id, risk)
        if self.db_service:
            await self.db_service.store("risks", risk_id, risk)
        await self._store_risk_dataset("risks", [risk], domain="risk_register")
        await self._publish_risk_event(
            "risk.status_updated",
            {"risk_id": risk_id, "status": risk["status"], "score": risk["score"]},
        )

        return {
            "risk_id": risk_id,
            "status": risk["status"],
            "score": risk["score"],
            "last_updated": risk["last_updated"],
            "data_quality": validation,
        }

    async def _run_monte_carlo(self, project_id: str, iterations: int = 10000) -> dict[str, Any]:
        """
        Run Monte Carlo simulation for schedule and cost risk.

        Returns probabilistic analysis results.
        """
        self.logger.info("Running Monte Carlo simulation for project: %s", project_id)

        # Get project risks
        project_risks = [
            r for r in self.risk_register.values() if r.get("project_id") == project_id
        ]

        schedule_distribution = await self._fetch_schedule_baseline(project_id)
        financial_distribution = await self._fetch_financial_distribution(project_id)
        simulation_results = await self._offload_or_simulate(
            project_id,
            project_risks,
            iterations,
            schedule_distribution=schedule_distribution,
            financial_distribution=financial_distribution,
        )

        # Calculate percentiles
        schedule_p50 = await self._calculate_percentile(simulation_results["schedule"], 50)
        schedule_p80 = await self._calculate_percentile(simulation_results["schedule"], 80)
        schedule_p95 = await self._calculate_percentile(simulation_results["schedule"], 95)

        cost_p50 = await self._calculate_percentile(simulation_results["cost"], 50)
        cost_p80 = await self._calculate_percentile(simulation_results["cost"], 80)
        cost_p95 = await self._calculate_percentile(simulation_results["cost"], 95)

        await self._store_risk_dataset(
            "monte_carlo",
            [
                {
                    "project_id": project_id,
                    "iterations": iterations,
                    "schedule": simulation_results["schedule"][:100],
                    "cost": simulation_results["cost"][:100],
                    "schedule_distribution": schedule_distribution,
                    "financial_distribution": financial_distribution,
                }
            ],
            domain="simulation",
        )
        simulation_record = {
            "project_id": project_id,
            "iterations": iterations,
            "schedule_p50": schedule_p50,
            "schedule_p80": schedule_p80,
            "schedule_p95": schedule_p95,
            "cost_p50": cost_p50,
            "cost_p80": cost_p80,
            "cost_p95": cost_p95,
            "schedule_sample": simulation_results["schedule"][:100],
            "cost_sample": simulation_results["cost"][:100],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db_service:
            record_id = (
                f"{project_id}-simulation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            )
            await self.db_service.store("risk_simulations", record_id, simulation_record)
        await self._publish_risk_event(
            "risk.simulation_completed",
            {"project_id": project_id, "iterations": iterations},
        )
        await self._publish_risk_event(
            "risk.simulated",
            {
                "project_id": project_id,
                "iterations": iterations,
                "schedule_p80": schedule_p80,
                "cost_p80": cost_p80,
            },
        )
        return {
            "project_id": project_id,
            "iterations": iterations,
            "schedule_analysis": {
                "p50": schedule_p50,
                "p80": schedule_p80,
                "p95": schedule_p95,
                "mean": sum(simulation_results["schedule"]) / len(simulation_results["schedule"]),
            },
            "cost_analysis": {
                "p50": cost_p50,
                "p80": cost_p80,
                "p95": cost_p95,
                "mean": sum(simulation_results["cost"]) / len(simulation_results["cost"]),
            },
            "risks_analyzed": len(project_risks),
            "simulation_date": datetime.now(timezone.utc).isoformat(),
        }

    async def _generate_risk_matrix(
        self, project_id: str | None, portfolio_id: str | None
    ) -> dict[str, Any]:
        """
        Generate risk matrix (probability vs impact).

        Returns risk matrix visualization data.
        """
        self.logger.info(
            "Generating risk matrix for project=%s, portfolio=%s", project_id, portfolio_id
        )

        # Filter risks
        risks_to_plot = []
        for risk_id, risk in self.risk_register.items():
            if project_id and risk.get("project_id") != project_id:
                continue
            if portfolio_id and risk.get("portfolio_id") != portfolio_id:
                continue
            risks_to_plot.append(risk)

        # Create matrix data
        matrix_data = []
        for risk in risks_to_plot:
            matrix_data.append(
                {
                    "risk_id": risk["risk_id"],
                    "title": risk["title"],
                    "probability": risk.get("probability", 0),
                    "impact": risk.get("impact", 0),
                    "score": risk.get("score", 0),
                    "category": risk.get("category"),
                    "status": risk.get("status"),
                    "risk_level": await self._classify_risk_level(float(risk.get("score", 0) or 0)),
                    "project_id": risk.get("project_id"),
                    "task_id": risk.get("task_id"),
                }
            )

        return {
            "matrix_data": matrix_data,
            "total_risks": len(matrix_data),
            "probability_scale": self.probability_scale,
            "impact_scale": self.impact_scale,
        }

    async def _get_risk_dashboard(
        self,
        project_id: str | None,
        portfolio_id: str | None,
        *,
        tenant_id: str,
        external_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get risk dashboard data.

        Returns dashboard data and visualizations.
        """
        self.logger.info(
            "Getting risk dashboard for project=%s, portfolio=%s", project_id, portfolio_id
        )

        external_risk_research: dict[str, Any] | None = None
        if (
            self.enable_external_risk_research
            and project_id
            and external_context
            and external_context.get("domain")
        ):
            try:
                external_risk_research = await self._research_risks(
                    project_id=project_id,
                    domain=external_context.get("domain", ""),
                    region=external_context.get("region"),
                    categories=external_context.get("categories", []),
                    tenant_id=tenant_id,
                    correlation_id=external_context.get("correlation_id", "n/a"),
                )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # pragma: no cover - defensive
                self.logger.warning(
                    "External risk research failed",
                    extra={"error": str(exc), "project_id": project_id},
                )

        # Prioritize risks
        prioritization = await self._prioritize_risks(project_id, portfolio_id)

        # Get top risks
        top_risks = await self._get_top_risks(project_id, 10)

        # Generate risk matrix
        risk_matrix = await self._generate_risk_matrix(project_id, portfolio_id)

        # Get mitigation status
        mitigation_status = await self._get_mitigation_status(project_id)
        external_risk_signals = []
        if project_id:
            external_risk_signals = await self._collect_external_risk_signals(project_id)

        return {
            "project_id": project_id,
            "portfolio_id": portfolio_id,
            "risk_summary": {
                "total_risks": prioritization["total_risks"],
                "high_risks": prioritization["high_risks"],
                "medium_risks": prioritization["medium_risks"],
                "low_risks": prioritization["low_risks"],
            },
            "top_risks": top_risks,
            "risk_matrix": risk_matrix,
            "mitigation_status": mitigation_status,
            "external_risk_research": external_risk_research,
            "external_risk_signals": external_risk_signals,
            "risk_data": {
                "project_id": project_id,
                "project_risk_level": (
                    "high"
                    if prioritization.get("high_risks", 0)
                    else "medium" if prioritization.get("medium_risks", 0) else "low"
                ),
                "task_risks": [
                    {
                        "task_id": item.get("task_id"),
                        "risk_id": item.get("risk_id"),
                        "risk_level": str(item.get("risk_level", "low")).lower(),
                        "score": item.get("score", 0),
                    }
                    for item in prioritization.get("ranked_risks", [])
                    if item.get("task_id")
                ],
            },
            "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _generate_risk_report(
        self, report_type: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate risk report.

        Returns risk report data.
        """
        self.logger.info("Generating %s risk report", report_type)

        if report_type == "summary":
            return await self._generate_summary_report(filters)
        elif report_type == "detailed":
            return await self._generate_detailed_report(filters)
        elif report_type == "mitigation":
            return await self._generate_mitigation_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    async def _perform_sensitivity_analysis(self, project_id: str) -> dict[str, Any]:
        """
        Perform sensitivity analysis on project risks.

        Returns sensitivity analysis results.
        """
        self.logger.info("Performing sensitivity analysis for project: %s", project_id)

        # Get project risks
        project_risks = [
            r for r in self.risk_register.values() if r.get("project_id") == project_id
        ]

        # Analyze sensitivity to each risk factor
        sensitivity_results = []
        for risk in project_risks:
            sensitivity = await self._analyze_risk_sensitivity(risk)
            sensitivity_results.append(
                {
                    "risk_id": risk["risk_id"],
                    "title": risk["title"],
                    "sensitivity_score": sensitivity.get("score"),
                    "impact_on_schedule": sensitivity.get("schedule_impact"),
                    "impact_on_cost": sensitivity.get("cost_impact"),
                    "tornado_range": sensitivity.get("tornado_range"),
                }
            )

        # Sort by sensitivity score
        sorted_results = sorted(
            sensitivity_results, key=lambda x: x["sensitivity_score"], reverse=True
        )

        results = {
            "project_id": project_id,
            "sensitivity_analysis": sorted_results,
            "most_sensitive_risk": sorted_results[0] if sorted_results else None,
        }
        if sorted_results:
            await self._store_risk_dataset(
                "sensitivity_analysis",
                [{"project_id": project_id, "results": sorted_results}],
                domain="analytics",
            )
            await self._publish_risk_event(
                "risk.sensitivity_analyzed",
                {"project_id": project_id, "risk_count": len(sorted_results)},
            )
        return results

    async def _get_top_risks(self, project_id: str | None, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top N risks by score.

        Returns list of top risks.
        """
        # Filter and prioritize
        prioritization = await self._prioritize_risks(project_id, None)

        # Return top N
        return prioritization["ranked_risks"][:limit]  # type: ignore

    async def research_risks(
        self,
        domain: str,
        region: str | None,
        categories: list[str] | None,
        *,
        llm_client: LLMGateway | None = None,
        result_limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Research emerging risks using external sources."""
        if not self.enable_external_risk_research:
            return []

        context_parts = [domain, region or "", ", ".join(categories or [])]
        context = " ".join(part for part in context_parts if part)
        query = build_search_query(
            context,
            "risk",
            extra_keywords=self.risk_search_keywords,
        )

        # NOTE: Only high-level, non-sensitive context should be sent to the search API.
        snippets = await search_web(
            query, result_limit=result_limit or self.risk_search_result_limit
        )
        if not snippets:
            return []

        summary = await summarize_snippets(snippets, llm_client=llm_client, purpose="risk")
        return await self._classify_external_risks(
            summary,
            snippets,
            categories,
            llm_client=llm_client,
        )

    async def _research_risks(
        self,
        *,
        project_id: str | None,
        domain: str,
        region: str | None,
        categories: list[str] | None,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Fetch and merge externally researched risks into the risk register."""
        if not self.enable_external_risk_research:
            return {
                "project_id": project_id,
                "external_risks": [],
                "added_risks": [],
                "used_external_research": False,
                "notice": "External risk research is disabled.",
                "correlation_id": correlation_id,
            }

        try:
            external_risks = await self.research_risks(domain, region, categories)
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
                "Risk research failed",
                extra={
                    "error": str(exc),
                    "project_id": project_id,
                    "correlation_id": correlation_id,
                },
            )
            return {
                "project_id": project_id,
                "external_risks": [],
                "added_risks": [],
                "used_external_research": False,
                "notice": "External risk research failed; internal risk processes continue.",
                "correlation_id": correlation_id,
            }

        added = await self._merge_external_risks(
            external_risks,
            project_id=project_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return {
            "project_id": project_id,
            "external_risks": external_risks,
            "added_risks": added,
            "used_external_research": bool(external_risks),
            "notice": None,
            "correlation_id": correlation_id,
        }

    async def _classify_external_risks(
        self,
        summary: str,
        snippets: list[str],
        categories: list[str] | None,
        *,
        llm_client: LLMGateway | None = None,
    ) -> list[dict[str, Any]]:
        allowed_categories = ["technical", "schedule", "cost", "compliance"]
        category_context = categories or allowed_categories
        sources = self._extract_sources(snippets)

        system_prompt = (
            "You are a PMO risk analyst. Use the external summary and snippets to identify "
            "emerging risks. Return ONLY valid JSON as an array of objects with fields: "
            "title, description, category (technical, schedule, cost, compliance), "
            "probability (1-5), impact (1-5), sources (array of {url, citation})."
        )
        user_prompt = json.dumps(
            {
                "summary": summary,
                "snippets": snippets,
                "preferred_categories": category_context,
                "sources": sources,
            },
            indent=2,
        )

        llm = llm_client or LLMGateway()
        try:
            response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            data = json.loads(response.content)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
            self.logger.warning("Risk classification failed", extra={"error": str(exc)})
            return self._fallback_risk_classification(summary, sources)

        risks: list[dict[str, Any]] = []
        if not isinstance(data, list):
            return self._fallback_risk_classification(summary, sources)

        for entry in data:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title", "")).strip()
            description = str(entry.get("description", "")).strip()
            if not title or not description:
                continue
            category = self._normalize_risk_category(entry.get("category"), allowed_categories)
            probability = self._coerce_rating(entry.get("probability"), fallback=3)
            impact = self._coerce_rating(entry.get("impact"), fallback=3)
            entry_sources = entry.get("sources")
            if not isinstance(entry_sources, list) or not entry_sources:
                entry_sources = sources
            risks.append(
                {
                    "title": title,
                    "description": description,
                    "category": category,
                    "probability": probability,
                    "impact": impact,
                    "sources": entry_sources,
                }
            )

        return risks or self._fallback_risk_classification(summary, sources)

    async def _merge_external_risks(
        self,
        external_risks: list[dict[str, Any]],
        *,
        project_id: str | None,
        tenant_id: str,
        correlation_id: str,
    ) -> list[dict[str, Any]]:
        if not project_id or not external_risks:
            return []

        existing_signatures = {
            self._risk_signature(risk)
            for risk in self.risk_register.values()
            if risk.get("project_id") == project_id
        }
        added: list[dict[str, Any]] = []
        for risk in external_risks:
            signature = self._risk_signature(risk)
            if signature in existing_signatures:
                continue
            risk_data = {
                "project_id": project_id,
                "title": risk.get("title"),
                "description": risk.get("description"),
                "category": risk.get("category", "external"),
                "probability": risk.get("probability", 3),
                "impact": risk.get("impact", 3),
                # "external" is not a valid schema value; external research risks
                # default to "internal" classification (org-visible but not public).
                "classification": risk.get("classification", "internal"),
                "owner": risk.get("owner", "risk-management-system"),
                "created_by": "external_research",
                "sources": risk.get("sources", []),
            }
            try:
                created = await self._identify_risk(
                    risk_data, tenant_id=tenant_id, correlation_id=correlation_id
                )
                added.append(created)
                existing_signatures.add(signature)
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
                    "Failed to merge external risk",
                    extra={"error": str(exc), "project_id": project_id},
                )
        return added

    def _extract_sources(self, snippets: list[str]) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        for snippet in snippets:
            match = re.search(r"\((https?://[^)]+)\)", snippet)
            url = match.group(1) if match else ""
            citation = snippet.strip()
            if not url:
                continue
            sources.append({"url": url, "citation": citation})
        return sources

    def _normalize_risk_category(self, value: Any, allowed: list[str]) -> str:
        cleaned = str(value or "").strip().lower()
        if cleaned in allowed:
            return cleaned
        if cleaned in {"financial", "budget", "cost"}:
            return "cost"
        if cleaned in {"regulatory", "legal"}:
            return "compliance"
        return "technical"

    def _coerce_rating(self, value: Any, *, fallback: int) -> int:
        try:
            rating = int(float(value))
        except (TypeError, ValueError):
            return fallback
        return max(1, min(5, rating))

    def _risk_signature(self, risk: dict[str, Any]) -> str:
        title = str(risk.get("title", "")).strip().lower()
        description = str(risk.get("description", "")).strip().lower()
        return f"{title}::{description}"

    def _fallback_risk_classification(
        self, summary: str, sources: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        for line in [item.strip("- ").strip() for item in summary.splitlines() if item.strip()]:
            category = "compliance" if "regulation" in line.lower() else "technical"
            risks.append(
                {
                    "title": line[:80],
                    "description": line,
                    "category": category,
                    "probability": 3,
                    "impact": 3,
                    "sources": sources,
                }
            )
        return risks

    # Helper methods

    async def _generate_risk_id(self) -> str:
        """Generate unique risk ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"RISK-{timestamp}"

    async def _generate_mitigation_plan_id(self) -> str:
        """Generate unique mitigation plan ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"MIT-{timestamp}"

    async def _extract_risks_from_documents(
        self, documents: list[dict[str, Any] | str]
    ) -> list[dict[str, Any]]:
        """Extract potential risks from documents using NLP."""
        extracted: list[dict[str, Any]] = []
        if self.risk_nlp_extractor:
            extracted.extend(self.risk_nlp_extractor.extract_risks(documents))
        if self.cognitive_search_service:
            extracted.extend(self.cognitive_search_service.extract_risks(documents))
        return extracted

    async def _prime_risk_extractor(self) -> None:
        training_documents = self.config.get("risk_nlp_training_documents") if self.config else None
        training_path = self.config.get("risk_nlp_training_path") if self.config else None
        documents: list[dict[str, Any] | str] = []

        if isinstance(training_documents, list):
            documents.extend(training_documents)

        if training_path:
            try:
                path = Path(training_path)
                if path.is_file():
                    if path.suffix.lower() == ".json":
                        documents.extend(json.loads(path.read_text()))
                    else:
                        documents.append(path.read_text())
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                documents = documents

        if documents:
            await self._train_risk_extractor(documents)

    async def _train_risk_extractor(self, documents: list[dict[str, Any] | str]) -> None:
        if self.risk_nlp_extractor and hasattr(self.risk_nlp_extractor, "train"):
            try:
                self.risk_nlp_extractor.train(documents)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                return

    async def _build_risk_features(self, risk: dict[str, Any]) -> dict[str, Any]:
        schedule_distribution = await self._fetch_schedule_baseline(risk.get("project_id"))
        financial_distribution = await self._fetch_financial_distribution(risk.get("project_id"))
        schedule_delay = schedule_distribution.get("mean_delay_days", 0) or 0
        cost_overrun = financial_distribution.get("mean_cost_overrun", 0) or 0
        baseline_duration = schedule_distribution.get("baseline_duration_days", 100) or 100
        baseline_cost = financial_distribution.get("baseline_cost", 1_000_000) or 1_000_000

        quality_score = risk.get("quality_score") or risk.get("quality_metrics", {}).get("score")
        resource_utilization = risk.get("resource_utilization") or risk.get(
            "resource_metrics", {}
        ).get("utilization")
        schedule_pressure = float(schedule_delay) / max(1.0, float(baseline_duration))
        cost_pressure = float(cost_overrun) / max(1.0, float(baseline_cost))
        quality_pressure = 1 - (float(quality_score) if quality_score is not None else 0.8)
        resource_pressure = float(resource_utilization) if resource_utilization is not None else 0.7

        return {
            "title": risk.get("title"),
            "description": risk.get("description"),
            "category": risk.get("category"),
            "risk_indicator": risk.get("probability", 3),
            "impact_indicator": risk.get("impact", 3),
            "schedule_pressure": round(schedule_pressure, 4),
            "cost_pressure": round(cost_pressure, 4),
            "quality_pressure": round(quality_pressure, 4),
            "resource_pressure": round(resource_pressure, 4),
            "baseline_duration_days": baseline_duration,
            "baseline_cost": baseline_cost,
        }

    async def _ensure_local_risk_models(self) -> None:
        if self._local_probability_model and self._local_impact_model:
            return
        if importlib.util.find_spec("sklearn") is None:
            return
        samples: list[list[float]] = []
        probability_targets: list[float] = []
        impact_targets: list[float] = []
        for risk in self.risk_register.values():
            features = await self._build_risk_features(risk)
            samples.append(
                [
                    features.get("schedule_pressure", 0.0),
                    features.get("cost_pressure", 0.0),
                    features.get("quality_pressure", 0.0),
                    features.get("resource_pressure", 0.0),
                    features.get("risk_indicator", 0.0),
                ]
            )
            probability_targets.append(float(risk.get("probability", 3)))
            impact_targets.append(float(risk.get("impact", 3)))
        if len(samples) < 4:
            return
        try:
            from sklearn.ensemble import GradientBoostingRegressor

            self._local_probability_model = GradientBoostingRegressor(random_state=42)
            self._local_probability_model.fit(samples, probability_targets)
            self._local_impact_model = GradientBoostingRegressor(random_state=42)
            self._local_impact_model.fit(samples, impact_targets)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            self._local_probability_model = None
            self._local_impact_model = None

    async def _resolve_mitigation_owner(
        self, risk: dict[str, Any], mitigation_data: dict[str, Any]
    ) -> str | None:
        if mitigation_data.get("responsible_person"):
            return mitigation_data.get("responsible_person")
        if self.resource_management_service:
            for method in ("assign_owner", "get_available_owner", "resolve_owner"):
                if hasattr(self.resource_management_service, method):
                    try:
                        owner = await getattr(self.resource_management_service, method)(risk)
                        if owner:
                            return owner
                    except (
                        ConnectionError,
                        TimeoutError,
                        ValueError,
                        KeyError,
                        TypeError,
                        RuntimeError,
                        OSError,
                    ):
                        continue
        return risk.get("owner")

    async def _create_mitigation_tasks(
        self,
        risk: dict[str, Any],
        tasks: list[dict[str, Any]],
        owner: str | None,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        if not tasks:
            return created
        for task in tasks:
            payload = {
                "title": task.get("title") or task.get("summary"),
                "description": task.get("description"),
                "priority": task.get("priority", "Medium"),
                "owner": task.get("owner") or owner,
                "due_date": task.get("due_date"),
                "labels": ["risk", risk.get("category", "risk")],
                "risk_id": risk.get("risk_id"),
                "project_id": risk.get("project_id"),
            }
            created.append({"status": "pending", **payload})

        for connector_type, service in self.project_management_services.items():
            try:
                result = await service.create_tasks(risk.get("project_id"), created)
                for task, response in zip(created, result):
                    task["status"] = response.get("status", "created")
                    task["external_id"] = response.get("task_id") or response.get("id")
                    task["system"] = connector_type
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                continue

        return created

    async def _initial_risk_assessment(self, risk_data: dict[str, Any]) -> dict[str, Any]:
        """Perform initial risk assessment."""
        # Use provided values or defaults
        probability = risk_data.get("probability", 3)
        impact = risk_data.get("impact", 3)
        score = probability * impact

        return {"probability": probability, "impact": impact, "score": score}

    async def _classify_risk_level(self, score: float) -> str:
        """Classify risk level based on score."""
        if score >= self.high_risk_threshold:
            return "High"
        elif score >= 5:
            return "Medium"
        else:
            return "Low"

    async def _predict_risk_metrics(self, risk: dict[str, Any]) -> dict[str, Any]:
        """Use ML to predict risk probability and impact."""
        features = await self._build_risk_features(risk)
        if self.ml_service:
            prediction = await self.ml_service.predict_classification(features)
            if prediction.get("status") == "predicted":
                result = prediction.get("result", {}) or {}
                probability = result.get("probability") or result.get("likelihood")
                impact = result.get("impact")
                if probability or impact:
                    return {
                        "probability": self._coerce_rating(
                            probability, fallback=risk.get("probability", 3)
                        ),
                        "impact": self._coerce_rating(impact, fallback=risk.get("impact", 3)),
                        "severity_score": result.get("severity_score"),
                    }
            if prediction.get("status") == "predicted_mock":
                mock_probability = features.get("risk_indicator", risk.get("probability", 3))
                mock_impact = features.get("impact_indicator", risk.get("impact", 3))
                return {
                    "probability": self._coerce_rating(
                        mock_probability, fallback=risk.get("probability", 3)
                    ),
                    "impact": self._coerce_rating(mock_impact, fallback=risk.get("impact", 3)),
                }

        if self._local_probability_model and self._local_impact_model:
            try:
                model_features = [
                    features.get("schedule_pressure", 0.0),
                    features.get("cost_pressure", 0.0),
                    features.get("quality_pressure", 0.0),
                    features.get("resource_pressure", 0.0),
                    features.get("risk_indicator", 0.0),
                ]
                probability_pred = float(self._local_probability_model.predict([model_features])[0])
                impact_pred = float(self._local_impact_model.predict([model_features])[0])
                return {
                    "probability": self._coerce_rating(
                        round(probability_pred), fallback=risk.get("probability", 3)
                    ),
                    "impact": self._coerce_rating(
                        round(impact_pred), fallback=risk.get("impact", 3)
                    ),
                }
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                pass

        history = self.risk_histories.get(risk.get("risk_id"), [])
        if history:
            probabilities = [
                entry.get("probability", risk.get("probability", 3))
                for entry in history
                if entry.get("probability") is not None
            ]
            impacts = [
                entry.get("impact", risk.get("impact", 3))
                for entry in history
                if entry.get("impact") is not None
            ]
            probability = round(sum(probabilities) / len(probabilities)) if probabilities else None
            impact = round(sum(impacts) / len(impacts)) if impacts else None
        else:
            probability = None
            impact = None

        if probability is None or impact is None:
            category = risk.get("category")
            category_risks = [
                r for r in self.risk_register.values() if r.get("category") == category
            ]
            if category_risks:
                probability_values = [
                    r.get("probability", 3)
                    for r in category_risks
                    if r.get("probability") is not None
                ]
                impact_values = [
                    r.get("impact", 3) for r in category_risks if r.get("impact") is not None
                ]
                if probability is None and probability_values:
                    probability = round(sum(probability_values) / len(probability_values))
                if impact is None and impact_values:
                    impact = round(sum(impact_values) / len(impact_values))

        probability = probability or risk.get("probability", 3)
        impact = impact or risk.get("impact", 3)
        return {"probability": probability, "impact": impact}

    async def _calculate_quantitative_impact(self, risk: dict[str, Any]) -> dict[str, Any]:
        """Calculate quantitative impact on schedule and cost."""
        project_id = risk.get("project_id")
        schedule_distribution = await self._fetch_schedule_baseline(project_id)
        financial_distribution = await self._fetch_financial_distribution(project_id)
        baseline_duration = schedule_distribution.get("baseline_duration_days", 100.0)
        baseline_cost = financial_distribution.get("baseline_cost", 1_000_000.0)
        probability = min(1.0, max(0.0, (risk.get("probability", 3) / 5)))
        impact_factor = risk.get("impact", 3) / 5
        schedule_variance = schedule_distribution.get("mean_delay_days")
        if schedule_variance is None:
            schedule_variance = baseline_duration * 0.1
        cost_variance = financial_distribution.get("mean_cost_overrun")
        if cost_variance is None:
            cost_variance = baseline_cost * 0.05
        expected_schedule = probability * impact_factor * schedule_variance
        expected_cost = probability * impact_factor * cost_variance
        return {
            "schedule_impact_days": round(expected_schedule, 2),
            "cost_impact": round(expected_cost, 2),
            "baseline_duration_days": baseline_duration,
            "baseline_cost": baseline_cost,
            "probability": probability,
            "impact_factor": impact_factor,
        }

    async def _recommend_mitigation_strategies(self, risk: dict[str, Any]) -> list[str]:
        """Recommend mitigation strategies from knowledge base."""
        base_strategies = [
            "Regular monitoring and reviews",
            "Allocate contingency reserves",
            "Implement early warning system",
        ]
        if self.knowledge_base_service:
            guidance = await self.knowledge_base_service.query_mitigations(risk)
            guidance_strategies = [item["strategy"] for item in guidance if item.get("strategy")]
            if guidance_strategies:
                return list(dict.fromkeys(guidance_strategies + base_strategies))
        return base_strategies

    async def _calculate_residual_risk(
        self, risk: dict[str, Any], mitigation_plan: dict[str, Any]
    ) -> float:
        """Calculate residual risk after mitigation."""
        original_score = risk.get("score", 0)

        # Apply reduction factor based on mitigation strategy
        reduction_factors = {"avoid": 0.9, "mitigate": 0.5, "transfer": 0.3, "accept": 0.0}

        reduction = reduction_factors.get(mitigation_plan.get("strategy", "accept"), 0.0)
        residual = original_score * (1 - reduction)

        return residual  # type: ignore

    async def _check_risk_triggers(self, risk: dict[str, Any]) -> dict[str, Any]:
        """Check if risk triggers have been activated."""
        triggers = risk.get("triggers") or []
        for trigger in triggers:
            threshold = trigger.get("threshold")
            current_value = trigger.get("current_value")
            status = trigger.get("status")
            if status == "triggered":
                return {
                    "triggered": True,
                    "trigger": trigger,
                    "new_score": min(25, risk.get("score", 0) + 2),
                }
            if threshold is not None and current_value is not None and current_value >= threshold:
                trigger["status"] = "triggered"
                return {
                    "triggered": True,
                    "trigger": trigger,
                    "new_score": min(25, risk.get("score", 0) + 2),
                }
        return {"triggered": False, "trigger": None, "new_score": risk.get("score")}

    async def _update_risk_from_trigger(
        self, risk: dict[str, Any], trigger_status: dict[str, Any]
    ) -> None:
        """Update risk probability/impact based on trigger."""
        # Increase probability when trigger activated
        risk["probability"] = min(5, risk.get("probability", 3) + 1)
        risk["score"] = risk["probability"] * risk.get("impact", 3)

    async def _perform_monte_carlo_simulation(
        self,
        project_id: str,
        risks: list[dict[str, Any]],
        iterations: int,
        schedule_distribution: dict[str, Any] | None = None,
        financial_distribution: dict[str, Any] | None = None,
    ) -> dict[str, list[float]]:
        """Perform Monte Carlo simulation."""
        if iterations <= 0:
            return {"schedule": [], "cost": []}

        schedule_distribution = schedule_distribution or {}
        financial_distribution = financial_distribution or {}
        baseline_schedule_days = float(schedule_distribution.get("baseline_duration_days", 100.0))
        baseline_cost = float(financial_distribution.get("baseline_cost", 1_000_000.0))
        numpy_spec = importlib.util.find_spec("numpy")
        if numpy_spec:
            import numpy as np

            probabilities = np.array(
                [min(1.0, max(0.0, (risk.get("probability", 3) / 5))) for risk in risks],
                dtype=float,
            )
            impact_levels = np.array([risk.get("impact", 3) for risk in risks], dtype=float)

            schedule_impact_days = impact_levels * (baseline_schedule_days * 0.1 / 5.0)
            cost_impact = impact_levels * (baseline_cost * 0.05 / 5.0)

            rng = np.random.default_rng()
            if risks:
                occurrences = rng.random((iterations, len(risks))) < probabilities
                schedule_adjustments = occurrences * schedule_impact_days
                cost_adjustments = occurrences * cost_impact
                schedule_results = baseline_schedule_days + schedule_adjustments.sum(axis=1)
                cost_results = baseline_cost + cost_adjustments.sum(axis=1)
            else:
                schedule_results = np.full(iterations, baseline_schedule_days, dtype=float)
                cost_results = np.full(iterations, baseline_cost, dtype=float)

            return {
                "schedule": schedule_results.tolist(),
                "cost": cost_results.tolist(),
            }

        schedule_results = []
        cost_results = []
        for _ in range(iterations):
            schedule = baseline_schedule_days
            cost = baseline_cost
            for risk in risks:
                probability = min(1.0, max(0.0, (risk.get("probability", 3) / 5)))
                impact = risk.get("impact", 3)
                if random.random() < probability:
                    schedule += impact * (baseline_schedule_days * 0.1 / 5.0)
                    cost += impact * (baseline_cost * 0.05 / 5.0)
            schedule_results.append(schedule)
            cost_results.append(cost)

        return {"schedule": schedule_results, "cost": cost_results}

    async def _calculate_percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def _get_mitigation_status(self, project_id: str | None) -> dict[str, Any]:
        """Get mitigation plan status summary."""
        plans = list(self.mitigation_plans.values())
        if self.db_service:
            try:
                plans = await self.db_service.query("mitigation_plans", limit=500)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                plans = plans
        if project_id:
            valid_risks = {
                risk_id
                for risk_id, risk in self.risk_register.items()
                if risk.get("project_id") == project_id
            }
            plans = [plan for plan in plans if plan.get("risk_id") in valid_risks]

        status_counts = {"planned": 0, "in_progress": 0, "completed": 0, "total_plans": len(plans)}
        for plan in plans:
            status = str(plan.get("status", "planned")).lower().replace(" ", "_")
            if status in status_counts:
                status_counts[status] += 1
        return status_counts

    async def _analyze_risk_sensitivity(self, risk: dict[str, Any]) -> dict[str, Any]:
        """Analyze sensitivity of outcomes to this risk."""
        quantitative = await self._calculate_quantitative_impact(risk)
        schedule = quantitative.get("schedule_impact_days", 0)
        cost = quantitative.get("cost_impact", 0)
        low_factor = 0.7
        high_factor = 1.3
        return {
            "score": risk.get("score", 0) * 2,
            "schedule_impact": schedule,
            "cost_impact": cost,
            "tornado_range": {
                "schedule_low": round(schedule * low_factor, 2),
                "schedule_high": round(schedule * high_factor, 2),
                "cost_low": round(cost * low_factor, 2),
                "cost_high": round(cost * high_factor, 2),
            },
        }

    async def _generate_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate summary risk report."""
        return {
            "report_type": "summary",
            "data": {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _generate_detailed_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate detailed risk report."""
        return {
            "report_type": "detailed",
            "data": {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _generate_mitigation_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate mitigation status report."""
        return {
            "report_type": "mitigation",
            "data": {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _map_rating_to_label(self, rating: Any) -> str:
        rating_map = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}
        try:
            value = int(float(rating))
        except (TypeError, ValueError):
            return "medium"
        return rating_map.get(value, "medium")

    async def _validate_risk_record(
        self, *, risk: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        impact_value = risk.get("impact")
        likelihood_value = risk.get("likelihood", risk.get("probability"))
        impact_map = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}
        likelihood_map = {1: "rare", 2: "unlikely", 3: "possible", 4: "likely", 5: "likely"}
        mapped_impact = impact_map.get(impact_value, impact_value)
        mapped_likelihood = likelihood_map.get(likelihood_value, likelihood_value)
        record = {
            "id": risk.get("risk_id"),
            "tenant_id": tenant_id,
            "title": risk.get("title"),
            "description": risk.get("description"),
            "impact": mapped_impact or "medium",
            "likelihood": mapped_likelihood or "possible",
            "status": risk.get("status", "open"),
            "owner": risk.get("owner"),
            "classification": risk.get("classification", "internal"),
            "created_at": risk.get("created_at"),
        }
        if risk.get("last_updated"):
            record["updated_at"] = risk.get("last_updated")
        errors = validate_against_schema(self.risk_schema_path, record)
        if errors:
            for error in errors:
                self.logger.warning("Risk schema error %s: %s", error.path, error.message)
        report = evaluate_quality_rules("risk", record)
        issues = [issue.__dict__ for issue in report.issues]
        if issues:
            for issue in issues:
                self.logger.warning(
                    "Risk data quality issue %s: %s", issue["rule_id"], issue["message"]
                )
        return {"is_valid": len(errors) == 0 and report.is_valid, "issues": issues}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Risk Management Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()
        if self.data_lake_manager and hasattr(self.data_lake_manager, "service_client"):
            service_client = getattr(self.data_lake_manager, "service_client")
            if service_client and hasattr(service_client, "close"):
                service_client.close()
        if self.synapse_manager and hasattr(self.synapse_manager, "synapse_client"):
            synapse_client = getattr(self.synapse_manager, "synapse_client")
            if synapse_client and hasattr(synapse_client, "close"):
                synapse_client.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "risk_identification",
            "risk_extraction_from_documents",
            "risk_classification",
            "risk_scoring",
            "risk_prioritization",
            "predictive_risk_modeling",
            "mitigation_planning",
            "mitigation_strategy_recommendation",
            "trigger_monitoring",
            "monte_carlo_simulation",
            "sensitivity_analysis",
            "correlation_analysis",
            "risk_matrix_generation",
            "risk_dashboards",
            "risk_reporting",
            "quantitative_risk_analysis",
            "external_risk_research",
            "risk_event_publishing",
            "knowledge_base_guidance",
            "pm_connector_risk_signals",
        ]

    def _initialize_project_management_services(self) -> dict[str, ProjectManagementService]:
        services: dict[str, ProjectManagementService] = {}
        connector_types = ["planview", "ms_project", "jira", "azure_devops"]
        for connector_type in connector_types:
            env_map = {
                "planview": "PLANVIEW_INSTANCE_URL",
                "ms_project": "MS_PROJECT_SITE_URL",
                "jira": "JIRA_INSTANCE_URL",
                "azure_devops": "AZURE_DEVOPS_ORG_URL",
            }
            if not (
                self.config.get("enable_all_pm_connectors") or os.getenv(env_map[connector_type])
            ):
                continue
            services[connector_type] = ProjectManagementService({"connector_type": connector_type})
        return services

    async def _register_triggers(self, risk_id: str, triggers: list[dict[str, Any]]) -> None:
        normalized = []
        for trigger in triggers:
            trigger_id = trigger.get("trigger_id") or f"TRG-{uuid.uuid4().hex[:8]}"
            trigger_record = {
                "trigger_id": trigger_id,
                "risk_id": risk_id,
                "type": trigger.get("type", "threshold"),
                "threshold": trigger.get("threshold"),
                "current_value": trigger.get("current_value"),
                "status": trigger.get("status", "monitoring"),
                "created_at": trigger.get("created_at") or datetime.now(timezone.utc).isoformat(),
            }
            normalized.append(trigger_record)
            self.triggers[trigger_id] = trigger_record
            if self.db_service:
                await self.db_service.store("risk_trigger_definitions", trigger_id, trigger_record)
        if normalized:
            await self._store_risk_dataset(
                "risk_trigger_definitions", normalized, domain="triggers"
            )

    async def _store_risk_dataset(
        self, dataset_type: str, payload: list[dict[str, Any]], *, domain: str
    ) -> dict[str, Any]:
        details: dict[str, Any] = {"dataset_type": dataset_type, "stored": False}
        if not payload:
            return details
        if self.data_lake_manager:
            details["data_lake"] = self.data_lake_manager.store_dataset(
                dataset_type, domain, payload
            )
        if self.synapse_manager:
            details["synapse"] = {
                "workspace": self.synapse_manager.workspace_name,
                "sql_pool": self.synapse_manager.sql_pool_name,
                "spark_pool": self.synapse_manager.spark_pool_name,
                "status": "queued",
            }
        details["stored"] = bool(details.get("data_lake") or details.get("synapse"))
        return details

    async def _publish_risk_event(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "payload": payload,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        self.risk_events.append(event)
        if self.event_bus:
            await self.event_bus.publish(event_type, payload)

    async def _offload_or_simulate(
        self,
        project_id: str,
        risks: list[dict[str, Any]],
        iterations: int,
        *,
        schedule_distribution: dict[str, Any],
        financial_distribution: dict[str, Any],
    ) -> dict[str, list[float]]:
        offload_result = await self._submit_simulation_job(
            project_id,
            risks,
            iterations,
            schedule_distribution=schedule_distribution,
            financial_distribution=financial_distribution,
        )
        if offload_result:
            return offload_result
        return await self._perform_monte_carlo_simulation(
            project_id,
            risks,
            iterations,
            schedule_distribution=schedule_distribution,
            financial_distribution=financial_distribution,
        )

    async def _submit_simulation_job(
        self,
        project_id: str,
        risks: list[dict[str, Any]],
        iterations: int,
        *,
        schedule_distribution: dict[str, Any],
        financial_distribution: dict[str, Any],
    ) -> dict[str, list[float]] | None:
        azure_batch_endpoint = self.simulation_offload.get("azure_batch_endpoint")
        databricks_endpoint = self.simulation_offload.get("databricks_endpoint")
        if not azure_batch_endpoint and not databricks_endpoint:
            return None
        payload = {
            "project_id": project_id,
            "iterations": iterations,
            "risks": risks,
            "schedule_distribution": schedule_distribution,
            "financial_distribution": financial_distribution,
        }
        endpoint = azure_batch_endpoint or databricks_endpoint
        response = await self._post_json(endpoint, payload) if endpoint else None
        if not response:
            return None
        results = response.get("results") if isinstance(response, dict) else None
        if isinstance(results, dict) and "schedule" in results and "cost" in results:
            return {
                "schedule": results.get("schedule", []),
                "cost": results.get("cost", []),
            }
        return None

    async def _fetch_schedule_baseline(self, project_id: str | None) -> dict[str, Any]:
        if project_id and project_id in self.latest_schedule_signals:
            return self.latest_schedule_signals[project_id]
        if isinstance(self.schedule_baseline_fixture, dict) and self.schedule_baseline_fixture:
            return self.schedule_baseline_fixture
        if not project_id or not self.schedule_agent_endpoint:
            return {"baseline_duration_days": 100.0}
        payload = {"action": "get_schedule_baseline", "project_id": project_id}
        response = await self._post_json(self.schedule_agent_endpoint, payload)
        if response:
            return response
        return {"baseline_duration_days": 100.0}

    async def _fetch_financial_distribution(self, project_id: str | None) -> dict[str, Any]:
        if project_id and project_id in self.latest_financial_signals:
            return self.latest_financial_signals[project_id]
        if (
            isinstance(self.financial_distribution_fixture, dict)
            and self.financial_distribution_fixture
        ):
            return self.financial_distribution_fixture
        if not project_id or not self.financial_agent_endpoint:
            return {"baseline_cost": 1_000_000.0}
        payload = {"action": "get_cost_distribution", "project_id": project_id}
        response = await self._post_json(self.financial_agent_endpoint, payload)
        if response:
            return response
        return {"baseline_cost": 1_000_000.0}

    async def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            req = url_request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with url_request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            return None

    async def _handle_schedule_baseline_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        if not project_id:
            return
        self.latest_schedule_signals[project_id] = payload

    async def _handle_schedule_delay_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        if not project_id:
            return
        self.latest_schedule_signals[project_id] = payload

    async def _handle_financial_update_event(self, payload: dict[str, Any]) -> None:
        project_id = payload.get("project_id")
        if not project_id:
            return
        self.latest_financial_signals[project_id] = payload

    async def _handle_cost_overrun_event(self, payload: dict[str, Any]) -> None:
        await self._evaluate_event_trigger(payload, trigger_type="cost_overrun")

    async def _handle_milestone_missed_event(self, payload: dict[str, Any]) -> None:
        await self._evaluate_event_trigger(payload, trigger_type="schedule_delay")

    async def _handle_quality_event(self, payload: dict[str, Any]) -> None:
        await self._evaluate_event_trigger(payload, trigger_type="quality_defect_rate")

    async def _handle_resource_utilization_event(self, payload: dict[str, Any]) -> None:
        await self._evaluate_event_trigger(payload, trigger_type="resource_utilization")

    async def _evaluate_event_trigger(self, payload: dict[str, Any], *, trigger_type: str) -> None:
        project_id = payload.get("project_id")
        if not project_id:
            return
        threshold_map = {
            "cost_overrun": self.risk_trigger_thresholds.get("cost_overrun_pct", 0.1),
            "schedule_delay": self.risk_trigger_thresholds.get("schedule_delay_days", 10),
            "quality_defect_rate": self.risk_trigger_thresholds.get("quality_defect_rate", 0.05),
            "resource_utilization": self.risk_trigger_thresholds.get("resource_utilization", 0.9),
        }
        value_map = {
            "cost_overrun": payload.get("overrun_pct")
            or payload.get("cost_overrun_pct")
            or payload.get("variance_pct"),
            "schedule_delay": payload.get("delay_days")
            or payload.get("slip_days")
            or payload.get("delay"),
            "quality_defect_rate": payload.get("defect_rate") or payload.get("quality_defect_rate"),
            "resource_utilization": payload.get("utilization")
            or payload.get("resource_utilization"),
        }
        threshold = threshold_map.get(trigger_type)
        current_value = value_map.get(trigger_type)
        if threshold is None or current_value is None:
            return
        if float(current_value) < float(threshold):
            return
        triggered = []
        for risk in self.risk_register.values():
            if risk.get("project_id") != project_id:
                continue
            await self._update_risk_from_trigger(
                risk,
                {
                    "triggered": True,
                    "trigger": {
                        "type": trigger_type,
                        "threshold": threshold,
                        "current_value": current_value,
                        "status": "triggered",
                    },
                    "new_score": min(25, risk.get("score", 0) + 2),
                },
            )
            triggered.append(
                {
                    "risk_id": risk.get("risk_id"),
                    "project_id": project_id,
                    "trigger_type": trigger_type,
                    "threshold": threshold,
                    "current_value": current_value,
                    "new_score": risk.get("score"),
                }
            )
        if triggered:
            await self._store_risk_dataset("risk_triggers", triggered, domain="triggers")
            for item in triggered:
                await self._publish_risk_event("risk.triggered", item)

    async def _collect_external_risk_signals(self, project_id: str) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for connector_type, service in self.project_management_services.items():
            try:
                tasks = await service.get_tasks(project_id, filters={"labels": ["risk"]}, limit=25)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                tasks = []
            for task in tasks:
                signals.append(
                    {
                        "source": connector_type,
                        "item_id": task.get("id") or task.get("key") or task.get("work_item_id"),
                        "summary": task.get("summary") or task.get("title") or task.get("name"),
                        "status": task.get("status"),
                        "risk_level": task.get("priority") or task.get("severity"),
                    }
                )
        return signals
