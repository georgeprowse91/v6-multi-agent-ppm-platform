"""
Agent 17: Change & Configuration Management Agent

Purpose:
Governs controlled introduction of changes to projects, programs and configuration items.
Ensures changes are assessed, approved, implemented and documented to minimize disruption
and preserve integrity. Maintains CMDB for project artifacts and infrastructure.

Specification: agents/operations-management/agent-17-change-configuration/README.md
"""

import importlib.util
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from urllib import parse, request

from agents.common.connector_integration import (
    DatabaseStorageService,
    DocumentManagementService,
    ITSMIntegrationService,
)
from agents.common.integration_services import NaiveBayesTextClassifier
from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore

from event_bus.service_bus import ServiceBusEventBus


@dataclass
class RepositoryReference:
    provider: str
    repo: str
    pull_request_id: str | None = None
    commit_id: str | None = None


class RepositoryIntegrationService:
    def __init__(self, logger: Any) -> None:
        self.logger = logger

    def _headers(self, provider: str) -> dict[str, str]:
        provider = provider.lower()
        if provider == "github":
            token = os.getenv("GITHUB_TOKEN")
            if token:
                return {"Authorization": f"token {token}"}
        if provider == "gitlab":
            token = os.getenv("GITLAB_TOKEN")
            if token:
                return {"PRIVATE-TOKEN": token}
        if provider in {"azure", "azure_repos", "azure_devops"}:
            token = os.getenv("AZURE_DEVOPS_TOKEN")
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    def _request(self, method: str, url: str, provider: str) -> dict[str, Any]:
        headers = self._headers(provider)
        if not headers:
            self.logger.warning("No auth token configured for %s", provider)
            return {"status": "unauthenticated", "url": url}
        try:
            req = request.Request(url, method=method, headers=headers)
            with request.urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return {"status": "ok", "data": json.loads(payload)}
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.warning("Repository request failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def fetch_repository_data(self, reference: RepositoryReference) -> dict[str, Any]:
        provider = reference.provider.lower()
        if provider == "github":
            url = f"https://api.github.com/repos/{reference.repo}"
        elif provider == "gitlab":
            project_id = parse.quote(reference.repo, safe="")
            url = f"https://gitlab.com/api/v4/projects/{project_id}"
        else:
            url = f"https://dev.azure.com/{reference.repo}/_apis/git/repositories?api-version=7.1"
        return self._request("GET", url, provider)

    def fetch_pull_request_status(self, reference: RepositoryReference) -> dict[str, Any]:
        if not reference.pull_request_id:
            return {"status": "missing_pr"}
        provider = reference.provider.lower()
        if provider == "github":
            url = (
                f"https://api.github.com/repos/{reference.repo}/pulls/{reference.pull_request_id}"
            )
        elif provider == "gitlab":
            project_id = parse.quote(reference.repo, safe="")
            url = (
                f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/"
                f"{reference.pull_request_id}"
            )
        else:
            url = (
                f"https://dev.azure.com/{reference.repo}/_apis/git/pullrequests/"
                f"{reference.pull_request_id}?api-version=7.1"
            )
        return self._request("GET", url, provider)

    def fetch_commit_diff(self, reference: RepositoryReference) -> dict[str, Any]:
        if not reference.commit_id:
            return {"status": "missing_commit"}
        provider = reference.provider.lower()
        if provider == "github":
            url = (
                f"https://api.github.com/repos/{reference.repo}/commits/{reference.commit_id}"
            )
        elif provider == "gitlab":
            project_id = parse.quote(reference.repo, safe="")
            url = (
                f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits/"
                f"{reference.commit_id}"
            )
        else:
            url = (
                f"https://dev.azure.com/{reference.repo}/_apis/git/repositories/"
                f"commits/{reference.commit_id}?api-version=7.1"
            )
        return self._request("GET", url, provider)


class IaCChangeParser:
    def __init__(self, logger: Any) -> None:
        self.logger = logger

    def parse_files(self, file_paths: Iterable[Path]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for file_path in file_paths:
            if not file_path.exists():
                continue
            if file_path.suffix in {".tf", ".tfvars"}:
                resources.extend(self._parse_terraform(file_path))
            elif file_path.suffix in {".json"}:
                resources.extend(self._parse_arm(file_path))
            elif file_path.suffix in {".bicep"}:
                resources.extend(self._parse_bicep(file_path))
        return resources

    def _parse_terraform(self, file_path: Path) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        spec = importlib.util.find_spec("terraform_config_inspect")
        if spec:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            tf_module = module.Module.load(str(file_path.parent))
            for resource_type, blocks in tf_module.resources.items():
                for resource_name in blocks:
                    resources.append(
                        {
                            "resource_type": resource_type,
                            "resource_name": resource_name,
                            "source": str(file_path),
                        }
                    )
            return resources

        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("resource "):
                parts = line.replace("resource", "").replace('"', "").split()
                if len(parts) >= 2:
                    resources.append(
                        {
                            "resource_type": parts[0],
                            "resource_name": parts[1],
                            "source": str(file_path),
                        }
                    )
        return resources

    def _parse_arm(self, file_path: Path) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return resources
        for resource in payload.get("resources", []):
            resources.append(
                {
                    "resource_type": resource.get("type"),
                    "resource_name": resource.get("name"),
                    "source": str(file_path),
                }
            )
        return resources

    def _parse_bicep(self, file_path: Path) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("resource "):
                parts = line.replace("resource", "").replace("'", "").replace('"', "").split()
                if len(parts) >= 2:
                    resources.append(
                        {
                            "resource_type": parts[1],
                            "resource_name": parts[0],
                            "source": str(file_path),
                        }
                    )
        return resources


@dataclass
class ImpactTrainingSample:
    complexity: float
    historical_failure_rate: float
    affected_services: int
    risk_category: str
    success_probability: float


class ChangeImpactModel:
    def __init__(self) -> None:
        self._weights = {
            "complexity": 0.4,
            "failure_rate": 0.3,
            "services": 0.2,
            "risk_modifier": 0.1,
        }
        self._risk_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
        self._trained = False

    def train(self, samples: Iterable[ImpactTrainingSample]) -> None:
        samples_list = list(samples)
        if not samples_list:
            return
        avg_failure = sum(sample.historical_failure_rate for sample in samples_list) / len(
            samples_list
        )
        self._weights["failure_rate"] = 0.3 + min(0.2, avg_failure)
        self._trained = True

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        complexity = float(features.get("complexity", 1.0))
        failure_rate = float(features.get("historical_failure_rate", 0.1))
        affected_services = float(features.get("affected_services", 1))
        risk_category = str(features.get("risk_category", "medium")).lower()
        risk_modifier = self._risk_map.get(risk_category, 0.5)

        score = (
            complexity * self._weights["complexity"]
            + failure_rate * self._weights["failure_rate"]
            + affected_services * self._weights["services"]
            + risk_modifier * self._weights["risk_modifier"]
        )
        success_probability = max(0.05, min(0.95, 1.0 - score / 5))
        return {
            "impact_score": round(score, 2),
            "success_probability": round(success_probability, 2),
            "risk_category": risk_category,
        }


class ChangeWorkflowOrchestrator:
    def __init__(self, db_service: DatabaseStorageService, orchestrator: str) -> None:
        self.db_service = db_service
        self.orchestrator = orchestrator

    async def create_workflow(self, change_id: str, tenant_id: str) -> dict[str, Any]:
        workflow = {
            "change_id": change_id,
            "tenant_id": tenant_id,
            "orchestrator": self.orchestrator,
            "tasks": [
                {"name": "peer_review", "status": "pending"},
                {"name": "automated_checks", "status": "pending"},
                {"name": "final_approval", "status": "pending"},
            ],
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.db_service.store("change_workflows", change_id, workflow)
        return workflow


class ChangeEventPublisher:
    def __init__(self, config: dict[str, Any], logger: Any) -> None:
        self.logger = logger
        connection_string = config.get("connection_string") or os.getenv(
            "SERVICE_BUS_CONNECTION_STRING"
        )
        topic_name = config.get("topic_name", "ppm-events")
        self._event_bus = (
            ServiceBusEventBus(connection_string=connection_string, topic_name=topic_name)
            if connection_string
            else None
        )
        self._published_ids: set[str] = set()
        self._event_log: list[dict[str, Any]] = []

    async def publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        event_id = payload.get("event_id")
        if event_id and event_id in self._published_ids:
            self.logger.info("Skipping duplicate event: %s", event_id)
            return
        if event_id:
            self._published_ids.add(event_id)
        self._event_log.append({"topic": topic, "payload": payload})
        if self._event_bus:
            await self._event_bus.publish(topic, payload)

    def get_event_log(self) -> list[dict[str, Any]]:
        return list(self._event_log)


class DependencyGraphService:
    def __init__(self, logger: Any, config: dict[str, Any] | None = None) -> None:
        self.logger = logger
        self.config = config or {}
        self._adjacency: dict[str, list[str]] = {}
        self._driver = None
        if importlib.util.find_spec("neo4j"):
            uri = self.config.get("uri")
            user = self.config.get("username")
            password = self.config.get("password")
            if uri and user and password:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def load_cmdb(self, cmdb: dict[str, Any]) -> None:
        adjacency: dict[str, list[str]] = {}
        for ci_id, ci in cmdb.items():
            adjacency.setdefault(ci_id, [])
            for rel in ci.get("relationships", []):
                target_id = rel.get("target_ci_id")
                if target_id:
                    adjacency[ci_id].append(target_id)
        self._adjacency = adjacency

    def get_impacted(self, ci_ids: Iterable[str]) -> list[str]:
        visited: set[str] = set()
        queue = list(ci_ids)
        impacted: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adjacency.get(current, []):
                impacted.add(neighbor)
                if neighbor not in visited:
                    queue.append(neighbor)
        return sorted(impacted)

    def root_cause(self, ci_id: str) -> list[str]:
        if not self._driver:
            return [ci_id]
        with self._driver.session() as session:
            result = session.run(
                "MATCH (n {ci_id: $ci_id})<-[:DEPENDS_ON*]-(root) RETURN root.ci_id",
                ci_id=ci_id,
            )
            return [record[0] for record in result]


class ChangeRequestClassifier:
    def __init__(self, labels: list[str]) -> None:
        self.labels = labels
        self.model = NaiveBayesTextClassifier(labels=labels)

    def train(self, samples: list[tuple[str, str]]) -> None:
        self.model.fit(samples)

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        return self.model.predict(text)


class ApprovalFallbackAgent:
    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": "approval-fallback", "status": "pending"}


class ChangeConfigurationAgent(BaseAgent):
    """
    Change & Configuration Management Agent - Manages changes and configuration items.

    Key Capabilities:
    - Change request intake and classification
    - Impact assessment and risk evaluation
    - Approval workflow orchestration
    - Configuration management database (CMDB)
    - Baseline and version control
    - Change implementation tracking
    - Change audit and history
    - Configuration visualization and dependency mapping
    """

    def __init__(self, agent_id: str = "agent_017", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.change_types = (
            config.get("change_types", ["normal", "standard", "emergency"])
            if config
            else ["normal", "standard", "emergency"]
        )

        self.priority_levels = (
            config.get("priority_levels", ["critical", "high", "medium", "low"])
            if config
            else ["critical", "high", "medium", "low"]
        )

        self.baseline_threshold = config.get("baseline_threshold", 0.10) if config else 0.10
        self.approval_priority_thresholds = (
            config.get("approval_priority_thresholds", ["critical", "high"])
            if config
            else ["critical", "high"]
        )
        self.approval_change_types = (
            config.get("approval_change_types", ["normal", "emergency"])
            if config
            else ["normal", "emergency"]
        )

        change_store_path = (
            Path(config.get("change_store_path", "data/change_requests.json"))
            if config
            else Path("data/change_requests.json")
        )
        cmdb_store_path = (
            Path(config.get("cmdb_store_path", "data/cmdb.json"))
            if config
            else Path("data/cmdb.json")
        )
        self.change_store = TenantStateStore(change_store_path)
        self.cmdb_store = TenantStateStore(cmdb_store_path)

        # Data stores (will be replaced with database)
        self.change_requests: dict[str, Any] = {}
        self.cmdb: dict[str, Any] = {}  # Configuration items
        self.baselines: dict[str, Any] = {}
        self.change_history: dict[str, Any] = {}
        self.cab_meetings: dict[str, Any] = {}
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config", {}) if config else {}
            if importlib.util.find_spec("msal"):
                from approval_workflow_agent import ApprovalWorkflowAgent

                self.approval_agent = ApprovalWorkflowAgent(config=approval_config)
            else:
                self.approval_agent = ApprovalFallbackAgent()

        self.event_publisher = config.get("event_publisher") if config else None
        self.dependency_graph = config.get("dependency_graph") if config else None
        self.document_service = None
        self.repo_service = None
        self.iac_parser = None
        self.workflow_orchestrator = None
        self.impact_model = None
        self.text_classifier = None

    async def initialize(self) -> None:
        """Initialize database connections, ITSM integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Change & Configuration Management Agent...")

        # Initialize Database Storage Service (Azure SQL, Cosmos DB, or JSON fallback)
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

        # Initialize ITSM Integration Service (ServiceNow, Jira Service Management, BMC Remedy)
        itsm_config = self.config.get("itsm_integration", {}) if self.config else {}
        self.itsm_service = ITSMIntegrationService(itsm_config)
        self.logger.info("ITSM Integration Service initialized")

        # Initialize change classification model
        self.text_classifier = ChangeRequestClassifier(labels=self.change_types)
        training_samples = (
            self.config.get("change_classification_samples", [])
            if self.config
            else []
        )
        if not training_samples:
            training_samples = [
                ("emergency fix for production outage", "emergency"),
                ("critical security patch rollout", "emergency"),
                ("routine maintenance window update", "standard"),
                ("standard patching for monthly updates", "standard"),
                ("feature enhancement request", "normal"),
                ("configuration change for new capability", "normal"),
            ]
        self.text_classifier.train(training_samples)
        self.logger.info("Change classification model initialized")

        self.repo_service = RepositoryIntegrationService(self.logger)
        self.iac_parser = IaCChangeParser(self.logger)
        orchestrator = "durable_functions"
        if self.config and self.config.get("workflow_orchestrator"):
            orchestrator = self.config["workflow_orchestrator"]
        self.workflow_orchestrator = ChangeWorkflowOrchestrator(self.db_service, orchestrator)

        impact_samples = self.config.get("impact_model_samples", []) if self.config else []
        if not impact_samples:
            impact_samples = [
                ImpactTrainingSample(2.0, 0.1, 3, "medium", 0.85),
                ImpactTrainingSample(4.0, 0.3, 8, "high", 0.6),
                ImpactTrainingSample(1.0, 0.05, 1, "low", 0.92),
            ]
        normalized_samples: list[ImpactTrainingSample] = []
        for sample in impact_samples:
            if isinstance(sample, ImpactTrainingSample):
                normalized_samples.append(sample)
            elif isinstance(sample, dict):
                normalized_samples.append(
                    ImpactTrainingSample(
                        sample.get("complexity", 1.0),
                        sample.get("historical_failure_rate", 0.1),
                        sample.get("affected_services", 1),
                        sample.get("risk_category", "medium"),
                        sample.get("success_probability", 0.8),
                    )
                )
        self.impact_model = ChangeImpactModel()
        self.impact_model.train(normalized_samples)

        if not self.document_service:
            document_config = self.config.get("document_management", {}) if self.config else {}
            self.document_service = DocumentManagementService(document_config)

        if not self.event_publisher:
            event_config = self.config.get("event_bus", {}) if self.config else {}
            self.event_publisher = ChangeEventPublisher(event_config, self.logger)

        if not self.dependency_graph:
            graph_config = self.config.get("graph", {}) if self.config else {}
            self.dependency_graph = DependencyGraphService(self.logger, graph_config)
        self.dependency_graph.load_cmdb(self.cmdb)

        self.logger.info("Change & Configuration Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "submit_change_request",
            "classify_change",
            "assess_impact",
            "predict_impact",
            "approve_change",
            "rollback_change",
            "register_ci",
            "create_baseline",
            "track_change_implementation",
            "audit_changes",
            "visualize_dependencies",
            "get_change_dashboard",
            "generate_change_report",
            "get_change_metrics",
            "cicd_webhook",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "submit_change_request":
            change_data = input_data.get("change", {})
            required_fields = ["title", "description", "requester"]
            for field in required_fields:
                if field not in change_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process change and configuration management requests.

        Args:
            input_data: {
                "action": "submit_change_request" | "classify_change" | "assess_impact" |
                          "approve_change" | "register_ci" | "create_baseline" |
                          "track_change_implementation" | "audit_changes" |
                          "visualize_dependencies" | "get_change_dashboard" |
                          "generate_change_report",
                "change": Change request data,
                "ci": Configuration item data,
                "baseline": Baseline data,
                "change_id": Change request ID,
                "ci_id": Configuration item ID,
                "filters": Query filters
            }

        Returns:
            Response based on action
        """
        action = input_data.get("action", "get_change_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "submit_change_request":
            return await self._submit_change_request(
                input_data.get("change", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "classify_change":
            return await self._classify_change(input_data.get("change_id"))  # type: ignore

        elif action == "assess_impact":
            return await self._assess_impact(input_data.get("change_id"))  # type: ignore

        elif action == "predict_impact":
            return await self._predict_impact(input_data.get("change", {}))

        elif action == "approve_change":
            return await self._approve_change(
                input_data.get("change_id"), input_data.get("approval", {})  # type: ignore
            )

        elif action == "rollback_change":
            return await self._rollback_change(
                input_data.get("change_id"), input_data.get("reason", "")  # type: ignore
            )

        elif action == "register_ci":
            return await self._register_ci(
                input_data.get("ci", {}),
                tenant_id=tenant_id,
            )

        elif action == "create_baseline":
            return await self._create_baseline(input_data.get("baseline", {}))

        elif action == "track_change_implementation":
            return await self._track_change_implementation(input_data.get("change_id"))  # type: ignore

        elif action == "audit_changes":
            return await self._audit_changes(input_data.get("filters", {}))

        elif action == "visualize_dependencies":
            return await self._visualize_dependencies(input_data.get("ci_id"))

        elif action == "get_change_dashboard":
            return await self._get_change_dashboard(input_data.get("filters", {}))

        elif action == "generate_change_report":
            return await self._generate_change_report(
                input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        elif action == "get_change_metrics":
            return await self._get_change_metrics(input_data.get("filters", {}))

        elif action == "cicd_webhook":
            return await self._handle_cicd_webhook(input_data.get("payload", {}))

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _submit_change_request(
        self,
        change_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """Submit change request."""
        self.logger.info(f"Submitting change request: {change_data.get('title')}")

        # Generate change ID
        change_id = await self._generate_change_id()

        # Auto-classify change type
        change_type = await self._auto_classify_change_type(change_data)

        iac_changes = await self._analyze_iac_changes(change_data)

        # Identify impacted CIs
        impacted_cis = await self._identify_impacted_cis(change_data)

        approval_required = await self._requires_approval(change_type, change_data)
        approval_payload = None
        if approval_required:
            approval_payload = await self.approval_agent.process(
                {
                    "request_type": "scope_change",
                    "request_id": change_id,
                    "requester": change_data.get("requester", actor_id),
                    "details": {
                        "description": change_data.get("description"),
                        "urgency": change_data.get("priority", "medium"),
                        "impact": change_data.get("impact", "medium"),
                    },
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                }
            )

        repo_context = await self._retrieve_repo_context(change_data)
        knowledge_context = await self._retrieve_context_documents(change_data)
        workflow = await self.workflow_orchestrator.create_workflow(change_id, tenant_id)

        # Create change request
        change = {
            "change_id": change_id,
            "title": change_data.get("title"),
            "description": change_data.get("description"),
            "type": change_type,
            "priority": change_data.get("priority", "medium"),
            "requester": change_data.get("requester"),
            "project_id": change_data.get("project_id"),
            "impacted_cis": impacted_cis,
            "impact_assessment": None,
            "risk_assessment": None,
            "approval_status": "Pending" if approval_required else "Approved",
            "approval": approval_payload,
            "status": "Submitted",
            "created_at": datetime.utcnow().isoformat(),
            "repository_context": repo_context,
            "iac_changes": iac_changes,
            "knowledge_context": knowledge_context,
            "workflow": workflow,
        }

        # Store change
        self.change_requests[change_id] = change
        self.change_store.upsert(tenant_id, change_id, change)

        itsm_payload = {
            "title": change.get("title"),
            "description": change.get("description"),
            "priority": change.get("priority"),
            "requester": change.get("requester"),
            "status": change.get("status"),
        }
        change["itsm_record"] = await self.itsm_service.create_change_request(itsm_payload)
        await self.db_service.store("change_requests", change_id, change)

        await self._publish_event(
            "change.created",
            {
                "event_id": f"change.created:{change_id}",
                "change_id": change_id,
                "tenant_id": tenant_id,
                "status": change["status"],
            },
        )

        return {
            "change_id": change_id,
            "type": change_type,
            "status": "Submitted",
            "impacted_cis": len(impacted_cis),
            "approval_required": approval_required,
            "approval": approval_payload,
            "next_steps": "Impact assessment will be performed",
        }

    async def _classify_change(self, change_id: str) -> dict[str, Any]:
        """Classify change request using AI."""
        self.logger.info(f"Classifying change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        description = f"{change.get('title', '')} {change.get('description', '')}".strip()
        classification, confidence = self.text_classifier.predict(description)

        # Update change
        change["type"] = classification
        change["routing"] = await self._determine_routing(classification)
        change["classification_confidence"] = confidence.get(classification, 0.0)
        await self.db_service.store("change_requests", change_id, change)

        return {
            "change_id": change_id,
            "type": classification,
            "routing": change["routing"],
            "confidence": change["classification_confidence"],
        }

    async def _assess_impact(self, change_id: str) -> dict[str, Any]:
        """Assess change impact."""
        self.logger.info(f"Assessing impact for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Consult other agents for impact
        # Future work: Call Schedule, Resource, Financial agents
        schedule_impact = await self._assess_schedule_impact(change)
        cost_impact = await self._assess_cost_impact(change)
        resource_impact = await self._assess_resource_impact(change)
        risk_impact = await self._assess_risk_impact(change)

        # Analyze CI dependencies
        dependency_impact = await self._analyze_dependency_impact(change)

        # Predict change impact using AI
        # Future work: Use Azure ML for impact prediction
        predicted_impact = await self._predict_change_impact(change)

        impact_assessment = {
            "schedule_impact": schedule_impact,
            "cost_impact": cost_impact,
            "resource_impact": resource_impact,
            "risk_impact": risk_impact,
            "dependency_impact": dependency_impact,
            "predicted_impact": predicted_impact,
            "overall_risk_score": await self._calculate_overall_risk(
                schedule_impact, cost_impact, risk_impact
            ),
            "assessed_at": datetime.utcnow().isoformat(),
        }

        # Update change
        change["impact_assessment"] = impact_assessment

        await self.db_service.store("change_requests", change_id, change)

        return {
            "change_id": change_id,
            "impact_assessment": impact_assessment,
            "recommendation": await self._generate_impact_recommendation(impact_assessment),
        }

    async def _approve_change(
        self, change_id: str, approval_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Approve or reject change."""
        self.logger.info(f"Processing approval for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Record approval/rejection
        decision = approval_data.get("decision", "approve")
        approver = approval_data.get("approver")
        comments = approval_data.get("comments", "")

        change["approval_status"] = "Approved" if decision == "approve" else "Rejected"
        change["approved_by"] = approver
        change["approval_date"] = datetime.utcnow().isoformat()
        change["approval_comments"] = comments

        if decision == "approve":
            change["status"] = "Approved"
        else:
            change["status"] = "Rejected"

        await self.db_service.store("change_requests", change_id, change)

        itsm_record = change.get("itsm_record", {})
        itsm_id = itsm_record.get("change_id") if isinstance(itsm_record, dict) else None
        if itsm_id:
            await self.itsm_service.update_ticket(
                itsm_id,
                {"status": change["status"], "approval_status": change["approval_status"]},
            )
        await self._publish_event(
            "change.approved" if decision == "approve" else "change.rejected",
            {
                "event_id": f"change.{decision}:{change_id}",
                "change_id": change_id,
                "status": change["status"],
                "approved_by": approver,
            },
        )

        return {
            "change_id": change_id,
            "approval_status": change["approval_status"],
            "approved_by": approver,
            "next_steps": (
                "Proceed with implementation" if decision == "approve" else "Review and resubmit"
            ),
        }

    async def _register_ci(
        self,
        ci_data: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Register configuration item in CMDB."""
        self.logger.info(f"Registering CI: {ci_data.get('name')}")

        # Generate CI ID
        ci_id = await self._generate_ci_id()

        # Create CI entry
        ci = {
            "ci_id": ci_id,
            "name": ci_data.get("name"),
            "type": ci_data.get("type"),  # hardware, software, document, requirement
            "version": ci_data.get("version", "1.0"),
            "owner": ci_data.get("owner"),
            "status": ci_data.get("status", "active"),
            "project_id": ci_data.get("project_id"),
            "relationships": ci_data.get("relationships", []),
            "attributes": ci_data.get("attributes", {}),
            "created_at": datetime.utcnow().isoformat(),
            "last_modified": datetime.utcnow().isoformat(),
        }

        # Store CI
        self.cmdb[ci_id] = ci
        self.cmdb_store.upsert(tenant_id, ci_id, ci)

        await self.db_service.store("configuration_items", ci_id, ci)
        if self.dependency_graph:
            self.dependency_graph.load_cmdb(self.cmdb)

        return {"ci_id": ci_id, "name": ci["name"], "type": ci["type"], "version": ci["version"]}

    async def _create_baseline(self, baseline_data: dict[str, Any]) -> dict[str, Any]:
        """Create configuration baseline."""
        self.logger.info(f"Creating baseline: {baseline_data.get('description')}")

        # Generate baseline ID
        baseline_id = await self._generate_baseline_id()

        # Snapshot current CI versions
        ci_ids = baseline_data.get("ci_ids", [])
        ci_snapshot = {}
        for ci_id in ci_ids:
            ci = self.cmdb.get(ci_id)
            if ci:
                ci_snapshot[ci_id] = {
                    "name": ci.get("name"),
                    "version": ci.get("version"),
                    "attributes": ci.get("attributes", {}).copy(),
                }

        # Create baseline
        baseline = {
            "baseline_id": baseline_id,
            "project_id": baseline_data.get("project_id"),
            "description": baseline_data.get("description"),
            "ci_snapshot": ci_snapshot,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": baseline_data.get("created_by", "unknown"),
            "locked": True,
        }

        # Store baseline
        self.baselines[baseline_id] = baseline

        await self.db_service.store("baselines", baseline_id, baseline)

        return {
            "baseline_id": baseline_id,
            "description": baseline["description"],
            "ci_count": len(ci_snapshot),
            "created_at": baseline["created_at"],
        }

    async def _track_change_implementation(self, change_id: str) -> dict[str, Any]:
        """Track change implementation progress."""
        self.logger.info(f"Tracking implementation for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Get implementation tasks
        # Future work: Integrate with task management system
        implementation_tasks = await self._get_implementation_tasks(change_id)

        # Calculate completion percentage
        total_tasks = len(implementation_tasks)
        completed_tasks = sum(1 for t in implementation_tasks if t.get("status") == "completed")
        completion_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Update change status
        if completion_pct == 100:
            change["status"] = "Implemented"
            change["implemented_at"] = datetime.utcnow().isoformat()

        return {
            "change_id": change_id,
            "status": change["status"],
            "completion_percentage": completion_pct,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "implementation_tasks": implementation_tasks,
        }

    async def _audit_changes(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Audit change history."""
        self.logger.info("Auditing changes")

        # Filter changes
        changes_to_audit = []
        for change_id, change in self.change_requests.items():
            if await self._matches_filters(change, filters):
                changes_to_audit.append(change)

        # Analyze change patterns
        patterns = await self._analyze_change_patterns(changes_to_audit)

        return {
            "total_changes": len(changes_to_audit),
            "approved_changes": len(
                [c for c in changes_to_audit if c.get("approval_status") == "Approved"]
            ),
            "rejected_changes": len(
                [c for c in changes_to_audit if c.get("approval_status") == "Rejected"]
            ),
            "emergency_changes": len([c for c in changes_to_audit if c.get("type") == "emergency"]),
            "patterns": patterns,
            "audit_date": datetime.utcnow().isoformat(),
        }

    async def _visualize_dependencies(self, ci_id: str | None) -> dict[str, Any]:
        """Visualize CI dependencies."""
        self.logger.info(f"Visualizing dependencies for CI: {ci_id}")

        # Get CI and its dependencies
        if ci_id:
            ci = self.cmdb.get(ci_id)
            if not ci:
                raise ValueError(f"CI not found: {ci_id}")

            # Build dependency graph
            dependency_graph = await self._build_dependency_graph(ci_id)
        else:
            # Get full CMDB graph
            dependency_graph = await self._build_full_cmdb_graph()

        return {
            "ci_id": ci_id,
            "dependency_graph": dependency_graph,
            "node_count": len(dependency_graph.get("nodes", [])),
            "edge_count": len(dependency_graph.get("edges", [])),
        }

    async def _get_change_dashboard(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Get change dashboard data."""
        self.logger.info("Getting change dashboard")

        # Get open changes
        open_changes = []
        for change_id, change in self.change_requests.items():
            if change.get("status") in ["Submitted", "Approved", "In Progress"]:
                if await self._matches_filters(change, filters):
                    open_changes.append(change)

        # Get change statistics
        stats = await self._calculate_change_statistics(filters)

        # Get CAB workload
        cab_workload = await self._calculate_cab_workload()

        return {
            "open_changes": len(open_changes),
            "change_statistics": stats,
            "cab_workload": cab_workload,
            "recent_changes": open_changes[:10],
            "dashboard_generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_change_report(
        self, report_type: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate change management report."""
        self.logger.info(f"Generating {report_type} change report")

        if report_type == "summary":
            return await self._generate_summary_report(filters)
        elif report_type == "audit":
            return await self._audit_changes(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    async def _predict_impact(self, change_data: dict[str, Any]) -> dict[str, Any]:
        """Predict impact for ad-hoc change data."""
        if not self.impact_model:
            raise RuntimeError("Impact model is not initialized")
        prediction = self.impact_model.predict(change_data)
        mitigation = await self._recommend_mitigation(prediction)
        return {"prediction": prediction, "mitigation": mitigation}

    async def _rollback_change(self, change_id: str, reason: str) -> dict[str, Any]:
        """Rollback change and publish event."""
        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")
        change["status"] = "Rolled Back"
        change["rollback_reason"] = reason
        change["rolled_back_at"] = datetime.utcnow().isoformat()
        await self.db_service.store("change_requests", change_id, change)
        await self._publish_event(
            "change.rolled_back",
            {
                "event_id": f"change.rolled_back:{change_id}",
                "change_id": change_id,
                "status": change["status"],
                "reason": reason,
            },
        )
        return {"change_id": change_id, "status": change["status"], "reason": reason}

    async def _handle_cicd_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle CI/CD webhook payloads and update change status."""
        change_id = payload.get("change_id")
        if not change_id:
            return {"status": "ignored", "reason": "missing_change_id"}
        change = self.change_requests.get(change_id)
        if not change:
            return {"status": "ignored", "reason": "unknown_change_id"}
        deployment_status = payload.get("deployment_status", "unknown")
        change["deployment_status"] = deployment_status
        if deployment_status in {"succeeded", "failed"}:
            change["status"] = "Implemented" if deployment_status == "succeeded" else "Failed"
            change["implemented_at"] = (
                datetime.utcnow().isoformat()
                if deployment_status == "succeeded"
                else change.get("implemented_at")
            )
        await self.db_service.store("change_requests", change_id, change)
        await self._publish_event(
            "change.deployment",
            {
                "event_id": f"change.deployment:{change_id}:{deployment_status}",
                "change_id": change_id,
                "deployment_status": deployment_status,
            },
        )
        return {"status": "updated", "change_id": change_id, "deployment_status": deployment_status}

    async def _get_change_metrics(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Calculate trending metrics for change management."""
        changes = [c for c in self.change_requests.values() if await self._matches_filters(c, filters)]
        type_counts: dict[str, int] = {}
        approval_times: list[float] = []
        success_count = 0
        for change in changes:
            change_type = change.get("type", "unknown")
            type_counts[change_type] = type_counts.get(change_type, 0) + 1
            created_at = change.get("created_at")
            approved_at = change.get("approval_date")
            if created_at and approved_at:
                created_dt = datetime.fromisoformat(created_at)
                approved_dt = datetime.fromisoformat(approved_at)
                approval_times.append((approved_dt - created_dt).total_seconds() / 3600)
            if change.get("status") == "Implemented":
                success_count += 1
        average_approval_hours = (
            sum(approval_times) / len(approval_times) if approval_times else 0.0
        )
        success_rate = (success_count / len(changes)) if changes else 0.0
        return {
            "total_changes": len(changes),
            "change_type_counts": type_counts,
            "average_approval_time_hours": round(average_approval_hours, 2),
            "success_rate": round(success_rate, 2),
        }

    # Helper methods

    async def _generate_change_id(self) -> str:
        """Generate unique change ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CHG-{timestamp}"

    async def _generate_ci_id(self) -> str:
        """Generate unique CI ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CI-{timestamp}"

    async def _generate_baseline_id(self) -> str:
        """Generate unique baseline ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"BL-{timestamp}"

    async def _auto_classify_change_type(self, change_data: dict[str, Any]) -> str:
        """Auto-classify change type using NLP."""
        description = f"{change_data.get('title', '')} {change_data.get('description', '')}".strip()
        classification, _ = self.text_classifier.predict(description)
        return classification

    async def _identify_impacted_cis(self, change_data: dict[str, Any]) -> list[str]:
        """Identify impacted configuration items."""
        ci_ids = set(change_data.get("ci_ids", []))
        impacted_resources = change_data.get("impacted_resources", [])
        for ci_id, ci in self.cmdb.items():
            attributes = ci.get("attributes", {})
            resource_type = attributes.get("resource_type")
            resource_name = attributes.get("resource_name")
            for resource in impacted_resources:
                if (
                    resource_type == resource.get("resource_type")
                    and resource_name == resource.get("resource_name")
                ):
                    ci_ids.add(ci_id)
        if self.dependency_graph:
            impacted = self.dependency_graph.get_impacted(ci_ids)
            ci_ids.update(impacted)
        return sorted(ci_ids)

    async def _determine_routing(self, change_type: str) -> str:
        """Determine approval routing based on change type."""
        routing_map = {
            "emergency": "Emergency CAB",
            "standard": "Auto-Approved",
            "normal": "CAB Review",
        }
        return routing_map.get(change_type, "CAB Review")

    async def _requires_approval(self, change_type: str, change_data: dict[str, Any]) -> bool:
        priority = change_data.get("priority", "medium")
        return (
            change_type in self.approval_change_types
            or priority in self.approval_priority_thresholds
        )

    async def _assess_schedule_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Assess schedule impact of change."""
        # Future work: Integrate with Schedule Agent
        return {"impact_days": 0, "critical_path_affected": False}

    async def _assess_cost_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Assess cost impact of change."""
        # Future work: Integrate with Financial Agent
        return {"cost_variance": 0, "budget_available": True}

    async def _assess_resource_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Assess resource impact of change."""
        # Future work: Integrate with Resource Agent
        return {"resources_required": [], "availability": True}

    async def _assess_risk_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Assess risk impact of change."""
        # Future work: Integrate with Risk Management Agent
        return {"new_risks": [], "risk_score_increase": 0}

    async def _analyze_dependency_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Analyze CI dependency impact."""
        impacted_cis = change.get("impacted_cis", [])
        if not impacted_cis:
            return {"dependent_cis": [], "cascading_impact": False, "dependency_depth": 0}
        if self.dependency_graph:
            dependent_cis = self.dependency_graph.get_impacted(impacted_cis)
            return {
                "dependent_cis": dependent_cis,
                "cascading_impact": len(dependent_cis) > 0,
                "dependency_depth": len(dependent_cis),
            }
        return {"dependent_cis": [], "cascading_impact": False, "dependency_depth": 0}

    async def _predict_change_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Predict change impact using ML."""
        impacted_cis = change.get("impacted_cis", [])
        criticality_weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        complexity = 0.0
        for ci_id in impacted_cis:
            ci = self.cmdb.get(ci_id, {})
            criticality = str(ci.get("attributes", {}).get("criticality", "medium")).lower()
            complexity += criticality_weights.get(criticality, 2)
        complexity = max(complexity, 1.0)
        features = {
            "complexity": complexity,
            "historical_failure_rate": change.get("historical_failure_rate", 0.1),
            "affected_services": len(impacted_cis),
            "risk_category": change.get("risk_category", "medium"),
        }
        if not self.impact_model:
            raise RuntimeError("Impact model not initialized")
        prediction = self.impact_model.predict(features)
        mitigation = await self._recommend_mitigation(prediction)
        predicted_duration = max(1, int(prediction["impact_score"] * 2 + len(impacted_cis)))
        return {
            "success_probability": prediction["success_probability"],
            "predicted_duration": predicted_duration,
            "impact_score": prediction["impact_score"],
            "impacted_ci_count": len(impacted_cis),
            "risk_category": prediction["risk_category"],
            "mitigation": mitigation,
        }

    async def _calculate_overall_risk(
        self,
        schedule_impact: dict[str, Any],
        cost_impact: dict[str, Any],
        risk_impact: dict[str, Any],
    ) -> float:
        """Calculate overall risk score for change."""
        score = 0.0

        if schedule_impact.get("critical_path_affected"):
            score += 30

        if cost_impact.get("cost_variance", 0) > 10000:
            score += 20

        score += risk_impact.get("risk_score_increase", 0)

        return min(100, score)  # type: ignore

    async def _generate_impact_recommendation(self, impact_assessment: dict[str, Any]) -> str:
        """Generate recommendation based on impact assessment."""
        risk_score = impact_assessment.get("overall_risk_score", 0)

        if risk_score > 70:
            return "High risk change. Recommend detailed review by CAB and additional testing."
        elif risk_score > 40:
            return "Medium risk change. Recommend standard CAB review and testing."
        else:
            return "Low risk change. Can proceed with standard approval process."

    async def _recommend_mitigation(self, prediction: dict[str, Any]) -> list[str]:
        """Recommend mitigation steps based on impact prediction."""
        mitigations = ["Schedule change in maintenance window", "Prepare rollback plan"]
        if prediction.get("risk_category") in {"high", "critical"}:
            mitigations.extend(
                [
                    "Run enhanced security scanning",
                    "Perform additional peer review",
                    "Increase monitoring during deployment",
                ]
            )
        return mitigations

    async def _retrieve_repo_context(self, change_data: dict[str, Any]) -> dict[str, Any]:
        repo_provider = change_data.get("repo_provider")
        repo_slug = change_data.get("repo_slug")
        if not repo_provider or not repo_slug or not self.repo_service:
            return {"status": "unavailable"}
        reference = RepositoryReference(
            provider=repo_provider,
            repo=repo_slug,
            pull_request_id=change_data.get("pull_request_id"),
            commit_id=change_data.get("commit_id"),
        )
        return {
            "repository": self.repo_service.fetch_repository_data(reference),
            "pull_request": self.repo_service.fetch_pull_request_status(reference),
            "commit_diff": self.repo_service.fetch_commit_diff(reference),
        }

    async def _analyze_iac_changes(self, change_data: dict[str, Any]) -> dict[str, Any]:
        file_paths = [Path(path) for path in change_data.get("iac_files", [])]
        if not self.iac_parser or not file_paths:
            return {"resources": [], "status": "no_iac"}
        resources = self.iac_parser.parse_files(file_paths)
        change_data["impacted_resources"] = resources
        return {"resources": resources, "resource_count": len(resources)}

    async def _retrieve_context_documents(self, change_data: dict[str, Any]) -> dict[str, Any]:
        if not self.document_service:
            return {"documents": [], "status": "unavailable"}
        query = change_data.get("knowledge_query") or change_data.get("title")
        if not query:
            return {"documents": [], "status": "no_query"}
        documents = await self.document_service.list_documents(limit=25)
        filtered = [doc for doc in documents if query.lower() in str(doc.get("title", "")).lower()]
        return {"documents": filtered, "status": "ok"}

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_publisher:
            return
        await self.event_publisher.publish_event(topic, payload)

    async def _get_implementation_tasks(self, change_id: str) -> list[dict[str, Any]]:
        """Get implementation tasks for change."""
        # Future work: Query task management system
        return []

    async def _matches_filters(self, change: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if change matches filters."""
        if "status" in filters and change.get("status") != filters["status"]:
            return False

        if "type" in filters and change.get("type") != filters["type"]:
            return False

        return True

    async def _analyze_change_patterns(self, changes: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze patterns in changes."""
        # Future work: Perform pattern analysis
        return {
            "most_common_type": "normal",
            "average_approval_time_days": 3,
            "rejection_rate": 0.15,
        }

    async def _build_dependency_graph(self, ci_id: str) -> dict[str, Any]:
        """Build dependency graph for CI."""
        # Future work: Use graph algorithms
        return {"nodes": [{"id": ci_id, "label": "CI"}], "edges": []}

    async def _build_full_cmdb_graph(self) -> dict[str, Any]:
        """Build full CMDB dependency graph."""
        nodes = []
        edges = []

        for ci_id, ci in self.cmdb.items():
            nodes.append({"id": ci_id, "label": ci.get("name"), "type": ci.get("type")})

            for rel in ci.get("relationships", []):
                edges.append(
                    {
                        "source": ci_id,
                        "target": rel.get("target_ci_id"),
                        "type": rel.get("relationship_type"),
                    }
                )

        return {"nodes": nodes, "edges": edges}

    async def _calculate_change_statistics(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Calculate change statistics."""
        changes = [c for c in self.change_requests.values() if await self._matches_filters(c, filters)]
        total = len(changes)
        approved = len([c for c in changes if c.get("approval_status") == "Approved"])
        lead_times: list[float] = []
        for change in changes:
            created_at = change.get("created_at")
            implemented_at = change.get("implemented_at")
            if created_at and implemented_at:
                created_dt = datetime.fromisoformat(created_at)
                implemented_dt = datetime.fromisoformat(implemented_at)
                lead_times.append((implemented_dt - created_dt).total_seconds() / 3600)
        average_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0.0
        return {
            "total_changes": total,
            "approved_rate": round(approved / total, 2) if total else 0.0,
            "average_lead_time_hours": round(average_lead_time, 2),
        }

    async def _calculate_cab_workload(self) -> dict[str, Any]:
        """Calculate CAB workload."""
        pending_reviews = len(
            [
                change
                for change in self.change_requests.values()
                if change.get("approval_status") == "Pending"
            ]
        )
        return {
            "pending_reviews": pending_reviews,
            "next_meeting": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }

    async def _generate_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate summary change report."""
        return {"report_type": "summary", "data": {}, "generated_at": datetime.utcnow().isoformat()}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Change & Configuration Management Agent...")
        # Future work: Close database connections
        # Future work: Close ITSM connections
        # Future work: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "change_request_intake",
            "change_classification",
            "change_impact_prediction",
            "impact_assessment",
            "risk_evaluation",
            "approval_workflow_orchestration",
            "repository_integration",
            "iac_change_analysis",
            "cicd_webhook_tracking",
            "document_context_enrichment",
            "service_bus_eventing",
            "graph_dependency_analysis",
            "cmdb_management",
            "ci_registration",
            "baseline_management",
            "version_control",
            "change_implementation_tracking",
            "change_audit",
            "dependency_mapping",
            "configuration_visualization",
            "change_dashboards",
            "change_reporting",
            "change_metrics",
        ]
