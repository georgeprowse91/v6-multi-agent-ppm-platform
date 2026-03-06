"""
Compliance & Regulatory Agent

Purpose:
Ensures projects, programs and portfolios adhere to internal policies, external regulations
and industry standards. Manages compliance requirements, monitors adherence, and facilitates
audits and evidence collection.

Specification: agents/delivery-management/compliance-governance-agent/README.md
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from observability.tracing import get_trace_id

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from agents.common.web_search import search_web, summarize_snippets  # noqa: E402, F401

from compliance_actions import (  # noqa: E402
    handle_add_regulation,
    handle_assess_compliance,
    handle_conduct_audit,
    handle_define_control,
    handle_generate_compliance_report,
    handle_get_compliance_dashboard,
    handle_get_evidence,
    handle_get_report,
    handle_list_evidence,
    handle_list_reports,
    handle_manage_policy,
    handle_map_controls_to_project,
    handle_monitor_regulations,
    handle_monitor_regulatory_changes,
    handle_prepare_audit,
    handle_upload_evidence,
    handle_verify_release_compliance,
)

# -- Extracted modules -------------------------------------------------------
from compliance_models import ComplianceRuleEngine  # noqa: E402

# Re-export models so existing ``from compliance_regulatory_agent import …`` still works.
from compliance_models import (  # noqa: E402, F401
    ControlRequirement as ControlRequirement,
)
from compliance_models import (  # noqa: E402
    EvidenceSnapshot as EvidenceSnapshot,
)
from compliance_models import (  # noqa: E402
    RegulatoryFramework as RegulatoryFramework,
)
from compliance_seed import (  # noqa: E402
    define_compliance_schemas,
    extract_regulation_metadata,
    seed_regulatory_frameworks,
)
from llm.client import LLMGateway  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentManagementService,
    GRCIntegrationService,
    NotificationService,
)
from agents.runtime import BaseAgent, ServiceBusEventBus, get_event_bus  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.policy import (  # noqa: E402
    evaluate_compliance_controls,
    evaluate_policy_bundle,
    load_default_policy_bundle,
)
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402


class ComplianceRegulatoryAgent(BaseAgent):
    """
    Compliance & Regulatory Agent - Ensures adherence to policies and regulations.

    Key Capabilities:
    - Regulatory requirement management
    - Control library and mapping
    - Compliance assessment and gap analysis
    - Control assignment and testing
    - Policy management and versioning
    - Audit preparation and management
    - Compliance dashboards and reporting
    - Regulatory change monitoring
    """

    def __init__(
        self,
        agent_id: str = "compliance-governance-agent",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.regulations = (
            config.get(
                "regulations",
                ["Privacy Act 1988", "APRA CPS 234", "ISO 27001", "ASD ISM", "PSPF"],
            )
            if config
            else ["Privacy Act 1988", "APRA CPS 234", "ISO 27001", "ASD ISM", "PSPF"]
        )
        self.enable_regulatory_monitoring = (
            config.get("enable_regulatory_monitoring", False) if config else False
        )
        self.regulatory_search_keywords = (
            config.get(
                "regulatory_search_keywords",
                ["law", "regulation", "standard", "guidance", "compliance update"],
            )
            if config
            else ["law", "regulation", "standard", "guidance", "compliance update"]
        )
        self.regulatory_search_result_limit = (
            int(config.get("regulatory_search_result_limit", 5)) if config else 5
        )
        self.control_test_frequencies = (
            config.get(
                "control_test_frequencies",
                {"critical": "monthly", "high": "quarterly", "medium": "semi-annually", "low": "annually"},
            )
            if config
            else {"critical": "monthly", "high": "quarterly", "medium": "semi-annually", "low": "annually"}
        )

        evidence_store_path = (
            Path(config.get("evidence_store_path", "data/compliance_evidence.json"))
            if config
            else Path("data/compliance_evidence.json")
        )
        self.evidence_store = TenantStateStore(evidence_store_path)

        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            service_bus_connection = (
                config.get("service_bus_connection_string")
                if config
                else os.getenv("SERVICE_BUS_CONNECTION_STRING")
            )
            if service_bus_connection:
                try:
                    self.event_bus = ServiceBusEventBus(connection_string=service_bus_connection)
                except RuntimeError as exc:
                    self.logger.warning(
                        "Service bus event bus unavailable, falling back to in-memory",
                        extra={"error": str(exc)},
                    )
                    self.event_bus = get_event_bus()
            else:
                self.event_bus = get_event_bus()

        self.notification_service = NotificationService(
            config.get("notifications") if config else None
        )
        self.agent_clients = config.get("agent_clients", {}) if config else {}
        self.rule_engine = ComplianceRuleEngine()

        # Data stores
        self.regulation_library: dict[str, Any] = {}
        self.control_registry: dict[str, Any] = {}
        self.compliance_mappings: dict[str, Any] = {}
        self.policies: dict[str, Any] = {}
        self.audits: dict[str, Any] = {}
        self.evidence: dict[str, Any] = {}
        self.regulatory_changes: dict[str, Any] = {}
        self.control_embeddings: dict[str, dict[str, float]] = {}
        self.compliance_reports: dict[str, Any] = {}
        self.compliance_alerts: list[dict[str, Any]] = []
        self.compliance_schemas: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize database connections, GRC integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Compliance & Regulatory Agent...")

        doc_config = self.config.get("document_management", {}) if self.config else {}
        self.document_service = DocumentManagementService(doc_config)

        grc_config = self.config.get("grc_integration", {}) if self.config else {}
        self.grc_service = GRCIntegrationService(grc_config)

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)

        await seed_regulatory_frameworks(self)
        await define_compliance_schemas(self)

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            for topic in [
                "release.deployed", "deployment.completed", "config.changed",
                "quality.test.completed", "risk.updated", "security.alert",
                "incident.created", "change.requested",
            ]:
                self.event_bus.subscribe(topic, self._handle_compliance_event)  # type: ignore[arg-type]

        self.logger.info("Compliance & Regulatory Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "add_regulation", "define_control", "map_controls_to_project",
            "assess_compliance", "test_control", "manage_policy",
            "prepare_audit", "conduct_audit", "upload_evidence",
            "monitor_regulatory_changes", "get_compliance_dashboard",
            "generate_compliance_report", "verify_release_compliance",
            "list_evidence", "get_evidence", "list_reports", "get_report",
        ]
        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "define_control":
            control_data = input_data.get("control", {})
            for field in ["description", "regulation", "owner"]:
                if field not in control_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        return True

    # ------------------------------------------------------------------
    # Process dispatcher
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process compliance and regulatory requests.

        Delegates to action-specific handlers in the ``actions`` package.
        """
        action = input_data.get("action", "get_compliance_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        # -- compliance controls gate -----------------------------------
        compliance_decision = evaluate_compliance_controls({
            "personal_data": input_data.get("personal_data", {}),
            "consent": input_data.get("consent", {}),
        })
        if compliance_decision.decision == "deny":
            emit_audit_event(build_audit_event(
                tenant_id=tenant_id, action="compliance.data_processing.denied",
                outcome="denied", actor_id=self.agent_id, actor_type="service",
                actor_roles=[], resource_id=input_data.get("project_id") or "unknown",
                resource_type="compliance_processing",
                metadata={"reasons": list(compliance_decision.reasons)},
                legal_basis="consent", retention_period="P3Y",
                trace_id=get_trace_id(), correlation_id=correlation_id,
            ))
            return {
                "status": "error",
                "error": "Consent is required before processing personal data.",
                "reasons": list(compliance_decision.reasons),
            }

        input_data["personal_data"] = compliance_decision.sanitized_payload.get("personal_data", {})
        emit_audit_event(build_audit_event(
            tenant_id=tenant_id, action="compliance.data_processing.allowed",
            outcome="success", actor_id=self.agent_id, actor_type="service",
            actor_roles=[], resource_id=input_data.get("project_id") or "unknown",
            resource_type="compliance_processing",
            metadata={
                "masked_fields": list(compliance_decision.masked_fields),
                "reasons": list(compliance_decision.reasons),
            },
            legal_basis="consent", retention_period="P3Y",
            trace_id=get_trace_id(), correlation_id=correlation_id,
        ))

        # -- action dispatch --------------------------------------------
        if action == "add_regulation":
            return await handle_add_regulation(self, input_data.get("regulation", {}))
        elif action == "define_control":
            return await handle_define_control(self, input_data.get("control", {}))
        elif action == "map_controls_to_project":
            return await handle_map_controls_to_project(
                self, input_data.get("project_id"), input_data.get("mapping", {}),  # type: ignore
                tenant_id=tenant_id, correlation_id=correlation_id,
            )
        elif action == "assess_compliance":
            return await handle_assess_compliance(
                self, input_data.get("project_id"), input_data.get("assessment", {}),  # type: ignore
            )
        elif action == "test_control":
            from compliance_actions.test_control import handle_test_control
            return await handle_test_control(
                self, input_data.get("control_id"), input_data.get("test", {}),  # type: ignore
            )
        elif action == "manage_policy":
            return await handle_manage_policy(self, input_data.get("policy", {}))
        elif action == "prepare_audit":
            return await handle_prepare_audit(self, input_data.get("audit", {}))
        elif action == "conduct_audit":
            return await handle_conduct_audit(self, input_data.get("audit_id"))  # type: ignore
        elif action == "upload_evidence":
            return await handle_upload_evidence(
                self, input_data.get("control_id"), input_data.get("evidence", {}),  # type: ignore
                tenant_id=tenant_id, correlation_id=correlation_id,
            )
        elif action == "monitor_regulatory_changes":
            return await handle_monitor_regulatory_changes(
                self, domain=input_data.get("domain"), region=input_data.get("region"),
                tenant_id=tenant_id, correlation_id=correlation_id,
            )
        elif action == "get_compliance_dashboard":
            return await handle_get_compliance_dashboard(
                self, input_data.get("project_id"), input_data.get("portfolio_id"),
                domain=input_data.get("domain"), region=input_data.get("region"),
            )
        elif action == "generate_compliance_report":
            return await handle_generate_compliance_report(
                self, input_data.get("report_type", "summary"), input_data.get("filters", {}),
            )
        elif action == "verify_release_compliance":
            return await handle_verify_release_compliance(
                self, input_data.get("release_id"), input_data.get("release", {}),
            )
        elif action == "list_evidence":
            return await handle_list_evidence(self, input_data.get("filters", {}))
        elif action == "get_evidence":
            return await handle_get_evidence(self, input_data.get("evidence_id"))
        elif action == "list_reports":
            return await handle_list_reports(self, input_data.get("filters", {}))
        elif action == "get_report":
            return await handle_get_report(self, input_data.get("report_id"))
        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Public API kept on the class for backward-compat
    # ------------------------------------------------------------------

    async def monitor_regulations(
        self, domain: str, region: str | None, *,
        llm_client: LLMGateway | None = None, result_limit: int | None = None,
    ) -> dict[str, Any]:
        """Monitor external sources for new or changing regulations."""
        return await handle_monitor_regulations(
            self, domain, region, llm_client=llm_client, result_limit=result_limit,
        )

    async def _map_controls_to_project(
        self, project_id: str, mapping_data: dict[str, Any], *,
        tenant_id: str, correlation_id: str,
    ) -> dict[str, Any]:
        """Thin wrapper so action modules can call ``agent._map_controls_to_project``."""
        return await handle_map_controls_to_project(
            self, project_id, mapping_data, tenant_id=tenant_id, correlation_id=correlation_id,
        )

    async def _assess_compliance(
        self, project_id: str, assessment_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Thin wrapper preserving the original internal API."""
        return await handle_assess_compliance(self, project_id, assessment_data)

    async def _generate_compliance_report(
        self, report_type: str, filters: dict[str, Any],
    ) -> dict[str, Any]:
        """Thin wrapper preserving the original internal API."""
        return await handle_generate_compliance_report(self, report_type, filters)

    # ------------------------------------------------------------------
    # Shared internal helpers (used by multiple action modules)
    # ------------------------------------------------------------------

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        await self.event_bus.publish(topic, payload)

    async def _notify_stakeholders(self, *, subject: str, message: str) -> list[dict[str, Any]]:
        stakeholders = self.config.get("stakeholders", []) if self.config else []
        recipients = [
            s.get("email") for s in stakeholders if isinstance(s, dict) and s.get("email")
        ]
        if not recipients:
            recipients = [self.config.get("default_stakeholder_email", "compliance@example.com")]
        results = []
        for recipient in recipients:
            result = await self.notification_service.send_email(
                to=recipient, subject=subject, body=message, metadata={"category": "compliance"},
            )
            results.append(result)
        return results

    async def _create_stakeholder_tasks(
        self, updates: list[dict[str, Any]], tenant_id: str,
    ) -> list[dict[str, Any]]:
        stakeholders = self.config.get("stakeholders", []) if self.config else []
        recipients = [
            s.get("email") for s in stakeholders if isinstance(s, dict) and s.get("email")
        ]
        if not recipients:
            recipients = [self.config.get("default_stakeholder_email", "compliance@example.com")]
        tasks = []
        for update in updates:
            task_id = f"TASK-{uuid.uuid4().hex[:8]}"
            task = {
                "task_id": task_id, "tenant_id": tenant_id,
                "title": f"Review regulatory update: {update.get('regulation', 'Update')}",
                "description": update.get("description"),
                "regulation": update.get("regulation"),
                "effective_date": update.get("effective_date"),
                "assigned_to": recipients, "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_url": update.get("source_url"),
            }
            tasks.append(task)
            await self.db_service.store("compliance_tasks", task_id, task)
            await self._publish_event("compliance.task.created", task)
        return tasks

    async def _evaluate_control_mapping_policy(
        self, *, project_id: str, mapping: dict[str, Any],
        tenant_id: str, correlation_id: str,
    ) -> dict[str, Any]:
        policy_bundle = {
            "metadata": {
                "version": self.get_config("policy_version", "1.0.0"),
                "owner": self.get_config("policy_owner", self.agent_id),
                "name": mapping.get("mapping_id", project_id),
            },
            "project_id": project_id,
            "control_count": len(mapping.get("applicable_controls", [])),
            "regulation_count": len(mapping.get("applicable_regulations", [])),
        }
        decision = evaluate_policy_bundle(policy_bundle, load_default_policy_bundle())
        outcome = "denied" if decision.decision == "deny" else "success"
        emit_audit_event(build_audit_event(
            tenant_id=tenant_id, action="compliance.control_mapping.policy.checked",
            outcome=outcome, actor_id=self.agent_id, actor_type="service",
            actor_roles=[], resource_id=project_id, resource_type="compliance_mapping",
            metadata={"decision": decision.decision, "reasons": decision.reasons},
            trace_id=get_trace_id(), correlation_id=correlation_id,
        ))
        return {"decision": decision.decision, "reasons": decision.reasons}

    async def _extract_regulation_metadata(
        self, regulation_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Delegate to compliance_seed module."""
        return await extract_regulation_metadata(self, regulation_data)

    async def _extract_regulatory_updates(
        self,
        summary: str,
        snippets: list[str],
        *,
        llm_client: Any = None,
    ) -> list[dict[str, Any]]:
        """Extract regulatory updates from search snippets via LLM.

        Delegates to the module-level helper in ``compliance_actions.monitor_regulatory``
        so that callers can monkeypatch this method for testing.
        """
        from compliance_actions.monitor_regulatory import (
            _extract_regulatory_updates as _impl,
        )

        return await _impl(self, summary, snippets, llm_client=llm_client)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def _handle_compliance_event(self, event: dict[str, Any]) -> None:
        project_id = event.get("project_id")
        if not project_id:
            return
        assessment = await handle_assess_compliance(self, project_id, {
            "tenant_id": event.get("tenant_id", "unknown"),
            "correlation_id": event.get("correlation_id", str(uuid.uuid4())),
            "mapping": event.get("mapping", {}),
        })
        if assessment.get("gaps"):
            recommendations = [
                {"control_id": g.get("control_id"), "recommendation": g.get("remediation")}
                for g in assessment.get("gaps", [])
            ]
            alert = {
                "alert_id": f"ALERT-{uuid.uuid4().hex[:8]}",
                "project_id": project_id,
                "gaps": assessment.get("gaps", []),
                "compliance_score": assessment.get("compliance_score", 0),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "trigger": event.get("event_type") or event.get("type"),
                "recommendations": recommendations,
            }
            self.compliance_alerts.append(alert)
            await self.db_service.store("compliance_alerts", alert["alert_id"], alert)
            await self._publish_event("compliance.alert.raised", alert)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Compliance & Regulatory Agent...")
        self.logger.info("Compliance & Regulatory Agent cleanup complete")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "regulation_management", "regulation_parsing",
            "control_definition", "control_library_management",
            "compliance_mapping", "compliance_assessment", "gap_analysis",
            "control_testing", "policy_management", "policy_versioning",
            "audit_preparation", "audit_management", "evidence_management",
            "regulatory_change_monitoring", "compliance_dashboards",
            "compliance_reporting", "automated_control_testing",
            "external_regulatory_monitoring", "compliance_alerting",
            "compliance_release_verification",
        ]
