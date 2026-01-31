"""
Agent 16: Compliance & Regulatory Agent

Purpose:
Ensures projects, programs and portfolios adhere to internal policies, external regulations
and industry standards. Manages compliance requirements, monitors adherence, and facilitates
audits and evidence collection.

Specification: agents/delivery-management/agent-16-compliance-regulatory/README.md
"""

import asyncio
import json
import math
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from observability.tracing import get_trace_id

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from llm.client import LLMClient, LLMProviderError  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentManagementService,
    DocumentMetadata,
    GRCControl,
    GRCIntegrationService,
    NotificationService,
)
from agents.common.web_search import (  # noqa: E402
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent, InMemoryEventBus, ServiceBusEventBus  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.policy import (  # noqa: E402
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

    def __init__(self, agent_id: str = "agent_016", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.regulations = (
            config.get("regulations", ["GDPR", "SOX", "ISO 27001", "HIPAA", "PCI DSS"])
            if config
            else ["GDPR", "SOX", "ISO 27001", "HIPAA", "PCI DSS"]
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
                {
                    "critical": "monthly",
                    "high": "quarterly",
                    "medium": "semi-annually",
                    "low": "annually",
                },
            )
            if config
            else {
                "critical": "monthly",
                "high": "quarterly",
                "medium": "semi-annually",
                "low": "annually",
            }
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
                    self.event_bus = ServiceBusEventBus(
                        connection_string=service_bus_connection
                    )
                except RuntimeError as exc:
                    self.logger.warning(
                        "Service bus event bus unavailable, falling back to in-memory",
                        extra={"error": str(exc)},
                    )
                    self.event_bus = InMemoryEventBus()
            else:
                self.event_bus = InMemoryEventBus()

        self.notification_service = NotificationService(
            config.get("notifications") if config else None
        )

        # Data stores (will be replaced with database)
        self.regulation_library: dict[str, Any] = {}
        self.control_registry: dict[str, Any] = {}
        self.compliance_mappings: dict[str, Any] = {}
        self.policies: dict[str, Any] = {}
        self.audits: dict[str, Any] = {}
        self.evidence: dict[str, Any] = {}
        self.regulatory_changes: dict[str, Any] = {}
        self.control_embeddings: dict[str, dict[str, float]] = {}

    async def initialize(self) -> None:
        """Initialize database connections, GRC integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Compliance & Regulatory Agent...")

        # Initialize Document Management Service (SharePoint integration)
        doc_config = self.config.get("document_management", {}) if self.config else {}
        self.document_service = DocumentManagementService(doc_config)
        self.logger.info("Document Management Service initialized")

        # Initialize GRC Integration Service (ServiceNow GRC, RSA Archer)
        grc_config = self.config.get("grc_integration", {}) if self.config else {}
        self.grc_service = GRCIntegrationService(grc_config)
        self.logger.info("GRC Integration Service initialized")

        # Initialize Database Storage Service (Azure SQL, Cosmos DB, or JSON fallback)
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

        self.logger.info("Compliance & Regulatory Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "add_regulation",
            "define_control",
            "map_controls_to_project",
            "assess_compliance",
            "test_control",
            "manage_policy",
            "prepare_audit",
            "conduct_audit",
            "upload_evidence",
            "monitor_regulatory_changes",
            "get_compliance_dashboard",
            "generate_compliance_report",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "define_control":
            control_data = input_data.get("control", {})
            required_fields = ["description", "regulation", "owner"]
            for field in required_fields:
                if field not in control_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process compliance and regulatory requests.

        Args:
            input_data: {
                "action": "add_regulation" | "define_control" | "map_controls_to_project" |
                          "assess_compliance" | "test_control" | "manage_policy" |
                          "prepare_audit" | "conduct_audit" | "upload_evidence" |
                          "monitor_regulatory_changes" | "get_compliance_dashboard" |
                          "generate_compliance_report",
                "regulation": Regulation data,
                "control": Control definition,
                "mapping": Compliance mapping,
                "assessment": Assessment parameters,
                "test": Control test data,
                "policy": Policy document,
                "audit": Audit details,
                "evidence": Evidence files,
                "project_id": Project identifier,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - add_regulation: Regulation ID and applicability
            - define_control: Control ID and requirements
            - map_controls_to_project: Mapping ID and control checklist
            - assess_compliance: Assessment results and gap analysis
            - test_control: Test results and status
            - manage_policy: Policy ID and version
            - prepare_audit: Audit package and documentation
            - conduct_audit: Audit findings and scores
            - upload_evidence: Evidence ID and confirmation
            - monitor_regulatory_changes: Change notifications and impacts
            - get_compliance_dashboard: Dashboard data
            - generate_compliance_report: Report data
        """
        action = input_data.get("action", "get_compliance_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "add_regulation":
            return await self._add_regulation(input_data.get("regulation", {}))

        elif action == "define_control":
            return await self._define_control(input_data.get("control", {}))

        elif action == "map_controls_to_project":
            return await self._map_controls_to_project(
                input_data.get("project_id"),  # type: ignore
                input_data.get("mapping", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "assess_compliance":
            return await self._assess_compliance(
                input_data.get("project_id"), input_data.get("assessment", {})  # type: ignore
            )

        elif action == "test_control":
            return await self._test_control(
                input_data.get("control_id"), input_data.get("test", {})  # type: ignore
            )

        elif action == "manage_policy":
            return await self._manage_policy(input_data.get("policy", {}))

        elif action == "prepare_audit":
            return await self._prepare_audit(input_data.get("audit", {}))

        elif action == "conduct_audit":
            return await self._conduct_audit(input_data.get("audit_id"))  # type: ignore

        elif action == "upload_evidence":
            return await self._upload_evidence(
                input_data.get("control_id"),  # type: ignore
                input_data.get("evidence", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "monitor_regulatory_changes":
            return await self._monitor_regulatory_changes(
                domain=input_data.get("domain"),
                region=input_data.get("region"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_compliance_dashboard":
            return await self._get_compliance_dashboard(
                input_data.get("project_id"),
                input_data.get("portfolio_id"),
                domain=input_data.get("domain"),
                region=input_data.get("region"),
            )

        elif action == "generate_compliance_report":
            return await self._generate_compliance_report(
                input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _add_regulation(self, regulation_data: dict[str, Any]) -> dict[str, Any]:
        """
        Add regulation to library.

        Returns regulation ID and applicability.
        """
        self.logger.info(f"Adding regulation: {regulation_data.get('name')}")

        # Generate regulation ID
        regulation_id = await self._generate_regulation_id()

        # Parse regulation using Azure Cognitive Services
        regulation_metadata = await self._extract_regulation_metadata(regulation_data)
        parsed_obligations = regulation_metadata.get("obligations", [])

        # Determine applicability
        applicability = await self._determine_applicability(regulation_data)

        effective_date = regulation_data.get("effective_date") or regulation_metadata.get(
            "effective_date"
        )

        # Create regulation entry
        regulation = {
            "regulation_id": regulation_id,
            "name": regulation_data.get("name"),
            "description": regulation_data.get("description"),
            "jurisdiction": regulation_data.get("jurisdiction", []),
            "industry": regulation_data.get("industry", []),
            "effective_date": effective_date,
            "obligations": parsed_obligations,
            "related_controls": [],
            "applicability_rules": applicability,
            "metadata": regulation_metadata.get("metadata", {}),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store regulation
        self.regulation_library[regulation_id] = regulation

        # Persist to database
        await self.db_service.store("regulations", regulation_id, regulation)

        return {
            "regulation_id": regulation_id,
            "name": regulation["name"],
            "obligations_extracted": len(parsed_obligations),
            "applicability": applicability,
            "next_steps": "Define controls to satisfy regulatory obligations",
        }

    async def _define_control(self, control_data: dict[str, Any]) -> dict[str, Any]:
        """
        Define compliance control.

        Returns control ID and requirements.
        """
        self.logger.info(f"Defining control: {control_data.get('description')}")

        # Generate control ID
        control_id = await self._generate_control_id()

        # Recommend similar controls using AI
        similar_controls = await self._recommend_similar_controls(control_data)

        # Create control
        control = {
            "control_id": control_id,
            "description": control_data.get("description"),
            "regulation": control_data.get("regulation"),
            "control_type": control_data.get("control_type", "preventive"),
            "owner": control_data.get("owner"),
            "evidence_requirements": control_data.get("evidence_requirements", []),
            "test_frequency": control_data.get("test_frequency", "quarterly"),
            "test_procedure": control_data.get("test_procedure"),
            "status": "Active",
            "last_test_date": None,
            "last_test_result": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store control
        self.control_registry[control_id] = control

        # Link to regulation
        if control["regulation"] in self.regulation_library:
            self.regulation_library[control["regulation"]]["related_controls"].append(control_id)

        # Persist to database
        await self.db_service.store("controls", control_id, control)

        # Sync control to GRC platform
        grc_control = GRCControl(
            control_id=control_id,
            name=control_data.get("description", "")[:100],
            description=control_data.get("description", ""),
            regulation=control_data.get("regulation", ""),
            status=control["status"],
            owner=control["owner"],
            test_frequency=control["test_frequency"],
        )
        grc_sync_result = await self.grc_service.sync_control(grc_control)
        control["grc_external_id"] = grc_sync_result.get("external_id")

        return {
            "control_id": control_id,
            "description": control["description"],
            "owner": control["owner"],
            "test_frequency": control["test_frequency"],
            "similar_controls": similar_controls,
            "next_steps": "Map control to projects and deliverables",
        }

    async def _map_controls_to_project(
        self,
        project_id: str,
        mapping_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Map controls to project.

        Returns mapping ID and control checklist.
        """
        self.logger.info(f"Mapping controls to project: {project_id}")

        # Determine applicable regulations
        applicable_regulations = await self._determine_applicable_regulations(project_id)

        # Get all controls for applicable regulations
        applicable_controls = []
        for regulation_id in applicable_regulations:
            regulation = self.regulation_library.get(regulation_id)
            if regulation:
                applicable_controls.extend(regulation.get("related_controls", []))

        # Create compliance mapping
        mapping_id = await self._generate_mapping_id()

        mapping = {
            "mapping_id": mapping_id,
            "project_id": project_id,
            "applicable_regulations": applicable_regulations,
            "applicable_controls": applicable_controls,
            "control_status": {},
            "created_at": datetime.utcnow().isoformat(),
        }

        # Initialize control status
        for control_id in applicable_controls:
            mapping["control_status"][control_id] = {  # type: ignore
                "implementation_status": "Not Started",
                "evidence_uploaded": False,
                "last_tested": None,
                "test_result": None,
            }

        policy_decision = await self._evaluate_control_mapping_policy(
            project_id=project_id,
            mapping=mapping,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        mapping["policy_decision"] = policy_decision

        # Store mapping
        self.compliance_mappings[project_id] = mapping

        # Persist to database
        await self.db_service.store("compliance_mappings", mapping_id, mapping)

        return {
            "mapping_id": mapping_id,
            "project_id": project_id,
            "applicable_regulations": len(applicable_regulations),
            "applicable_controls": len(applicable_controls),
            "policy_decision": policy_decision,
            "compliance_checklist": [
                {
                    "control_id": c_id,
                    "description": self.control_registry.get(c_id, {}).get("description"),
                    "status": "Not Started",
                }
                for c_id in applicable_controls
            ],
        }

    async def _assess_compliance(
        self, project_id: str, assessment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Assess compliance readiness.

        Returns assessment results and gap analysis.
        """
        self.logger.info(f"Assessing compliance for project: {project_id}")

        mapping = self.compliance_mappings.get(project_id)
        if not mapping:
            # Create mapping first
            await self._map_controls_to_project(project_id, {})
            mapping = self.compliance_mappings.get(project_id)

        # Assess each control
        control_assessments = []
        gaps = []

        for control_id, status in mapping["control_status"].items():  # type: ignore
            control = self.control_registry.get(control_id)
            if not control:
                continue

            # Check implementation status
            implemented = status.get("implementation_status") == "Implemented"
            evidence_provided = status.get("evidence_uploaded", False)
            recently_tested = await self._is_recently_tested(control, status)

            assessment = {
                "control_id": control_id,
                "description": control.get("description"),
                "implemented": implemented,
                "evidence_provided": evidence_provided,
                "recently_tested": recently_tested,
                "compliant": implemented and evidence_provided and recently_tested,
            }

            control_assessments.append(assessment)

            if not assessment["compliant"]:
                gaps.append(
                    {
                        "control_id": control_id,
                        "description": control.get("description"),
                        "gap_type": await self._identify_gap_type(assessment),
                        "remediation": await self._recommend_remediation(assessment),
                    }
                )

        # Calculate compliance score
        total_controls = len(control_assessments)
        compliant_controls = sum(1 for a in control_assessments if a["compliant"])
        compliance_score = (compliant_controls / total_controls * 100) if total_controls > 0 else 0

        assessment = {
            "project_id": project_id,
            "compliance_score": compliance_score,
            "total_controls": total_controls,
            "compliant_controls": compliant_controls,
            "gaps_identified": len(gaps),
            "gaps": gaps,
            "control_assessments": control_assessments,
            "assessment_date": datetime.utcnow().isoformat(),
        }

        assessment_id = f"ASM-{project_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.db_service.store("compliance_assessments", assessment_id, assessment)

        return assessment

    async def _test_control(self, control_id: str, test_data: dict[str, Any]) -> dict[str, Any]:
        """
        Test control effectiveness.

        Returns test results and status.
        """
        self.logger.info(f"Testing control: {control_id}")

        control = self.control_registry.get(control_id)
        if not control:
            raise ValueError(f"Control not found: {control_id}")

        # Perform control test
        test_result = test_data.get("result", "pass")
        test_notes = test_data.get("notes", "")
        tester = test_data.get("tester", "unknown")

        # Update control
        control["last_test_date"] = datetime.utcnow().isoformat()
        control["last_test_result"] = test_result
        control["last_tester"] = tester

        # Update project mapping if exists
        for project_id, mapping in self.compliance_mappings.items():
            if control_id in mapping.get("control_status", {}):
                mapping["control_status"][control_id]["last_tested"] = control["last_test_date"]
                mapping["control_status"][control_id]["test_result"] = test_result

        # Persist control test result
        test_record_id = f"TST-{control_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        test_record = {
            "test_id": test_record_id,
            "control_id": control_id,
            "result": test_result,
            "notes": test_notes,
            "tester": tester,
            "tested_at": control["last_test_date"],
        }
        await self.db_service.store("control_tests", test_record_id, test_record)

        return {
            "control_id": control_id,
            "test_result": test_result,
            "test_date": control["last_test_date"],
            "tester": tester,
            "next_test_date": await self._calculate_next_test_date(control),
            "notes": test_notes,
        }

    async def _manage_policy(self, policy_data: dict[str, Any]) -> dict[str, Any]:
        """
        Manage policy document.

        Returns policy ID and version.
        """
        self.logger.info(f"Managing policy: {policy_data.get('title')}")

        # Generate policy ID
        policy_id = policy_data.get("policy_id") or await self._generate_policy_id()

        # Check if update to existing policy
        existing_policy = self.policies.get(policy_id)

        if existing_policy:
            # Create new version
            version = existing_policy.get("version", 1.0) + 0.1
        else:
            version = 1.0

        # Create/update policy
        policy = {
            "policy_id": policy_id,
            "title": policy_data.get("title"),
            "description": policy_data.get("description"),
            "version": version,
            "effective_date": policy_data.get("effective_date"),
            "owner": policy_data.get("owner"),
            "approval_status": "Draft",
            "document_url": policy_data.get("document_url"),
            "related_regulations": policy_data.get("related_regulations", []),
            "version_history": (
                existing_policy.get("version_history", []) if existing_policy else []
            ),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Add to version history
        if existing_policy:
            policy["version_history"].append(
                {
                    "version": existing_policy["version"],
                    "effective_date": existing_policy["effective_date"],
                    "archived_at": datetime.utcnow().isoformat(),
                }
            )

        # Store policy
        self.policies[policy_id] = policy

        # Persist to database
        await self.db_service.store("policies", policy_id, policy)

        # Publish policy document to SharePoint
        policy_content = f"""# {policy['title']}

**Version:** {policy['version']}
**Effective Date:** {policy.get('effective_date', 'TBD')}
**Owner:** {policy.get('owner', 'Unassigned')}

## Description
{policy.get('description', 'No description provided.')}

## Related Regulations
{', '.join(policy.get('related_regulations', [])) or 'None specified'}
"""
        doc_metadata = DocumentMetadata(
            title=f"Policy - {policy['title']} v{policy['version']}",
            description=policy.get("description", ""),
            classification="confidential",
            tags=["policy", policy_id] + policy.get("related_regulations", []),
            owner=policy.get("owner", "compliance"),
        )
        publish_result = await self.document_service.publish_document(
            document_content=policy_content,
            metadata=doc_metadata,
            folder_path="Policies",
        )
        policy["document_url"] = publish_result.get("url")

        return {
            "policy_id": policy_id,
            "title": policy["title"],
            "version": policy["version"],
            "status": policy["approval_status"],
            "next_steps": "Submit policy for approval and publication",
        }

    async def _prepare_audit(self, audit_data: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare audit package.

        Returns audit package and documentation.
        """
        self.logger.info(f"Preparing audit: {audit_data.get('title')}")

        # Generate audit ID
        audit_id = await self._generate_audit_id()

        project_id = audit_data.get("project_id")
        scope = audit_data.get("scope", [])

        # Compile required documentation
        documentation = await self._compile_audit_documentation(project_id, scope)  # type: ignore

        # Collect evidence
        evidence_package = await self._compile_evidence(project_id, scope)  # type: ignore

        # Generate control status summary
        control_summary = await self._generate_control_summary(project_id)  # type: ignore

        # Create audit record
        audit = {
            "audit_id": audit_id,
            "project_id": project_id,
            "title": audit_data.get("title"),
            "audit_type": audit_data.get("audit_type", "internal"),
            "scope": scope,
            "auditor": audit_data.get("auditor"),
            "scheduled_date": audit_data.get("scheduled_date"),
            "documentation": documentation,
            "evidence_package": evidence_package,
            "control_summary": control_summary,
            "status": "Prepared",
            "findings": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store audit
        self.audits[audit_id] = audit

        # Persist to database
        await self.db_service.store("audits", audit_id, audit)
        # Future work: Grant read-only access to auditors

        return {
            "audit_id": audit_id,
            "title": audit["title"],
            "scheduled_date": audit["scheduled_date"],
            "documentation_items": len(documentation),
            "evidence_items": len(evidence_package),
            "controls_in_scope": len(control_summary),
            "audit_package_url": f"/audits/{audit_id}/package",
        }

    async def _conduct_audit(self, audit_id: str) -> dict[str, Any]:
        """
        Conduct audit and record findings.

        Returns audit findings and scores.
        """
        self.logger.info(f"Conducting audit: {audit_id}")

        audit = self.audits.get(audit_id)
        if not audit:
            raise ValueError(f"Audit not found: {audit_id}")

        # Review controls and evidence
        findings = []
        controls_reviewed = 0
        controls_passed = 0

        for control_id in audit.get("control_summary", []):
            control = self.control_registry.get(control_id)
            if not control:
                continue

            controls_reviewed += 1

            # Check control effectiveness
            control_effective = await self._verify_control_effectiveness(control)

            if control_effective:
                controls_passed += 1
            else:
                findings.append(
                    {
                        "control_id": control_id,
                        "description": control.get("description"),
                        "finding_type": "deficiency",
                        "severity": "high",
                        "recommendation": "Strengthen control implementation and testing",
                    }
                )

        # Calculate audit score
        audit_score = (controls_passed / controls_reviewed * 100) if controls_reviewed > 0 else 0

        # Update audit
        audit["findings"] = findings
        audit["audit_score"] = audit_score
        audit["controls_reviewed"] = controls_reviewed
        audit["controls_passed"] = controls_passed
        audit["status"] = "Completed"
        audit["completion_date"] = datetime.utcnow().isoformat()

        # Persist audit results
        await self.db_service.store("audits", audit_id, audit)

        await self._publish_event(
            "compliance.audit.completed",
            {
                "audit_id": audit_id,
                "project_id": audit.get("project_id"),
                "audit_score": audit_score,
                "controls_reviewed": controls_reviewed,
                "controls_passed": controls_passed,
                "findings_count": len(findings),
                "completion_date": audit["completion_date"],
            },
        )
        await self._notify_stakeholders(
            subject=f"Audit completed: {audit.get('title', audit_id)}",
            message=(
                f"Audit {audit_id} completed with score {audit_score:.1f}. "
                f"Findings: {len(findings)}."
            ),
        )

        return {
            "audit_id": audit_id,
            "audit_score": audit_score,
            "controls_reviewed": controls_reviewed,
            "controls_passed": controls_passed,
            "findings_count": len(findings),
            "findings": findings,
            "completion_date": audit["completion_date"],
        }

    async def _upload_evidence(
        self,
        control_id: str,
        evidence_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Upload evidence for control.

        Returns evidence ID and confirmation.
        """
        self.logger.info(f"Uploading evidence for control: {control_id}")

        control = self.control_registry.get(control_id)
        if not control:
            raise ValueError(f"Control not found: {control_id}")

        # Generate evidence ID
        evidence_id = await self._generate_evidence_id()

        # Create evidence record
        evidence_record = {
            "evidence_id": evidence_id,
            "control_id": control_id,
            "file_name": evidence_data.get("file_name"),
            "file_type": evidence_data.get("file_type"),
            "file_url": evidence_data.get("file_url"),
            "description": evidence_data.get("description"),
            "uploaded_by": evidence_data.get("uploaded_by", "unknown"),
            "uploaded_at": datetime.utcnow().isoformat(),
            "classification": evidence_data.get("classification", "confidential"),
        }

        # Store evidence
        if control_id not in self.evidence:
            self.evidence[control_id] = []
        self.evidence[control_id].append(evidence_record)
        self.evidence_store.upsert(tenant_id, evidence_id, evidence_record)

        # Update project mapping
        for project_id, mapping in self.compliance_mappings.items():
            if control_id in mapping.get("control_status", {}):
                mapping["control_status"][control_id]["evidence_uploaded"] = True

        # Persist to database
        await self.db_service.store("evidence", evidence_id, evidence_record)

        # Upload evidence document to SharePoint with security classification
        evidence_content = evidence_data.get("content", f"Evidence for control {control_id}")
        doc_metadata = DocumentMetadata(
            title=evidence_record["file_name"] or f"Evidence-{evidence_id}",
            description=evidence_record.get("description", ""),
            classification=evidence_record.get("classification", "confidential"),
            tags=["evidence", control_id, evidence_id],
            owner=evidence_record.get("uploaded_by", "compliance"),
            retention_days=2555,  # 7 years retention for compliance evidence
        )
        publish_result = await self.document_service.publish_document(
            document_content=evidence_content,
            metadata=doc_metadata,
            folder_path=f"Compliance Evidence/{control_id}",
        )
        evidence_record["storage_url"] = publish_result.get("url")
        evidence_record["document_id"] = publish_result.get("document_id")

        return {
            "evidence_id": evidence_id,
            "control_id": control_id,
            "file_name": evidence_record["file_name"],
            "uploaded_at": evidence_record["uploaded_at"],
            "storage_url": evidence_record["file_url"],
        }

    async def monitor_regulations(
        self,
        domain: str,
        region: str | None,
        *,
        llm_client: LLMClient | None = None,
        result_limit: int | None = None,
    ) -> dict[str, Any]:
        """Monitor external sources for new or changing regulations."""
        if not self.enable_regulatory_monitoring:
            return {
                "summary": "",
                "updates": [],
                "gaps": [],
                "sources": [],
                "used_external_research": False,
            }

        context = f"{domain} {region or ''}".strip()
        query = build_search_query(
            context,
            "compliance",
            extra_keywords=self.regulatory_search_keywords,
        )

        # NOTE: Only high-level context should be sent to external search providers.
        snippets = await search_web(
            query, result_limit=result_limit or self.regulatory_search_result_limit
        )
        if not snippets:
            return {
                "summary": "",
                "updates": [],
                "gaps": [],
                "sources": [],
                "used_external_research": False,
            }

        summary = await summarize_snippets(snippets, llm_client=llm_client, purpose="compliance")
        updates = await self._extract_regulatory_updates(summary, snippets, llm_client=llm_client)
        gaps = self._identify_control_gaps(updates)
        sources = self._extract_sources(snippets)

        return {
            "summary": summary,
            "updates": updates,
            "gaps": gaps,
            "sources": sources,
            "used_external_research": True,
        }

    async def _monitor_regulatory_changes(
        self,
        *,
        domain: str | None,
        region: str | None,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Monitor regulatory changes and updates.

        Returns change notifications and impacts.
        """
        self.logger.info("Monitoring regulatory changes")

        # Check for regulatory updates
        # Future work: Subscribe to regulatory feeds and APIs
        changes = await self._check_regulatory_feeds()

        # Assess impact on existing regulations and controls
        impacted_regulations = []
        for change in changes:
            impact_assessment = await self._assess_regulatory_change_impact(change)
            if impact_assessment.get("projects_affected"):
                impacted_regulations.append(
                    {
                        "regulation": change.get("regulation"),
                        "change_description": change.get("description"),
                        "effective_date": change.get("effective_date"),
                        "impact_assessment": impact_assessment,
                    }
                )

        external_monitoring: dict[str, Any] | None = None
        if self.enable_regulatory_monitoring and domain:
            try:
                external_monitoring = await self.monitor_regulations(domain, region)
            except Exception as exc:
                self.logger.warning(
                    "External regulatory monitoring failed",
                    extra={"error": str(exc), "correlation_id": correlation_id},
                )
                external_monitoring = {
                    "summary": "",
                    "updates": [],
                    "gaps": [],
                    "sources": [],
                    "used_external_research": False,
                }

        external_updates = external_monitoring.get("updates", []) if external_monitoring else []
        all_updates = [
            *changes,
            *external_updates,
        ]

        new_obligations = [
            update
            for update in all_updates
            if update.get("description") or update.get("obligation")
        ]
        tasks_created = await self._create_stakeholder_tasks(new_obligations, tenant_id)

        if new_obligations:
            await self._publish_event(
                "compliance.regulation.change_detected",
                {
                    "changes": new_obligations,
                    "impacted_regulations": impacted_regulations,
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                },
            )
            await self._notify_stakeholders(
                subject="Regulatory updates detected",
                message=f"{len(new_obligations)} regulatory updates require review.",
            )

        return {
            "changes_detected": len(changes),
            "regulations_impacted": len(impacted_regulations),
            "impacted_regulations": impacted_regulations,
            "external_monitoring": external_monitoring,
            "tasks_created": tasks_created,
            "last_check": datetime.utcnow().isoformat(),
        }

    async def _extract_regulatory_updates(
        self,
        summary: str,
        snippets: list[str],
        *,
        llm_client: LLMClient | None = None,
    ) -> list[dict[str, Any]]:
        sources = self._extract_sources(snippets)
        system_prompt = (
            "You are a compliance analyst. Extract new or changing regulations from the "
            "summary and snippets. Return ONLY JSON as an array of objects with fields: "
            "regulation, description, effective_date, region, source_url."
        )
        user_prompt = json.dumps(
            {"summary": summary, "snippets": snippets, "sources": sources},
            indent=2,
        )

        llm = llm_client or LLMClient()
        try:
            response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            data = json.loads(response.content)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
            self.logger.warning("Regulatory extraction failed", extra={"error": str(exc)})
            return []

        updates: list[dict[str, Any]] = []
        if not isinstance(data, list):
            return updates
        for entry in data:
            if not isinstance(entry, dict):
                continue
            regulation = str(entry.get("regulation", "")).strip()
            description = str(entry.get("description", "")).strip()
            if not regulation or not description:
                continue
            updates.append(
                {
                    "regulation": regulation,
                    "description": description,
                    "effective_date": str(entry.get("effective_date", "")).strip(),
                    "region": str(entry.get("region", "")).strip(),
                    "source_url": str(entry.get("source_url", "")).strip(),
                }
            )
        return updates

    def _identify_control_gaps(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        gaps: list[dict[str, Any]] = []
        known_regulations = set(self.regulation_library.keys())
        for update in updates:
            regulation = update.get("regulation")
            if regulation and regulation not in known_regulations:
                gaps.append(
                    {
                        "regulation": regulation,
                        "recommended_action": "Review control library and add mappings.",
                    }
                )
        return gaps

    def _extract_sources(self, snippets: list[str]) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        for snippet in snippets:
            match = re.search(r"\((https?://[^)]+)\)", snippet)
            url = match.group(1) if match else ""
            if not url:
                continue
            sources.append({"url": url, "citation": snippet.strip()})
        return sources

    async def _get_compliance_dashboard(
        self,
        project_id: str | None,
        portfolio_id: str | None,
        *,
        domain: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """
        Get compliance dashboard.

        Returns dashboard data.
        """
        self.logger.info(
            f"Getting compliance dashboard for project={project_id}, portfolio={portfolio_id}"
        )

        external_monitoring = None
        if self.enable_regulatory_monitoring and domain:
            try:
                external_monitoring = await self.monitor_regulations(domain, region)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning(
                    "External compliance monitoring failed", extra={"error": str(exc)}
                )
                external_monitoring = {
                    "summary": "",
                    "updates": [],
                    "gaps": [],
                    "sources": [],
                    "used_external_research": False,
                }

        # Get compliance assessment
        assessment = None
        if project_id:
            assessment = await self._assess_compliance(project_id, {})

        # Get control testing status
        control_status = await self._get_control_testing_status(project_id)

        # Get upcoming audits
        upcoming_audits = await self._get_upcoming_audits(project_id)

        # Get recent findings
        recent_findings = await self._get_recent_audit_findings(project_id)

        return {
            "project_id": project_id,
            "portfolio_id": portfolio_id,
            "compliance_assessment": assessment,
            "control_testing_status": control_status,
            "upcoming_audits": upcoming_audits,
            "recent_findings": recent_findings,
            "external_monitoring": external_monitoring,
            "dashboard_generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_compliance_report(
        self, report_type: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate compliance report.

        Returns report data.
        """
        self.logger.info(f"Generating {report_type} compliance report")

        if report_type == "summary":
            return await self._generate_summary_report(filters)
        elif report_type == "detailed":
            return await self._generate_detailed_report(filters)
        elif report_type == "audit":
            return await self._generate_audit_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    # Helper methods

    async def _generate_regulation_id(self) -> str:
        """Generate unique regulation ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REG-{timestamp}"

    async def _generate_control_id(self) -> str:
        """Generate unique control ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CTL-{timestamp}"

    async def _generate_mapping_id(self) -> str:
        """Generate unique mapping ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"MAP-{timestamp}"

    async def _generate_policy_id(self) -> str:
        """Generate unique policy ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"POL-{timestamp}"

    async def _generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"AUD-{timestamp}"

    async def _generate_evidence_id(self) -> str:
        """Generate unique evidence ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"EV-{timestamp}"

    async def _parse_regulation_text(self, text: str) -> list[dict[str, Any]]:
        """Parse regulation text to extract obligations."""
        metadata = await self._extract_regulation_metadata({"text": text})
        return metadata.get("obligations", [])

    async def _determine_applicability(self, regulation_data: dict[str, Any]) -> dict[str, Any]:
        """Determine regulation applicability rules."""
        return {
            "applies_to_all": False,
            "jurisdiction_filter": regulation_data.get("jurisdiction", []),
            "industry_filter": regulation_data.get("industry", []),
        }

    async def _recommend_similar_controls(self, control_data: dict[str, Any]) -> list[str]:
        """Recommend similar controls."""
        query_text = " ".join(
            filter(
                None,
                [
                    control_data.get("description", ""),
                    control_data.get("regulation", ""),
                    control_data.get("control_type", ""),
                ],
            )
        ).strip()
        if not query_text:
            return []

        embeddings = await self._build_control_embeddings()
        query_vector = self._embed_text(query_text)
        scores: list[tuple[str, float]] = []
        for control_id, vector in embeddings.items():
            score = self._cosine_similarity(query_vector, vector)
            if score > 0:
                scores.append((control_id, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        return [control_id for control_id, _ in scores[:5]]

    async def _determine_applicable_regulations(self, project_id: str) -> list[str]:
        """Determine which regulations apply to project."""
        # Future work: Use project metadata to filter regulations
        return list(self.regulation_library.keys())[:3]  # Baseline

    async def _is_recently_tested(self, control: dict[str, Any], status: dict[str, Any]) -> bool:
        """Check if control has been tested recently."""
        last_test_date_str = status.get("last_tested")
        if not last_test_date_str:
            return False

        last_test_date = datetime.fromisoformat(last_test_date_str)
        test_frequency = control.get("test_frequency", "quarterly")

        # Determine frequency in days
        frequency_days = {"monthly": 30, "quarterly": 90, "semi-annually": 180, "annually": 365}

        days_threshold = frequency_days.get(test_frequency, 90)
        days_since_test = (datetime.utcnow() - last_test_date).days

        return days_since_test <= days_threshold

    async def _identify_gap_type(self, assessment: dict[str, Any]) -> str:
        """Identify type of compliance gap."""
        if not assessment["implemented"]:
            return "Not Implemented"
        elif not assessment["evidence_provided"]:
            return "Missing Evidence"
        elif not assessment["recently_tested"]:
            return "Overdue Testing"
        else:
            return "Unknown"

    async def _recommend_remediation(self, assessment: dict[str, Any]) -> str:
        """Recommend remediation action."""
        gap_type = await self._identify_gap_type(assessment)

        recommendations = {
            "Not Implemented": "Implement control and document procedures",
            "Missing Evidence": "Upload evidence of control implementation",
            "Overdue Testing": "Schedule and perform control testing",
            "Unknown": "Review control status",
        }

        return recommendations.get(gap_type, "Review and update")

    async def _calculate_next_test_date(self, control: dict[str, Any]) -> str:
        """Calculate next test date based on frequency."""
        last_test_date_str = control.get("last_test_date")
        if not last_test_date_str:
            return datetime.utcnow().isoformat()

        last_test_date = datetime.fromisoformat(last_test_date_str)
        test_frequency = control.get("test_frequency", "quarterly")

        # Determine frequency in days
        frequency_days = {"monthly": 30, "quarterly": 90, "semi-annually": 180, "annually": 365}

        days_to_add = frequency_days.get(test_frequency, 90)
        next_test_date = last_test_date + timedelta(days=days_to_add)

        return next_test_date.isoformat()

    async def _compile_audit_documentation(
        self, project_id: str, scope: list[str]
    ) -> list[dict[str, Any]]:
        """Compile documentation for audit from SharePoint and database."""
        documentation = []

        # Gather policies from document management system
        policies = await self.document_service.list_documents(
            folder_path="Policies",
            limit=50,
        )
        for policy in policies:
            documentation.append({
                "type": "policy",
                "title": policy.get("title", policy.get("Title", "")),
                "url": policy.get("url", policy.get("ServerRelativeUrl", "")),
                "document_id": policy.get("document_id", policy.get("Id", "")),
            })

        # Gather evidence documents for controls in scope
        for control_id in scope:
            evidence_docs = await self.document_service.list_documents(
                folder_path=f"Compliance Evidence/{control_id}",
                limit=20,
            )
            for doc in evidence_docs:
                documentation.append({
                    "type": "evidence",
                    "control_id": control_id,
                    "title": doc.get("title", doc.get("Title", "")),
                    "url": doc.get("url", doc.get("ServerRelativeUrl", "")),
                    "document_id": doc.get("document_id", doc.get("Id", "")),
                })

        return documentation

    async def _compile_evidence(self, project_id: str, scope: list[str]) -> list[dict[str, Any]]:
        """Compile evidence for audit."""
        evidence_package = []
        for control_id, evidence_list in self.evidence.items():
            evidence_package.extend(evidence_list)
        return evidence_package

    async def _generate_control_summary(self, project_id: str) -> list[str]:
        """Generate control summary for audit."""
        mapping = self.compliance_mappings.get(project_id)
        if not mapping:
            return []
        return mapping.get("applicable_controls", [])  # type: ignore

    async def _verify_control_effectiveness(self, control: dict[str, Any]) -> bool:
        """Verify control effectiveness."""
        # Check if recently tested and passed
        last_result = control.get("last_test_result")
        return last_result == "pass"

    async def _check_regulatory_feeds(self) -> list[dict[str, Any]]:
        """Check regulatory feeds for updates."""
        feeds = self.config.get("regulatory_feeds", []) if self.config else []
        if not feeds:
            return []

        updates: list[dict[str, Any]] = []
        for feed in feeds:
            feed_config = feed if isinstance(feed, dict) else {"url": str(feed)}
            url = feed_config.get("url")
            if not url:
                continue
            headers = feed_config.get("headers", {})
            api_key = feed_config.get("api_key") or os.getenv(feed_config.get("api_key_env", ""))
            if api_key:
                headers = {**headers, "Authorization": f"Bearer {api_key}"}
            params = feed_config.get("params", {})
            timeout = float(feed_config.get("timeout", 10))

            try:
                response = await asyncio.to_thread(
                    requests.get,
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                self.logger.warning("Regulatory feed fetch failed", extra={"error": str(exc)})
                continue

            feed_updates = payload
            if isinstance(payload, dict):
                feed_updates = payload.get("updates") or payload.get("items") or []

            if isinstance(feed_updates, list):
                for entry in feed_updates:
                    normalized = self._normalize_regulatory_update(entry, feed_config)
                    if normalized:
                        updates.append(normalized)

        return updates

    async def _assess_regulatory_change_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Assess impact of regulatory change."""
        # Future work: Analyze impact on projects and controls
        return {"projects_affected": [], "controls_affected": [], "estimated_effort": "medium"}

    async def _get_control_testing_status(self, project_id: str | None) -> dict[str, Any]:
        """Get control testing status."""
        # Future work: Query control test records
        return {"overdue_tests": 0, "upcoming_tests": 0, "recently_tested": 0}

    async def _get_upcoming_audits(self, project_id: str | None) -> list[dict[str, Any]]:
        """Get upcoming audits."""
        upcoming = []
        for audit_id, audit in self.audits.items():
            if project_id and audit.get("project_id") != project_id:
                continue
            if audit.get("status") in ["Scheduled", "Prepared"]:
                upcoming.append(
                    {
                        "audit_id": audit_id,
                        "title": audit.get("title"),
                        "scheduled_date": audit.get("scheduled_date"),
                    }
                )
        return upcoming

    async def _get_recent_audit_findings(self, project_id: str | None) -> list[dict[str, Any]]:
        """Get recent audit findings."""
        findings = []
        for audit_id, audit in self.audits.items():
            if project_id and audit.get("project_id") != project_id:
                continue
            if audit.get("status") == "Completed":
                findings.extend(audit.get("findings", []))
        return findings[:10]  # Most recent 10

    async def _generate_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate summary compliance report."""
        return {"report_type": "summary", "data": {}, "generated_at": datetime.utcnow().isoformat()}

    async def _generate_detailed_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate detailed compliance report."""
        return {
            "report_type": "detailed",
            "data": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_audit_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate audit report."""
        return {"report_type": "audit", "data": {}, "generated_at": datetime.utcnow().isoformat()}

    async def _extract_regulation_metadata(
        self, regulation_data: dict[str, Any]
    ) -> dict[str, Any]:
        text = regulation_data.get("text") or ""
        document_url = regulation_data.get("document_url")
        document_content = regulation_data.get("document_content")

        extracted_text = text
        metadata: dict[str, Any] = {}
        if document_url or document_content:
            document_result = await self._analyze_document_intelligence(
                document_url=document_url,
                document_content=document_content,
            )
            extracted_text = document_result.get("content") or extracted_text
            metadata["document_intelligence"] = document_result

        text_analytics_result = await self._analyze_text_analytics(extracted_text)
        metadata["text_analytics"] = text_analytics_result

        obligations = self._extract_obligations_from_text(
            extracted_text,
            text_analytics_result.get("key_phrases", []),
        )
        effective_date = self._extract_effective_date(
            text_analytics_result.get("entities", [])
        )

        return {
            "obligations": obligations,
            "effective_date": effective_date,
            "metadata": metadata,
        }

    async def _analyze_text_analytics(self, text: str) -> dict[str, Any]:
        endpoint = self.config.get("text_analytics_endpoint") if self.config else None
        api_key = self.config.get("text_analytics_key") if self.config else None
        endpoint = endpoint or os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
        api_key = api_key or os.getenv("AZURE_TEXT_ANALYTICS_KEY")
        if not endpoint or not api_key or not text:
            return {"key_phrases": [], "entities": []}

        text_payload = {
            "documents": [
                {
                    "id": "1",
                    "language": "en",
                    "text": text[:5000],
                }
            ]
        }

        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
        }

        async def _post(path: str) -> dict[str, Any]:
            response = await asyncio.to_thread(
                requests.post,
                f"{endpoint.rstrip('/')}/{path}",
                headers=headers,
                json=text_payload,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        try:
            key_phrases_response = await _post("text/analytics/v3.1/keyPhrases")
            entities_response = await _post("text/analytics/v3.1/entities/recognition/general")
        except requests.RequestException as exc:
            self.logger.warning("Text analytics failed", extra={"error": str(exc)})
            return {"key_phrases": [], "entities": []}

        key_phrases = (
            key_phrases_response.get("documents", [{}])[0].get("keyPhrases", [])
            if isinstance(key_phrases_response, dict)
            else []
        )
        entities = (
            entities_response.get("documents", [{}])[0].get("entities", [])
            if isinstance(entities_response, dict)
            else []
        )

        return {"key_phrases": key_phrases, "entities": entities}

    async def _analyze_document_intelligence(
        self,
        *,
        document_url: str | None,
        document_content: str | bytes | None,
    ) -> dict[str, Any]:
        endpoint = self.config.get("document_intelligence_endpoint") if self.config else None
        api_key = self.config.get("document_intelligence_key") if self.config else None
        endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not endpoint or not api_key or (not document_url and not document_content):
            return {"content": ""}

        headers = {"Ocp-Apim-Subscription-Key": api_key}
        analyze_url = f"{endpoint.rstrip('/')}/formrecognizer/documentModels/prebuilt-layout:analyze"
        params = {"api-version": "2023-07-31"}

        if document_url:
            request_body = {"urlSource": document_url}
            headers["Content-Type"] = "application/json"
            response = await asyncio.to_thread(
                requests.post,
                analyze_url,
                params=params,
                headers=headers,
                json=request_body,
                timeout=15,
            )
        else:
            if isinstance(document_content, str):
                document_bytes = document_content.encode("utf-8")
            else:
                document_bytes = document_content
            headers["Content-Type"] = "application/octet-stream"
            response = await asyncio.to_thread(
                requests.post,
                analyze_url,
                params=params,
                headers=headers,
                data=document_bytes,
                timeout=15,
            )

        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            self.logger.warning("Document intelligence call failed", extra={"error": str(exc)})
            return {"content": ""}

        operation_location = response.headers.get("operation-location")
        if not operation_location:
            return {"content": ""}

        try:
            result_response = await asyncio.to_thread(
                requests.get,
                operation_location,
                headers={"Ocp-Apim-Subscription-Key": api_key},
                timeout=15,
            )
            result_response.raise_for_status()
            result_payload = result_response.json()
        except (requests.RequestException, ValueError) as exc:
            self.logger.warning("Document intelligence result failed", extra={"error": str(exc)})
            return {"content": ""}

        content = result_payload.get("analyzeResult", {}).get("content", "")
        return {"content": content, "raw": result_payload}

    def _extract_obligations_from_text(
        self, text: str, key_phrases: list[str]
    ) -> list[dict[str, Any]]:
        obligations: list[dict[str, Any]] = []
        if not text:
            return obligations
        sentences = re.split(r"(?<=[.!?])\s+", text)
        obligation_patterns = re.compile(
            r"\b(shall|must|required|requires|obligated|ensure|prohibit|mandate)\b",
            re.IGNORECASE,
        )
        for sentence in sentences:
            if obligation_patterns.search(sentence):
                obligation = sentence.strip()
                if obligation:
                    obligations.append({"obligation": obligation, "deadline": None})

        for phrase in key_phrases[:10]:
            obligations.append({"obligation": phrase, "deadline": None, "source": "key_phrase"})

        return obligations

    def _extract_effective_date(self, entities: list[dict[str, Any]]) -> str | None:
        for entity in entities:
            if entity.get("category") in {"DateTime", "Date"}:
                return entity.get("text")
        return None

    async def _build_control_embeddings(self) -> dict[str, dict[str, float]]:
        if not self.control_registry:
            return {}
        corpus_tokens = {
            control_id: self._tokenize_text(
                " ".join(
                    filter(
                        None,
                        [
                            control.get("description", ""),
                            control.get("regulation", ""),
                            control.get("control_type", ""),
                        ],
                    )
                )
            )
            for control_id, control in self.control_registry.items()
        }

        document_frequencies: Counter[str] = Counter()
        for tokens in corpus_tokens.values():
            document_frequencies.update(set(tokens))

        total_docs = len(corpus_tokens)
        embeddings: dict[str, dict[str, float]] = {}
        for control_id, tokens in corpus_tokens.items():
            token_counts = Counter(tokens)
            vector: dict[str, float] = {}
            for token, count in token_counts.items():
                idf = math.log((total_docs + 1) / (1 + document_frequencies[token])) + 1
                vector[token] = count * idf
            embeddings[control_id] = vector

        self.control_embeddings = embeddings
        return embeddings

    def _embed_text(self, text: str) -> dict[str, float]:
        tokens = self._tokenize_text(text)
        token_counts = Counter(tokens)
        return {token: float(count) for token, count in token_counts.items()}

    def _tokenize_text(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _cosine_similarity(self, vector_a: dict[str, float], vector_b: dict[str, float]) -> float:
        if not vector_a or not vector_b:
            return 0.0
        intersection = set(vector_a) & set(vector_b)
        dot_product = sum(vector_a[token] * vector_b[token] for token in intersection)
        magnitude_a = math.sqrt(sum(value * value for value in vector_a.values()))
        magnitude_b = math.sqrt(sum(value * value for value in vector_b.values()))
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)

    def _normalize_regulatory_update(
        self, entry: Any, feed_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None
        regulation = entry.get("regulation") or entry.get("title") or entry.get("name")
        description = entry.get("description") or entry.get("summary") or entry.get("details")
        if not regulation and not description:
            return None
        return {
            "regulation": regulation,
            "description": description,
            "effective_date": entry.get("effective_date") or entry.get("effectiveDate"),
            "region": entry.get("region"),
            "source_url": entry.get("source_url") or entry.get("url") or feed_config.get("url"),
            "feed": feed_config.get("name") or feed_config.get("url"),
            "raw": entry,
        }

    async def _create_stakeholder_tasks(
        self, updates: list[dict[str, Any]], tenant_id: str
    ) -> list[dict[str, Any]]:
        stakeholders = self.config.get("stakeholders", []) if self.config else []
        recipients = [
            stakeholder.get("email")
            for stakeholder in stakeholders
            if isinstance(stakeholder, dict) and stakeholder.get("email")
        ]
        if not recipients:
            recipients = [self.config.get("default_stakeholder_email", "compliance@example.com")]

        tasks = []
        for update in updates:
            task_id = f"TASK-{uuid.uuid4().hex[:8]}"
            task = {
                "task_id": task_id,
                "tenant_id": tenant_id,
                "title": f"Review regulatory update: {update.get('regulation', 'Update')}",
                "description": update.get("description"),
                "regulation": update.get("regulation"),
                "effective_date": update.get("effective_date"),
                "assigned_to": recipients,
                "status": "open",
                "created_at": datetime.utcnow().isoformat(),
                "source_url": update.get("source_url"),
            }
            tasks.append(task)
            await self.db_service.store("compliance_tasks", task_id, task)
            await self._publish_event("compliance.task.created", task)

        return tasks

    async def _notify_stakeholders(self, *, subject: str, message: str) -> list[dict[str, Any]]:
        stakeholders = self.config.get("stakeholders", []) if self.config else []
        recipients = [
            stakeholder.get("email")
            for stakeholder in stakeholders
            if isinstance(stakeholder, dict) and stakeholder.get("email")
        ]
        if not recipients:
            recipients = [self.config.get("default_stakeholder_email", "compliance@example.com")]

        results = []
        for recipient in recipients:
            result = await self.notification_service.send_email(
                to=recipient,
                subject=subject,
                body=message,
                metadata={"category": "compliance"},
            )
            results.append(result)
        return results

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        await self.event_bus.publish(topic, payload)

    async def _evaluate_control_mapping_policy(
        self,
        *,
        project_id: str,
        mapping: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
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
        audit_event = build_audit_event(
            tenant_id=tenant_id,
            action="compliance.control_mapping.policy.checked",
            outcome=outcome,
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=project_id,
            resource_type="compliance_mapping",
            metadata={"decision": decision.decision, "reasons": decision.reasons},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(audit_event)
        return {"decision": decision.decision, "reasons": decision.reasons}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Compliance & Regulatory Agent...")
        # Integration services use connection pooling and don't require explicit cleanup
        self.logger.info("Compliance & Regulatory Agent cleanup complete")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "regulation_management",
            "regulation_parsing",
            "control_definition",
            "control_library_management",
            "compliance_mapping",
            "compliance_assessment",
            "gap_analysis",
            "control_testing",
            "policy_management",
            "policy_versioning",
            "audit_preparation",
            "audit_management",
            "evidence_management",
            "regulatory_change_monitoring",
            "compliance_dashboards",
            "compliance_reporting",
            "automated_control_testing",
            "external_regulatory_monitoring",
        ]
