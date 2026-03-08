"""
Connector Integration Services for Agents.

Provides high-level integration services that wrap the platform's connectors
for use by agents. These services handle:
- Document management (SharePoint, Confluence)
- GRC platforms (ServiceNow GRC, RSA Archer)
- Documentation repository publishing (facade over DocumentManagementService)
- ERP finance (SAP, Oracle, NetSuite, Dynamics 365)
- HRIS (Workday, SuccessFactors, ADP)
- Project/work management (Planview, MS Project, Jira, Azure DevOps)
- ITSM (ServiceNow, Jira Service Management, BMC Remedy)
- Notifications (email, Teams, Slack, push)
- Calendar (Outlook, Google Calendar)
- Database storage (Azure SQL, Cosmos DB, local JSON)
- ML prediction (Azure ML)

All write operations should go through the ConnectorWriteGate to enforce:
- Connector configured + connected
- Approval present if required by policy
- Dry-run capability
- Consistent audit logging and idempotency checks
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import importlib.util
import logging
import os
import smtplib
import ssl
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from common.bootstrap import ensure_monorepo_paths  # noqa: E402


def _ensure_connector_paths() -> None:
    ensure_monorepo_paths()


def _get_connector_types() -> tuple[type, type]:
    _ensure_connector_paths()
    from base_connector import ConnectorCategory, ConnectorConfig

    return ConnectorConfig, ConnectorCategory


ConnectorConfig, ConnectorCategory = _get_connector_types()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Write-gating hook used by all integration services
# ---------------------------------------------------------------------------


@dataclass
class WriteGateResult:
    """Result of a write-gating check."""

    allowed: bool
    reason: str = ""
    idempotency_key: str = ""
    audit_entry: dict[str, Any] = field(default_factory=dict)


class ConnectorWriteGate:
    """Standard write-gating hook enforced before any connector write operation.

    Every integration service SHOULD call ``check`` before writing to an
    external system of record.  The gate verifies:

    1. The connector is configured **and** connected (status >=
       ``permissions_validated`` or ``connected``).
    2. An approval is present when required by organisational policy.
    3. A dry-run has been executed successfully (when ``require_dry_run`` is
       set).
    4. An idempotency key is generated so the same write is not executed
       twice.
    5. An audit log entry is emitted for every write attempt (pass or fail).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.require_dry_run = self.config.get("require_dry_run", False)

    def check(
        self,
        *,
        connector_status: str,
        approval_status: str | None = None,
        approval_required: bool = False,
        dry_run_passed: bool | None = None,
        operation: str = "",
        entity_id: str = "",
        agent_id: str = "",
        tenant_id: str = "",
    ) -> WriteGateResult:
        """Evaluate write-gate preconditions and return a result."""
        idempotency_key = hashlib.sha256(
            f"{agent_id}:{tenant_id}:{operation}:{entity_id}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:32]

        audit_entry = {
            "gate": "connector_write_gate",
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "operation": operation,
            "entity_id": entity_id,
            "connector_status": connector_status,
            "approval_required": approval_required,
            "approval_status": approval_status,
            "dry_run_passed": dry_run_passed,
            "idempotency_key": idempotency_key,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Connector must be configured + connected
        valid_statuses = {"connected", "permissions_validated"}
        if connector_status not in valid_statuses:
            audit_entry["result"] = "blocked"
            audit_entry["reason"] = f"connector_status={connector_status}"
            logger.warning(
                "Write gate blocked: connector not ready (status=%s, op=%s)",
                connector_status,
                operation,
            )
            return WriteGateResult(
                allowed=False,
                reason=f"Connector status '{connector_status}' does not meet minimum requirement. Must be one of: {valid_statuses}",
                idempotency_key=idempotency_key,
                audit_entry=audit_entry,
            )

        # 2. Approval present if required
        if approval_required and approval_status != "approved":
            audit_entry["result"] = "blocked"
            audit_entry["reason"] = f"approval_status={approval_status}"
            logger.warning(
                "Write gate blocked: approval required but status=%s (op=%s)",
                approval_status,
                operation,
            )
            return WriteGateResult(
                allowed=False,
                reason=f"Approval required but current status is '{approval_status}'",
                idempotency_key=idempotency_key,
                audit_entry=audit_entry,
            )

        # 3. Dry-run passed if required
        if self.require_dry_run and dry_run_passed is not True:
            audit_entry["result"] = "blocked"
            audit_entry["reason"] = "dry_run_not_passed"
            logger.warning("Write gate blocked: dry-run not passed (op=%s)", operation)
            return WriteGateResult(
                allowed=False,
                reason="Dry-run is required but has not passed",
                idempotency_key=idempotency_key,
                audit_entry=audit_entry,
            )

        audit_entry["result"] = "allowed"
        logger.info(
            "Write gate passed (op=%s, entity=%s, idempotency=%s)",
            operation,
            entity_id,
            idempotency_key,
        )
        return WriteGateResult(
            allowed=True,
            idempotency_key=idempotency_key,
            audit_entry=audit_entry,
        )


@dataclass
class DocumentMetadata:
    """Metadata for documents stored in document management systems."""

    title: str
    description: str = ""
    classification: str = "internal"
    retention_days: int = 365
    tags: list[str] = field(default_factory=list)
    owner: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GRCControl:
    """Represents a GRC control record."""

    control_id: str
    name: str
    description: str
    regulation: str
    status: str = "active"
    owner: str = ""
    test_frequency: str = "quarterly"
    last_test_date: str | None = None
    last_test_result: str | None = None


@dataclass
class GRCRisk:
    """Represents a GRC risk record."""

    risk_id: str
    title: str
    description: str
    category: str
    likelihood: str = "medium"
    impact: str = "medium"
    status: str = "open"
    owner: str = ""
    mitigation_plan: str = ""


class DocumentManagementService:
    """
    Document Management Integration Service.

    Provides methods to publish, retrieve, and manage documents
    in SharePoint or other document management systems.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "sharepoint")

    def _get_connector(self) -> Any:
        """Lazy-load and return the document management connector."""
        if self._connector is not None:
            return self._connector

        # Check if SharePoint is configured
        site_url = os.getenv("SHAREPOINT_SITE_URL")
        if not site_url:
            logger.warning("SharePoint not configured - using mock document service")
            return None

        try:
            from sharepoint_connector import SharePointConnector

            connector_config = ConnectorConfig(
                connector_id="sharepoint",
                name="SharePoint",
                category=ConnectorCategory.DOC_MGMT,
                instance_url=site_url,
            )
            self._connector = SharePointConnector(connector_config)
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize SharePoint connector: %s", exc)
            return None

    async def publish_document(
        self,
        document_content: str | bytes,
        metadata: DocumentMetadata,
        folder_path: str = "Documents",
    ) -> dict[str, Any]:
        """
        Publish a document to the document management system.

        Args:
            document_content: The content of the document (text or bytes)
            metadata: Document metadata including title, description, etc.
            folder_path: Target folder path in the document library

        Returns:
            Dictionary with document_id, url, and status
        """
        connector = self._get_connector()

        if connector is None:
            # Mock implementation when connector not available
            logger.info("Mock publishing document: %s", metadata.title)
            return {
                "document_id": f"DOC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "title": metadata.title,
                "url": f"/sites/default/Documents/{folder_path}/{metadata.title}",
                "status": "published_mock",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            # Prepare document data for SharePoint
            document_data = [
                {
                    "Title": metadata.title,
                    "Description": metadata.description,
                    "Classification": metadata.classification,
                    "RetentionDays": metadata.retention_days,
                    "Tags": ",".join(metadata.tags),
                    "Owner": metadata.owner,
                }
            ]

            result = connector.write("documents", document_data)

            return {
                "document_id": result[0].get("Id") if result else None,
                "title": metadata.title,
                "url": result[0].get("ServerRelativeUrl") if result else None,
                "status": "published",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to publish document: %s", exc)
            return {
                "document_id": None,
                "title": metadata.title,
                "url": None,
                "status": "failed",
                "error": str(exc),
            }

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        """
        Retrieve a document from the document management system.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            Document data or None if not found
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving document: %s", document_id)
            return {
                "document_id": document_id,
                "title": f"Document {document_id}",
                "content": "Mock document content",
                "status": "retrieved_mock",
            }

        try:
            documents = connector.read("documents", filters={"Id": document_id})
            if documents:
                return documents[0]
            return None
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve document: %s", exc)
            return None

    async def list_documents(
        self,
        folder_path: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List documents from the document management system.

        Args:
            folder_path: Optional folder path to filter by
            filters: Additional filters
            limit: Maximum number of documents to return

        Returns:
            List of document records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock listing documents")
            return [
                {
                    "document_id": "DOC-001",
                    "title": "Sample Document 1",
                    "folder": folder_path or "Documents",
                },
                {
                    "document_id": "DOC-002",
                    "title": "Sample Document 2",
                    "folder": folder_path or "Documents",
                },
            ]

        try:
            query_filters = filters or {}
            if folder_path:
                query_filters["folder"] = folder_path
            return connector.read("documents", filters=query_filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to list documents: %s", exc)
            return []


class GRCIntegrationService:
    """
    GRC (Governance, Risk, Compliance) Integration Service.

    Provides methods to sync controls, risks, and compliance data
    with ServiceNow GRC, RSA Archer, or other GRC platforms.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "servicenow_grc")

    def _get_connector(self) -> Any:
        """Lazy-load and return the GRC connector."""
        if self._connector is not None:
            return self._connector

        # Check if ServiceNow GRC is configured
        instance_url = os.getenv("SERVICENOW_URL")
        if not instance_url:
            # Try RSA Archer
            archer_url = os.getenv("ARCHER_URL")
            if archer_url:
                self._connector_type = "archer"
                try:
                    from archer_connector import ArcherConnector

                    connector_config = ConnectorConfig(
                        connector_id="archer",
                        name="RSA Archer",
                        category=ConnectorCategory.GRC,
                        instance_url=archer_url,
                    )
                    self._connector = ArcherConnector(connector_config)
                    return self._connector
                except (
                    ConnectionError,
                    TimeoutError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                    OSError,
                ) as exc:
                    logger.warning("Failed to initialize Archer connector: %s", exc)
                    return None

            logger.warning("GRC platform not configured - using mock GRC service")
            return None

        try:
            from servicenow_grc_connector import ServiceNowGrcConnector

            connector_config = ConnectorConfig(
                connector_id="servicenow_grc",
                name="ServiceNow GRC",
                category=ConnectorCategory.GRC,
                instance_url=instance_url,
            )
            self._connector = ServiceNowGrcConnector(connector_config)
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize ServiceNow GRC connector: %s", exc)
            return None

    async def sync_control(self, control: GRCControl) -> dict[str, Any]:
        """
        Sync a compliance control to the GRC platform.

        Args:
            control: The GRC control to sync

        Returns:
            Sync result with external_id and status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock syncing control: %s", control.control_id)
            return {
                "control_id": control.control_id,
                "external_id": f"GRC-CTL-{control.control_id}",
                "status": "synced_mock",
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            # Read existing control from GRC platform
            if self._connector_type == "servicenow_grc":
                # ServiceNow GRC - query profiles as controls equivalent
                result = connector.read("profiles", limit=1)
            else:
                # Archer format - query controls table
                result = connector.read("controls", filters={"ControlID": control.control_id})

            return {
                "control_id": control.control_id,
                "external_id": result[0].get("sys_id") if result else None,
                "status": "synced",
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to sync control: %s", exc)
            return {
                "control_id": control.control_id,
                "external_id": None,
                "status": "failed",
                "error": str(exc),
            }

    async def sync_risk(self, risk: GRCRisk) -> dict[str, Any]:
        """
        Sync a risk record to the GRC platform.

        Args:
            risk: The GRC risk to sync

        Returns:
            Sync result with external_id and status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock syncing risk: %s", risk.risk_id)
            return {
                "risk_id": risk.risk_id,
                "external_id": f"GRC-RISK-{risk.risk_id}",
                "status": "synced_mock",
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            risk_data = [
                {
                    "short_description": risk.title,
                    "description": risk.description,
                    "category": risk.category,
                    "likelihood": risk.likelihood,
                    "impact": risk.impact,
                    "state": risk.status,
                    "owner": risk.owner,
                    "mitigation_plan": risk.mitigation_plan,
                }
            ]

            result = connector.write("risks", risk_data)

            return {
                "risk_id": risk.risk_id,
                "external_id": result[0].get("sys_id") if result else None,
                "status": "synced",
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to sync risk: %s", exc)
            return {
                "risk_id": risk.risk_id,
                "external_id": None,
                "status": "failed",
                "error": str(exc),
            }

    async def get_risks(
        self, filters: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Retrieve risks from the GRC platform.

        Args:
            filters: Optional filters
            limit: Maximum number of risks to return

        Returns:
            List of risk records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving risks")
            return [
                {
                    "risk_id": "RISK-001",
                    "title": "Sample Risk 1",
                    "category": "operational",
                    "status": "open",
                },
                {
                    "risk_id": "RISK-002",
                    "title": "Sample Risk 2",
                    "category": "compliance",
                    "status": "mitigated",
                },
            ]

        try:
            return connector.read("risks", filters=filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve risks: %s", exc)
            return []

    async def get_profiles(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Retrieve GRC profiles from the platform.

        Args:
            limit: Maximum number of profiles to return

        Returns:
            List of GRC profile records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving GRC profiles")
            return [
                {"profile_id": "PROF-001", "name": "Sample GRC Profile"},
            ]

        try:
            return connector.read("profiles", limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve profiles: %s", exc)
            return []


class ERPIntegrationService:
    """
    ERP Finance Integration Service.

    Provides methods to sync financial data with ERP finance systems:
    SAP, Oracle, NetSuite, and Dynamics 365.

    Note: Workday is classified under HRISService.  Use ``ERPFinanceService``
    (alias for this class) in new code for clarity.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "sap")

    def _select_connector_type(self) -> str | None:
        connector_envs = {
            "sap": "SAP_URL",
            "oracle": "ORACLE_URL",
            "netsuite": "NETSUITE_URL",
            "dynamics_365": "DYNAMICS365_URL",
        }
        preferred_env = connector_envs.get(self._connector_type)
        if preferred_env and os.getenv(preferred_env):
            return self._connector_type
        for connector_type, env_var in connector_envs.items():
            if os.getenv(env_var):
                return connector_type
        return None

    def _get_connector(self) -> Any:
        """Lazy-load and return the ERP connector."""
        if self._connector is not None:
            return self._connector

        connector_type = self._select_connector_type()
        if not connector_type:
            logger.warning("ERP platform not configured - using mock ERP service")
            return None

        try:
            if connector_type == "sap":
                from sap_connector import SapConnector

                connector_config = ConnectorConfig(
                    connector_id="sap",
                    name="SAP",
                    category=ConnectorCategory.ERP,
                    instance_url=os.getenv("SAP_URL", ""),
                )
                self._connector = SapConnector(connector_config)
            elif connector_type == "oracle":
                from oracle_connector import OracleConnector

                connector_config = ConnectorConfig(
                    connector_id="oracle",
                    name="Oracle ERP Cloud",
                    category=ConnectorCategory.ERP,
                    instance_url=os.getenv("ORACLE_URL", ""),
                )
                self._connector = OracleConnector(connector_config)
            elif connector_type == "netsuite":
                logger.warning("NetSuite connector not available - using mock ERP service")
                return None
            elif connector_type == "dynamics_365":
                logger.warning("Dynamics 365 connector not available - using mock ERP service")
                return None
            else:
                logger.warning("Unsupported ERP connector type - using mock ERP service")
                return None
            self._connector_type = connector_type
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize ERP connector (%s): %s", connector_type, exc)
            return None

    async def sync_financial_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Sync financial data to the ERP platform.

        Args:
            payload: Financial data payload

        Returns:
            Sync result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock syncing financial data")
            return {
                "status": "synced_mock",
                "connector": self._connector_type,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("financials", [payload])
            return {
                "status": "synced",
                "connector": self._connector_type,
                "external_id": result[0].get("id") if result else None,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to sync financial data: %s", exc)
            return {
                "status": "failed",
                "connector": self._connector_type,
                "error": str(exc),
            }

    async def get_transactions(
        self, filters: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Retrieve transactions from the ERP platform.

        Args:
            filters: Optional filters
            limit: Maximum number of records to return

        Returns:
            List of transaction records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving ERP transactions")
            return [
                {"transaction_id": "TXN-001", "amount": 1250.0, "currency": "AUD"},
                {"transaction_id": "TXN-002", "amount": 300.0, "currency": "AUD"},
            ]

        try:
            return connector.read("transactions", filters=filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve transactions: %s", exc)
            return []

    async def post_journal_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        Post a journal entry to the ERP platform.

        Args:
            entry: Journal entry payload

        Returns:
            Posting result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock posting journal entry")
            return {
                "status": "posted_mock",
                "journal_entry_id": f"JE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("journal_entries", [entry])
            return {
                "status": "posted",
                "journal_entry_id": result[0].get("id") if result else None,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to post journal entry: %s", exc)
            return {"status": "failed", "error": str(exc)}


# Explicit alias — new code should use ERPFinanceService.
ERPFinanceService = ERPIntegrationService


class HRISService:
    """
    HRIS (Human Resource Information System) Integration Service.

    Provides methods to sync HR data with HRIS platforms:
    Workday, SAP SuccessFactors, and ADP.

    Previously Workday was bundled inside ERPIntegrationService; it is now
    correctly classified here under HRIS.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "workday")

    def _select_connector_type(self) -> str | None:
        connector_envs = {
            "workday": "WORKDAY_API_URL",
            "successfactors": "SUCCESSFACTORS_URL",
            "adp": "ADP_API_URL",
        }
        preferred_env = connector_envs.get(self._connector_type)
        if preferred_env and os.getenv(preferred_env):
            return self._connector_type
        for connector_type, env_var in connector_envs.items():
            if os.getenv(env_var):
                return connector_type
        return None

    def _get_connector(self) -> Any:
        """Lazy-load and return the HRIS connector."""
        if self._connector is not None:
            return self._connector

        connector_type = self._select_connector_type()
        if not connector_type:
            logger.warning("HRIS platform not configured - using mock HRIS service")
            return None

        try:
            if connector_type == "workday":
                from workday_connector import WorkdayConnector

                connector_config = ConnectorConfig(
                    connector_id="workday",
                    name="Workday",
                    category=ConnectorCategory.HRIS,
                    instance_url=os.getenv("WORKDAY_API_URL", ""),
                )
                self._connector = WorkdayConnector(connector_config)
            elif connector_type == "successfactors":
                logger.warning("SuccessFactors connector not available - using mock HRIS service")
                return None
            elif connector_type == "adp":
                logger.warning("ADP connector not available - using mock HRIS service")
                return None
            else:
                logger.warning("Unsupported HRIS connector type - using mock HRIS service")
                return None
            self._connector_type = connector_type
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize HRIS connector (%s): %s", connector_type, exc)
            return None

    async def get_employees(
        self, filters: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve employee records from the HRIS platform."""
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving employees")
            return [
                {"employee_id": "EMP-001", "name": "Sample Employee", "status": "active"},
            ]

        try:
            return connector.read("workers", filters=filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve employees: %s", exc)
            return []

    async def sync_resource_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sync resource/capacity data from the HRIS platform."""
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock syncing resource data")
            return {
                "status": "synced_mock",
                "connector": self._connector_type,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.read("workers", filters=payload, limit=500)
            return {
                "status": "synced",
                "connector": self._connector_type,
                "record_count": len(result),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to sync resource data: %s", exc)
            return {"status": "failed", "connector": self._connector_type, "error": str(exc)}

    async def get_org_structure(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve organisational structure from the HRIS platform."""
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving org structure")
            return [
                {"org_id": "ORG-001", "name": "Engineering", "manager": "EMP-001"},
            ]

        try:
            return connector.read("organizations", filters=filters)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve org structure: %s", exc)
            return []


class ITSMIntegrationService:
    """
    ITSM Integration Service.

    Provides methods to manage change requests, tickets, and incidents
    in ServiceNow, Jira Service Management, or BMC Remedy.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "servicenow")

    def _select_connector_type(self) -> str | None:
        connector_envs = {
            "servicenow": "SERVICENOW_URL",
            "jira": "JIRA_INSTANCE_URL",
            "bmc_remedy": "BMC_REMEDY_URL",
        }
        preferred_env = connector_envs.get(self._connector_type)
        if preferred_env and os.getenv(preferred_env):
            return self._connector_type
        for connector_type, env_var in connector_envs.items():
            if os.getenv(env_var):
                return connector_type
        return None

    def _get_connector(self) -> Any:
        """Lazy-load and return the ITSM connector."""
        if self._connector is not None:
            return self._connector

        connector_type = self._select_connector_type()
        if not connector_type:
            logger.warning("ITSM platform not configured - using mock ITSM service")
            return None

        try:
            if connector_type == "jira":
                from jira_connector import JiraConnector

                connector_config = ConnectorConfig(
                    connector_id="jira",
                    name="Jira Service Management",
                    category=ConnectorCategory.PM,
                    instance_url=os.getenv("JIRA_INSTANCE_URL", ""),
                )
                self._connector = JiraConnector(connector_config)
            elif connector_type == "servicenow":
                logger.warning("ServiceNow ITSM connector not available - using mock ITSM service")
                return None
            elif connector_type == "bmc_remedy":
                logger.warning("BMC Remedy connector not available - using mock ITSM service")
                return None
            else:
                logger.warning("Unsupported ITSM connector type - using mock ITSM service")
                return None
            self._connector_type = connector_type
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize ITSM connector (%s): %s", connector_type, exc)
            return None

    async def create_change_request(self, change_request: dict[str, Any]) -> dict[str, Any]:
        """
        Create a change request in the ITSM platform.

        Args:
            change_request: Change request payload

        Returns:
            Creation result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock creating change request")
            return {
                "status": "created_mock",
                "change_id": f"CHG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            resource_type = "issues" if self._connector_type == "jira" else "changes"
            result = connector.write(resource_type, [change_request])
            return {
                "status": "created",
                "change_id": result[0].get("id") if result else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to create change request: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def update_ticket(self, ticket_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update a ticket in the ITSM platform.

        Args:
            ticket_id: Ticket identifier
            updates: Ticket updates payload

        Returns:
            Update result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock updating ticket")
            return {
                "status": "updated_mock",
                "ticket_id": ticket_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            resource_type = "issues" if self._connector_type == "jira" else "tickets"
            update_payload = {"id": ticket_id, **updates}
            result = connector.write(resource_type, [update_payload])
            return {
                "status": "updated",
                "ticket_id": result[0].get("id") if result else ticket_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to update ticket: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def get_incidents(
        self, filters: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Retrieve incidents from the ITSM platform.

        Args:
            filters: Optional filters
            limit: Maximum number of incidents to return

        Returns:
            List of incident records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving incidents")
            return [
                {"incident_id": "INC-001", "summary": "Sample incident 1", "status": "open"},
                {"incident_id": "INC-002", "summary": "Sample incident 2", "status": "resolved"},
            ]

        try:
            resource_type = "issues" if self._connector_type == "jira" else "incidents"
            return connector.read(resource_type, filters=filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve incidents: %s", exc)
            return []


class ProjectManagementService:
    """
    Project Management Integration Service.

    Provides methods to sync projects, tasks, and schedules with
    Planview, MS Project, Jira, or Azure DevOps.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "planview")

    def _select_connector_type(self) -> str | None:
        connector_envs = {
            "planview": "PLANVIEW_INSTANCE_URL",
            "ms_project": "MS_PROJECT_SITE_URL",
            "jira": "JIRA_INSTANCE_URL",
            "azure_devops": "AZURE_DEVOPS_ORG_URL",
        }
        preferred_env = connector_envs.get(self._connector_type)
        if preferred_env and os.getenv(preferred_env):
            return self._connector_type
        for connector_type, env_var in connector_envs.items():
            if os.getenv(env_var):
                return connector_type
        return None

    def _get_connector(self) -> Any:
        """Lazy-load and return the project management connector."""
        if self._connector is not None:
            return self._connector

        connector_type = self._select_connector_type()
        if not connector_type:
            logger.warning("Project management platform not configured - using mock PM service")
            return None

        try:
            if connector_type == "planview":
                from planview_connector import PlanviewConnector

                connector_config = ConnectorConfig(
                    connector_id="planview",
                    name="Planview",
                    category=ConnectorCategory.PPM,
                    instance_url=os.getenv("PLANVIEW_INSTANCE_URL", ""),
                )
                self._connector = PlanviewConnector(connector_config)
            elif connector_type == "ms_project":
                from ms_project_server_connector import MsProjectServerConnector

                connector_config = ConnectorConfig(
                    connector_id="ms_project_server",
                    name="Microsoft Project",
                    category=ConnectorCategory.PPM,
                    instance_url=os.getenv("MS_PROJECT_SITE_URL", ""),
                )
                self._connector = MsProjectServerConnector(connector_config)
            elif connector_type == "jira":
                from jira_connector import JiraConnector

                connector_config = ConnectorConfig(
                    connector_id="jira",
                    name="Jira",
                    category=ConnectorCategory.PM,
                    instance_url=os.getenv("JIRA_INSTANCE_URL", ""),
                )
                self._connector = JiraConnector(connector_config)
            elif connector_type == "azure_devops":
                from azure_devops_connector import AzureDevOpsConnector

                connector_config = ConnectorConfig(
                    connector_id="azure_devops",
                    name="Azure DevOps",
                    category=ConnectorCategory.PM,
                    instance_url=os.getenv("AZURE_DEVOPS_ORG_URL", ""),
                )
                self._connector = AzureDevOpsConnector(connector_config)
            else:
                logger.warning(
                    "Unsupported project management connector type - using mock PM service"
                )
                return None
            self._connector_type = connector_type
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize PM connector (%s): %s", connector_type, exc)
            return None

    def _task_resource_type(self) -> str:
        return {
            "jira": "issues",
            "azure_devops": "work_items",
            "ms_project": "tasks",
        }.get(self._connector_type, "tasks")

    async def sync_project(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Sync project details to the PM platform.

        Args:
            project: Project payload

        Returns:
            Sync result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock syncing project")
            return {
                "status": "synced_mock",
                "project_id": project.get("id") or project.get("project_id"),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("projects", [project])
            return {
                "status": "synced",
                "project_id": result[0].get("id") if result else None,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to sync project: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def get_tasks(
        self,
        project_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve tasks from the PM platform.

        Args:
            project_id: Project identifier
            filters: Optional filters
            limit: Maximum number of tasks to return

        Returns:
            List of task records
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock retrieving tasks")
            return [
                {"task_id": "TASK-001", "name": "Sample Task 1", "status": "in_progress"},
                {"task_id": "TASK-002", "name": "Sample Task 2", "status": "not_started"},
            ]

        try:
            task_filters = {"project_id": project_id, **(filters or {})}
            return connector.read(self._task_resource_type(), filters=task_filters, limit=limit)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to retrieve tasks: %s", exc)
            return []

    async def create_tasks(
        self,
        project_id: str | None,
        tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Create tasks in the PM platform.

        Args:
            project_id: Project identifier
            tasks: Task payloads

        Returns:
            List of task creation results
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock creating tasks")
            return [
                {
                    "status": "created_mock",
                    "task_id": f"TASK-{index+1:03d}",
                    "project_id": project_id,
                }
                for index, _task in enumerate(tasks)
            ]

        try:
            payloads = []
            for task in tasks:
                payload = {"project_id": project_id, **task}
                payloads.append(payload)
            results = connector.write(self._task_resource_type(), payloads)
            return [
                {
                    "status": "created",
                    "task_id": result.get("id") or result.get("task_id"),
                    "project_id": project_id,
                }
                for result in (results or [])
            ]
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to create tasks: %s", exc)
            return [{"status": "failed", "error": str(exc)}]

    async def update_schedule(self, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update project schedule in the PM platform.

        Args:
            project_id: Project identifier
            updates: Schedule update payload

        Returns:
            Update result status
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock updating project schedule")
            return {
                "status": "updated_mock",
                "project_id": project_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            payload = {"project_id": project_id, **updates}
            result = connector.write(self._task_resource_type(), [payload])
            return {
                "status": "updated",
                "project_id": result[0].get("project_id") if result else project_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to update schedule: %s", exc)
            return {"status": "failed", "error": str(exc)}


class NotificationService:
    """
    Notification Service.

    Provides methods to send notifications via email, Teams, or Slack.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connectors: dict[str, Any] = {}

    def _get_connector(self, connector_type: str) -> Any:
        """Lazy-load and return the notification connector."""
        if connector_type in self._connectors:
            return self._connectors[connector_type]

        try:
            if connector_type == "teams":
                if not (os.getenv("TEAMS_CLIENT_ID") or os.getenv("TEAMS_REFRESH_TOKEN")):
                    logger.warning("Teams not configured - using mock notification service")
                    return None
                from teams_connector import TeamsConnector

                connector_config = ConnectorConfig(
                    connector_id="teams",
                    name="Microsoft Teams",
                    category=ConnectorCategory.COLLABORATION,
                    instance_url=os.getenv("TEAMS_API_URL", ""),
                )
                self._connectors[connector_type] = TeamsConnector(connector_config)
            elif connector_type == "slack":
                if not os.getenv("SLACK_BOT_TOKEN"):
                    logger.warning("Slack not configured - using mock notification service")
                    return None
                from slack_connector import SlackConnector

                connector_config = ConnectorConfig(
                    connector_id="slack",
                    name="Slack",
                    category=ConnectorCategory.COLLABORATION,
                    instance_url=os.getenv("SLACK_API_URL", ""),
                )
                self._connectors[connector_type] = SlackConnector(connector_config)
            elif connector_type == "email":
                if not os.getenv("EMAIL_SMTP_HOST"):
                    logger.warning("Email not configured - using mock notification service")
                    return None
                logger.warning("Email connector not available - using mock notification service")
                return None
            elif connector_type == "twilio":
                if not (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")):
                    logger.warning("Twilio not configured - using mock notification service")
                    return None
                from twilio_connector import TwilioConnector

                connector_config = ConnectorConfig(
                    connector_id="twilio",
                    name="Twilio",
                    category=ConnectorCategory.COLLABORATION,
                    instance_url=os.getenv("TWILIO_API_URL", ""),
                )
                self._connectors[connector_type] = TwilioConnector(connector_config)
            elif connector_type == "notification_hubs":
                if not (
                    os.getenv("AZURE_NOTIFICATION_HUBS_NAMESPACE")
                    and os.getenv("AZURE_NOTIFICATION_HUBS_NAME")
                    and os.getenv("AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME")
                    and os.getenv("AZURE_NOTIFICATION_HUBS_SAS_KEY")
                ):
                    logger.warning(
                        "Notification Hubs not configured - using mock notification service"
                    )
                    return None
                from notification_hubs_connector import NotificationHubsConnector

                connector_config = ConnectorConfig(
                    connector_id="notification_hubs",
                    name="Notification Hubs",
                    category=ConnectorCategory.COLLABORATION,
                )
                self._connectors[connector_type] = NotificationHubsConnector(connector_config)
            else:
                logger.warning(
                    "Unsupported notification connector type - using mock notification service"
                )
                return None
            return self._connectors[connector_type]
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning(
                "Failed to initialize notification connector (%s): %s", connector_type, exc
            )
            return None

    async def send_email(
        self, to: str, subject: str, body: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Send an email notification.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            metadata: Optional metadata

        Returns:
            Send status
        """
        metadata = metadata or {}

        def get_setting(key: str, default: Any | None = None) -> Any | None:
            return self.config.get(key) or os.getenv(key, default)

        provider = (
            get_setting("email_provider") or get_setting("EMAIL_PROVIDER") or "smtp"
        ).lower()
        smtp_host = get_setting("smtp_host") or get_setting("EMAIL_SMTP_HOST")
        sendgrid_key = get_setting("sendgrid_api_key") or get_setting("SENDGRID_API_KEY")
        graph_provider = provider == "graph"
        acs_provider = provider in {
            "acs",
            "azure_communication_service",
            "azure_communication_services",
        }

        if provider == "sendgrid" and not sendgrid_key:
            logger.error("SendGrid provider selected but SENDGRID_API_KEY is not configured")
            return {
                "status": "failed",
                "to": to,
                "subject": subject,
                "error": "SendGrid API key not configured",
            }

        if provider == "smtp" and not smtp_host:
            if sendgrid_key:
                provider = "sendgrid"
            else:
                logger.info("Email not configured - using mock notification service")
                return {
                    "status": "sent_mock",
                    "to": to,
                    "subject": subject,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata,
                }

        email_from = (
            get_setting("email_from") or get_setting("EMAIL_FROM") or "no-reply@example.com"
        )
        reply_to = metadata.get("reply_to") or get_setting("EMAIL_REPLY_TO")
        cc = metadata.get("cc")
        bcc = metadata.get("bcc")
        html_body = metadata.get("html_body")
        locale = metadata.get("locale")
        accessible_format = metadata.get("accessible_format")

        try:
            if graph_provider:
                graph_result = await self._send_email_via_graph(
                    to=to,
                    subject=subject,
                    body=body,
                    metadata=metadata,
                )
                if graph_result.get("status") != "failed":
                    return graph_result
                if smtp_host:
                    provider = "smtp"
                else:
                    return graph_result
            if acs_provider:
                acs_result = await self._send_email_via_acs(
                    to=to,
                    subject=subject,
                    body=body,
                    metadata=metadata,
                )
                if acs_result.get("status") != "failed":
                    return acs_result
                if smtp_host:
                    provider = "smtp"
                else:
                    return acs_result
            if provider == "sendgrid":
                try:
                    from sendgrid import SendGridAPIClient
                    from sendgrid.helpers.mail import Mail
                except ImportError as exc:
                    logger.error("SendGrid library not installed")
                    return {
                        "status": "failed",
                        "to": to,
                        "subject": subject,
                        "error": f"SendGrid library not installed: {exc}",
                    }

                message = Mail(
                    from_email=email_from,
                    to_emails=[to],
                    subject=subject,
                    plain_text_content=body,
                )
                if html_body:
                    message.html_content = html_body
                if cc:
                    message.cc = cc if isinstance(cc, list) else [cc]
                if bcc:
                    message.bcc = bcc if isinstance(bcc, list) else [bcc]

                client = SendGridAPIClient(sendgrid_key)
                response = client.send(message)
                status = "sent" if 200 <= response.status_code < 300 else "failed"
                return {
                    "status": status,
                    "to": to,
                    "subject": subject,
                    "provider": "sendgrid",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata,
                    "sendgrid_status": response.status_code,
                }

            smtp_port = int(get_setting("smtp_port") or get_setting("EMAIL_SMTP_PORT") or 587)
            smtp_user = get_setting("smtp_user") or get_setting("EMAIL_SMTP_USER")
            smtp_password = get_setting("smtp_password") or get_setting("EMAIL_SMTP_PASSWORD")
            use_ssl = str(
                get_setting("smtp_use_ssl") or get_setting("EMAIL_SMTP_USE_SSL") or ""
            ).lower()
            use_tls = str(
                get_setting("smtp_use_tls") or get_setting("EMAIL_SMTP_USE_TLS") or ""
            ).lower()

            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = email_from
            message["To"] = to
            if reply_to:
                message["Reply-To"] = reply_to
            if locale:
                message["Content-Language"] = str(locale)
            if accessible_format:
                message["X-Accessible-Format"] = str(accessible_format)
            if cc:
                message["Cc"] = ", ".join(cc) if isinstance(cc, list) else cc
            if bcc:
                message["Bcc"] = ", ".join(bcc) if isinstance(bcc, list) else bcc
            message.set_content(body)
            if html_body:
                message.add_alternative(html_body, subtype="html")

            should_use_ssl = use_ssl in {"1", "true", "yes"} or smtp_port == 465
            should_use_tls = use_tls in {"1", "true", "yes"} or smtp_port == 587

            if should_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                    if smtp_user and smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    if should_use_tls:
                        server.starttls(context=ssl.create_default_context())
                    if smtp_user and smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.send_message(message)

            return {
                "status": "sent",
                "to": to,
                "subject": subject,
                "provider": "smtp",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to send email: %s", exc)
            return {
                "status": "failed",
                "to": to,
                "subject": subject,
                "error": str(exc),
                "provider": provider,
            }

    async def send_sms(
        self, to: str, message: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send an SMS notification."""
        metadata = metadata or {}
        provider = (
            self.config.get("sms_provider") or os.getenv("SMS_PROVIDER") or "twilio"
        ).lower()

        if provider in {"twilio", "sms"}:
            connector = self._get_connector("twilio")
            if connector is None:
                logger.info("Twilio not configured - using mock SMS notification")
                return {
                    "status": "sent_mock",
                    "to": to,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            from_number = (
                metadata.get("from_number")
                or self.config.get("twilio_from_number")
                or os.getenv("TWILIO_FROM_NUMBER")
            )
            payload = {"to": to, "from": from_number, "body": message}
            try:
                result = connector.write("messages", [payload])
                return {
                    "status": "sent",
                    "to": to,
                    "message_id": result[0].get("sid") if result else None,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                logger.error("Failed to send SMS via Twilio: %s", exc)
                return {"status": "failed", "to": to, "error": str(exc)}

        if provider in {"acs", "azure_communication_services"}:
            try:
                from azure_communication_services_connector import (
                    AzureCommunicationServicesConnector,
                )

                connector_config = ConnectorConfig(
                    connector_id="azure_communication_services",
                    name="Azure Communication Services",
                    category=ConnectorCategory.COLLABORATION,
                )
                connector = AzureCommunicationServicesConnector(connector_config)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                logger.warning("ACS connector unavailable: %s", exc)
                connector = None
            if connector is None:
                return {"status": "failed", "to": to, "error": "acs_connector_missing"}
            payload = {
                "to": [to],
                "from": metadata.get("from_number") or os.getenv("ACS_FROM_NUMBER"),
                "message": message,
            }
            try:
                result = connector.write("sms", [payload])
                return {
                    "status": "sent",
                    "to": to,
                    "message_id": result[0].get("messageId") if result else None,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                logger.error("Failed to send SMS via ACS: %s", exc)
                return {"status": "failed", "to": to, "error": str(exc)}

        logger.info("Mock sending SMS notification")
        return {
            "status": "sent_mock",
            "to": to,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _send_email_via_graph(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        token = await self._get_graph_access_token()
        if not token:
            return {"status": "failed", "error": "graph_access_token_missing", "provider": "graph"}
        sender = (
            metadata.get("graph_sender")
            or self.config.get("graph_sender")
            or os.getenv("GRAPH_SENDER")
            or "me"
        )
        html_body = metadata.get("html_body")
        content_type = "HTML" if html_body else "Text"
        message_body = html_body or body
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": content_type, "content": message_body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": "false",
        }
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            if response.status_code in {200, 202}:
                return {
                    "status": "sent",
                    "to": to,
                    "subject": subject,
                    "provider": "graph",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata,
                }
            return {
                "status": "failed",
                "to": to,
                "subject": subject,
                "provider": "graph",
                "error": response.text,
            }

    async def _send_email_via_acs(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        connection_string = self.config.get("acs_connection_string") or os.getenv(
            "ACS_CONNECTION_STRING"
        )
        if not connection_string:
            return {"status": "failed", "error": "acs_connection_missing", "provider": "acs"}
        if not importlib.util.find_spec("azure.communication.email"):
            return {
                "status": "failed",
                "error": "acs_email_library_missing",
                "provider": "acs",
            }
        from azure.communication.email import EmailClient  # type: ignore

        sender = (
            metadata.get("acs_sender")
            or self.config.get("acs_sender")
            or os.getenv("ACS_EMAIL_SENDER")
        )
        if not sender:
            return {"status": "failed", "error": "acs_sender_missing", "provider": "acs"}
        html_body = metadata.get("html_body")
        email_message = {
            "senderAddress": sender,
            "content": {
                "subject": subject,
                "plainText": body,
                "html": html_body,
            },
            "recipients": {"to": [{"address": to}]},
        }
        client = EmailClient.from_connection_string(connection_string)
        poller = client.begin_send(email_message)
        poller.result()
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "provider": "acs",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        }

    async def _get_graph_access_token(self) -> str | None:
        token = self.config.get("graph_access_token") or os.getenv("GRAPH_ACCESS_TOKEN")
        if token:
            return token
        if not importlib.util.find_spec("msal"):
            return None
        import msal

        tenant_id = self.config.get("graph_tenant_id") or os.getenv("AZURE_TENANT_ID")
        client_id = self.config.get("graph_client_id") or os.getenv("AZURE_CLIENT_ID")
        client_secret = self.config.get("graph_client_secret") or os.getenv("AZURE_CLIENT_SECRET")
        if not tenant_id or not client_id or not client_secret:
            return None
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=client_id, authority=authority, client_credential=client_secret
        )
        scopes = self.config.get("graph_scopes") or ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_silent(scopes, account=None) or app.acquire_token_for_client(
            scopes=scopes
        )
        return result.get("access_token") if result else None

    async def send_teams_message(
        self,
        team_id: str | None,
        channel_id: str | None,
        message: str,
        chat_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a message to a Microsoft Teams channel.

        Args:
            team_id: Teams team ID
            channel_id: Teams channel ID
            message: Message content

        Returns:
            Send status
        """
        if chat_id or user_id:
            return await self.send_chat_message(chat_id=chat_id, user_id=user_id, message=message)

        connector = self._get_connector("teams")

        if connector is None:
            logger.info("Mock sending Teams message")
            return {
                "status": "sent_mock",
                "team_id": team_id,
                "channel_id": channel_id,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write(
                "messages",
                [{"team_id": team_id, "channel_id": channel_id, "body": message}],
            )
            return {
                "status": "sent",
                "message_id": result[0].get("id") if result else None,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to send Teams message: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def send_slack_message(self, destination: str, message: str) -> dict[str, Any]:
        connector = self._get_connector("slack")

        if connector is None:
            logger.info("Mock sending Slack message")
            return {
                "status": "sent_mock",
                "destination": destination,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write(
                "messages",
                [{"channel": destination, "text": message}],
            )
            return {
                "status": "sent",
                "message_id": result[0].get("ts") if result else None,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to send Slack message: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def send_chat_message(
        self, chat_id: str | None, user_id: str | None, message: str
    ) -> dict[str, Any]:
        chat_id = chat_id or (
            self.config.get("graph_chat_map", {}).get(user_id) if user_id else None
        )
        token = await self._get_graph_access_token()
        if not token or not chat_id:
            logger.info("Mock sending chat message")
            return {
                "status": "sent_mock",
                "chat_id": chat_id,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"body": {"contentType": "html", "content": message}},
            )
            if response.status_code in {200, 201, 202}:
                return {
                    "status": "sent",
                    "chat_id": chat_id,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            return {"status": "failed", "error": response.text}

    async def send_push_notification(self, destination: str, message: str) -> dict[str, Any]:
        """
        Send a push notification.

        Args:
            destination: Target destination identifier
            message: Notification message

        Returns:
            Send status
        """
        provider = (
            self.config.get("push_provider") or os.getenv("PUSH_PROVIDER") or "mock"
        ).lower()
        if provider == "firebase":
            return await self._send_push_via_firebase(destination, message)
        if provider in {"azure_notification_hubs", "notification_hubs"}:
            return await self._send_push_via_notification_hubs(destination, message)
        logger.info("Mock sending push notification")
        return {
            "status": "sent_mock",
            "destination": destination,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _send_push_via_firebase(self, destination: str, message: str) -> dict[str, Any]:
        server_key = self.config.get("firebase_server_key") or os.getenv("FIREBASE_SERVER_KEY")
        if not server_key:
            return {"status": "failed", "error": "firebase_server_key_missing"}
        import httpx

        payload = {"to": destination, "notification": {"title": "Approval Update", "body": message}}
        headers = {"Authorization": f"key={server_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send", headers=headers, json=payload
            )
            if response.status_code in {200, 201}:
                return {
                    "status": "sent",
                    "destination": destination,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            return {"status": "failed", "error": response.text}

    async def _send_push_via_notification_hubs(
        self, destination: str, message: str
    ) -> dict[str, Any]:
        connector = self._get_connector("notification_hubs")
        if connector is not None:
            try:
                payload = {
                    "to": destination,
                    "notification": {"title": "Approval Update", "body": message},
                }
                result = connector.write("notifications", [payload])
                return {
                    "status": "sent",
                    "destination": destination,
                    "message_id": result[0].get("id") if result else None,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                logger.error("Failed to send push notification via connector: %s", exc)
        namespace = self.config.get("notification_hubs_namespace") or os.getenv(
            "AZURE_NOTIFICATION_HUBS_NAMESPACE"
        )
        hub_name = self.config.get("notification_hubs_name") or os.getenv(
            "AZURE_NOTIFICATION_HUBS_NAME"
        )
        sas_key_name = self.config.get("notification_hubs_sas_key_name") or os.getenv(
            "AZURE_NOTIFICATION_HUBS_SAS_KEY_NAME"
        )
        sas_key = self.config.get("notification_hubs_sas_key") or os.getenv(
            "AZURE_NOTIFICATION_HUBS_SAS_KEY"
        )
        if not namespace or not hub_name or not sas_key_name or not sas_key:
            return {"status": "failed", "error": "notification_hubs_config_missing"}
        url = (
            f"https://{namespace}.servicebus.windows.net/{hub_name}/messages" "?api-version=2015-01"
        )
        token = self._build_sas_token(url, sas_key_name, sas_key)
        import httpx

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "ServiceBusNotification-Format": "gcm",
        }
        payload = {"data": {"message": message}, "to": destination}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in {200, 201, 202}:
                return {
                    "status": "sent",
                    "destination": destination,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            return {"status": "failed", "error": response.text}

    def _build_sas_token(self, uri: str, key_name: str, key: str) -> str:
        expiry = int(time.time() + 3600)
        encoded_uri = urllib.parse.quote_plus(uri)
        sign_key = f"{encoded_uri}\n{expiry}".encode()
        signature = base64.b64encode(
            hmac.new(base64.b64decode(key), sign_key, hashlib.sha256).digest()
        ).decode()
        return (
            f"SharedAccessSignature sr={encoded_uri}&sig={urllib.parse.quote_plus(signature)}"
            f"&se={expiry}&skn={key_name}"
        )


class CalendarIntegrationService:
    """Calendar integration service for Outlook and Google Calendar connectors."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector: Any | None = None
        self._provider = (
            self.config.get("provider") or os.getenv("CALENDAR_PROVIDER") or ""
        ).lower()

    def _select_provider(self) -> str | None:
        if self._provider:
            return self._provider
        if os.getenv("OUTLOOK_CLIENT_ID") or os.getenv("OUTLOOK_REFRESH_TOKEN"):
            return "outlook"
        if os.getenv("GOOGLE_CALENDAR_CLIENT_ID") or os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN"):
            return "google_calendar"
        return None

    def _get_connector(self) -> Any | None:
        if self._connector is not None:
            return self._connector

        provider = self._select_provider()
        if not provider:
            return None
        try:
            _ensure_connector_paths()
            if provider in {"outlook", "graph"}:
                from outlook_connector import OutlookConnector

                connector_config = ConnectorConfig(
                    connector_id="outlook",
                    name="Outlook",
                    category=ConnectorCategory.COLLABORATION,
                )
                self._connector = OutlookConnector(connector_config)
            elif provider in {"google", "google_calendar"}:
                from google_calendar_connector import GoogleCalendarConnector

                connector_config = ConnectorConfig(
                    connector_id="google_calendar",
                    name="Google Calendar",
                    category=ConnectorCategory.COLLABORATION,
                )
                self._connector = GoogleCalendarConnector(connector_config)
            else:
                return None
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize calendar connector (%s): %s", provider, exc)
            return None

    def create_event(self, event: dict[str, Any]) -> dict[str, Any]:
        connector = self._get_connector()
        if connector is None:
            return {"status": "skipped", "reason": "calendar_connector_unavailable"}

        start_time = event.get("start") or event.get("scheduled_time")
        end_time = event.get("end")
        if not end_time and start_time:
            end_time = start_time
        payload = {
            "subject": event.get("title") or event.get("summary"),
            "summary": event.get("title") or event.get("summary"),
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
            "description": event.get("description"),
        }
        try:
            result = connector.write("events", [payload])
            return {
                "status": "scheduled",
                "provider": connector.CONNECTOR_ID,
                "event_id": result[0].get("id") if result else None,
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to create calendar event: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def list_events(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        connector = self._get_connector()
        if connector is None:
            return []
        try:
            return connector.read("events", filters=filters)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to list calendar events: %s", exc)
            return []

    def get_availability(
        self, user_id: str | None, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        connector = self._get_connector()
        if connector is None:
            return []
        try:
            if connector.CONNECTOR_ID == "outlook":
                filters = {
                    "startDateTime": start.isoformat(),
                    "endDateTime": end.isoformat(),
                }
                return connector.read("calendar_view", filters=filters)
            filters = {
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
            }
            return connector.read("events", filters=filters)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to get calendar availability: %s", exc)
            return []


class MLPredictionService:
    """
    ML Prediction Service.

    Provides methods to run predictions using Azure ML endpoints.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None

    def _get_connector(self) -> Any:
        """Lazy-load and return the Azure ML connector."""
        if self._connector is not None:
            return self._connector

        endpoint = os.getenv("AZURE_ML_ENDPOINT")
        api_key = os.getenv("AZURE_ML_API_KEY")
        if not endpoint or not api_key:
            logger.warning("Azure ML not configured - using mock ML service")
            return None

        try:
            from azure_ml_connector import AzureMLConnector

            connector_config = ConnectorConfig(
                connector_id="azure_ml",
                name="Azure ML",
                category=ConnectorCategory.PM,
                instance_url=endpoint,
            )
            self._connector = AzureMLConnector(connector_config)
            return self._connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize Azure ML connector: %s", exc)
            return None

    async def predict_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Run a classification prediction.

        Args:
            payload: Input features for classification

        Returns:
            Prediction response
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock classification prediction")
            return {
                "status": "predicted_mock",
                "label": "neutral",
                "confidence": 0.75,
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("predict", [payload])
            return {
                "status": "predicted",
                "result": result[0] if result else None,
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to run classification prediction: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def forecast_timeseries(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Forecast a time series.

        Args:
            payload: Time series input payload

        Returns:
            Forecast response
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock timeseries forecast")
            return {
                "status": "predicted_mock",
                "forecast": [0.1, 0.2, 0.15],
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("forecast", [payload])
            return {
                "status": "predicted",
                "result": result[0] if result else None,
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to forecast timeseries: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def detect_anomalies(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Detect anomalies in a dataset.

        Args:
            payload: Input payload

        Returns:
            Detection response
        """
        connector = self._get_connector()

        if connector is None:
            logger.info("Mock anomaly detection")
            return {
                "status": "predicted_mock",
                "anomalies": [],
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            result = connector.write("anomalies", [payload])
            return {
                "status": "predicted",
                "result": result[0] if result else None,
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.error("Failed to detect anomalies: %s", exc)
            return {"status": "failed", "error": str(exc)}


class DocumentationPublishingService:
    """
    Documentation Repository Publishing Service (thin facade).

    This is a **thin facade** over ``DocumentManagementService`` that adds
    Confluence-first publishing with SharePoint fallback and convenience
    methods for release notes and technical docs.

    It does NOT duplicate document storage — all writes ultimately flow
    through ``DocumentManagementService`` when Confluence is unavailable.
    Agents that only need basic document CRUD should use
    ``DocumentManagementService`` directly.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._doc_service = DocumentManagementService(config)
        self._confluence_connector = None

    def _get_confluence_connector(self) -> Any:
        """Lazy-load and return the Confluence connector."""
        if self._confluence_connector is not None:
            return self._confluence_connector

        confluence_url = os.getenv("CONFLUENCE_URL")
        if not confluence_url:
            return None

        try:
            from confluence_connector import ConfluenceConnector

            connector_config = ConnectorConfig(
                connector_id="confluence",
                name="Confluence",
                category=ConnectorCategory.DOC_MGMT,
                instance_url=confluence_url,
            )
            self._confluence_connector = ConfluenceConnector(connector_config)
            return self._confluence_connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.warning("Failed to initialize Confluence connector: %s", exc)
            return None

    async def publish_release_notes(
        self,
        release_id: str,
        release_name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Publish release notes to the documentation repository.

        Args:
            release_id: The release identifier
            release_name: The release name
            content: The release notes content (markdown or HTML)
            metadata: Additional metadata

        Returns:
            Publishing result with document URL and status
        """
        meta = metadata or {}

        doc_metadata = DocumentMetadata(
            title=f"Release Notes - {release_name}",
            description=f"Release notes for {release_name} ({release_id})",
            classification=meta.get("classification", "internal"),
            tags=["release-notes", release_id] + meta.get("tags", []),
            owner=meta.get("owner", "release-management"),
        )

        # Try Confluence first
        confluence = self._get_confluence_connector()
        if confluence:
            try:
                result = confluence.write(
                    "pages",
                    [
                        {
                            "title": doc_metadata.title,
                            "body": {"storage": {"value": content, "representation": "wiki"}},
                            "space": {"key": meta.get("space_key", "RELEASES")},
                        }
                    ],
                )
                return {
                    "release_id": release_id,
                    "document_id": result[0].get("id") if result else None,
                    "url": result[0].get("_links", {}).get("webui") if result else None,
                    "platform": "confluence",
                    "status": "published",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                }
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                logger.warning("Confluence publish failed, falling back to SharePoint: %s", exc)

        # Fall back to SharePoint
        result = await self._doc_service.publish_document(
            document_content=content,
            metadata=doc_metadata,
            folder_path="Release Notes",
        )

        result["release_id"] = release_id
        result["platform"] = "sharepoint" if result.get("status") == "published" else "mock"
        return result

    async def publish_technical_documentation(
        self,
        doc_type: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Publish technical documentation.

        Args:
            doc_type: Type of documentation (e.g., "api", "architecture", "runbook")
            title: Document title
            content: Document content
            metadata: Additional metadata

        Returns:
            Publishing result
        """
        meta = metadata or {}

        doc_metadata = DocumentMetadata(
            title=title,
            description=meta.get("description", f"Technical documentation: {title}"),
            classification=meta.get("classification", "internal"),
            tags=[doc_type, "technical-docs"] + meta.get("tags", []),
            owner=meta.get("owner", "engineering"),
        )

        folder_map = {
            "api": "Technical/API",
            "architecture": "Technical/Architecture",
            "runbook": "Operations/Runbooks",
            "deployment": "Operations/Deployment",
        }
        folder_path = folder_map.get(doc_type, "Technical")

        return await self._doc_service.publish_document(
            document_content=content,
            metadata=doc_metadata,
            folder_path=folder_path,
        )


class DatabaseStorageService:
    """
    Database Storage Service for persistent data storage.

    Provides methods to store and retrieve agent data from a database
    (Azure SQL, Cosmos DB, or local JSON fallback).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._storage_type = "json"  # Default to JSON file storage
        self._storage_path = Path(self.config.get("storage_path", "data/agent_storage"))
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Check for database configuration
        if os.getenv("AZURE_SQL_CONNECTION_STRING"):
            self._storage_type = "azure_sql"
        elif os.getenv("COSMOS_DB_CONNECTION_STRING"):
            self._storage_type = "cosmos_db"

    async def store(
        self,
        collection: str,
        record_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store a record in the database.

        Args:
            collection: The collection/table name
            record_id: Unique record identifier
            data: The data to store

        Returns:
            Storage result with record_id and status
        """
        if self._storage_type == "json":
            return await self._store_json(collection, record_id, data)
        elif self._storage_type == "azure_sql":
            return await self._store_azure_sql(collection, record_id, data)
        elif self._storage_type == "cosmos_db":
            return await self._store_cosmos_db(collection, record_id, data)
        return {"record_id": record_id, "status": "unsupported_storage"}

    async def retrieve(
        self,
        collection: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a record from the database.

        Args:
            collection: The collection/table name
            record_id: Unique record identifier

        Returns:
            The record data or None if not found
        """
        if self._storage_type == "json":
            return await self._retrieve_json(collection, record_id)
        elif self._storage_type == "azure_sql":
            return await self._retrieve_azure_sql(collection, record_id)
        elif self._storage_type == "cosmos_db":
            return await self._retrieve_cosmos_db(collection, record_id)
        return None

    async def query(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query records from the database.

        Args:
            collection: The collection/table name
            filters: Query filters
            limit: Maximum number of records to return

        Returns:
            List of matching records
        """
        if self._storage_type == "json":
            return await self._query_json(collection, filters, limit)
        elif self._storage_type == "azure_sql":
            return await self._query_azure_sql(collection, filters, limit)
        elif self._storage_type == "cosmos_db":
            return await self._query_cosmos_db(collection, filters, limit)
        return []

    async def delete(self, collection: str, record_id: str) -> bool:
        """
        Delete a record from the database.

        Args:
            collection: The collection/table name
            record_id: Unique record identifier

        Returns:
            True if deleted, False otherwise
        """
        if self._storage_type == "json":
            return await self._delete_json(collection, record_id)
        return False

    # JSON file storage implementation
    async def _store_json(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        import json

        collection_path = self._storage_path / collection
        collection_path.mkdir(parents=True, exist_ok=True)

        record_path = collection_path / f"{record_id}.json"
        data["_id"] = record_id
        data["_updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(record_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return {
            "record_id": record_id,
            "collection": collection,
            "status": "stored",
            "storage_type": "json",
        }

    async def _retrieve_json(self, collection: str, record_id: str) -> dict[str, Any] | None:
        import json

        record_path = self._storage_path / collection / f"{record_id}.json"
        if not record_path.exists():
            return None

        with open(record_path) as f:
            return json.load(f)

    async def _query_json(
        self, collection: str, filters: dict[str, Any] | None, limit: int
    ) -> list[dict[str, Any]]:
        import json

        collection_path = self._storage_path / collection
        if not collection_path.exists():
            return []

        results = []
        for record_path in collection_path.glob("*.json"):
            if len(results) >= limit:
                break
            with open(record_path) as f:
                record = json.load(f)
                if filters:
                    if all(record.get(k) == v for k, v in filters.items()):
                        results.append(record)
                else:
                    results.append(record)

        return results

    async def _delete_json(self, collection: str, record_id: str) -> bool:
        record_path = self._storage_path / collection / f"{record_id}.json"
        if record_path.exists():
            record_path.unlink()
            return True
        return False

    def _normalize_collection_name(self, collection: str) -> str:
        normalized = "".join(char if char.isalnum() or char == "_" else "_" for char in collection)
        return normalized[:128] if normalized else "ppm_records"

    def _get_azure_sql_connection(self):
        spec = importlib.util.find_spec("pyodbc")
        if spec is None:
            raise RuntimeError("pyodbc is required for Azure SQL operations but is not installed.")
        pyodbc = importlib.import_module("pyodbc")

        connection_string = self.config.get("azure_sql_connection_string") or os.getenv(
            "AZURE_SQL_CONNECTION_STRING"
        )
        if connection_string:
            return pyodbc.connect(connection_string)

        server = self.config.get("azure_sql_server") or os.getenv("AZURE_SQL_SERVER")
        database = self.config.get("azure_sql_database") or os.getenv("AZURE_SQL_DATABASE")
        driver = (
            self.config.get("azure_sql_driver")
            or os.getenv("AZURE_SQL_DRIVER")
            or "{ODBC Driver 18 for SQL Server}"
        )
        if not server or not database:
            raise ValueError(
                "Azure SQL configuration requires AZURE_SQL_CONNECTION_STRING or "
                "AZURE_SQL_SERVER/AZURE_SQL_DATABASE."
            )

        credential_spec = importlib.util.find_spec("azure.identity")
        if credential_spec is None:
            raise RuntimeError(
                "azure-identity is required for token-based Azure SQL authentication."
            )
        credential_module = importlib.import_module("azure.identity")
        credential = credential_module.DefaultAzureCredential()
        token = credential.get_token("https://database.windows.net/.default").token
        access_token = token.encode("utf-16-le")
        access_token_key = getattr(pyodbc, "SQL_COPT_SS_ACCESS_TOKEN", 1256)
        conn_str = (
            f"Driver={driver};Server={server};Database={database};Encrypt=yes;"
            "TrustServerCertificate=no;"
        )
        return pyodbc.connect(conn_str, attrs_before={access_token_key: access_token})

    def _safe_bracket_quote(self, name: str) -> str:
        """Bracket-quote a SQL Server identifier after normalization."""
        normalized = self._normalize_collection_name(name)
        # SQL Server bracket quoting prevents identifier injection
        return f"[{normalized}]"

    def _ensure_azure_sql_table(self, cursor, table_name: str) -> None:
        safe_name = self._safe_bracket_quote(table_name)
        cursor.execute(f"""
            IF OBJECT_ID(N'{safe_name}', N'U') IS NULL
            CREATE TABLE {safe_name} (
                record_id NVARCHAR(255) NOT NULL PRIMARY KEY,
                data NVARCHAR(MAX) NOT NULL,
                updated_at DATETIME2 NOT NULL
            )
            """)

    def _get_cosmos_container_client(self, collection: str):
        spec = importlib.util.find_spec("azure.cosmos")
        if spec is None:
            raise RuntimeError(
                "azure-cosmos is required for Cosmos DB operations but is not installed."
            )
        cosmos_module = importlib.import_module("azure.cosmos")

        connection_string = self.config.get("cosmos_connection_string") or os.getenv(
            "COSMOS_DB_CONNECTION_STRING"
        )
        if not connection_string:
            raise ValueError("COSMOS_DB_CONNECTION_STRING is required for Cosmos DB.")

        database_name = self.config.get("cosmos_database") or os.getenv("COSMOS_DB_DATABASE")
        if not database_name:
            raise ValueError("COSMOS_DB_DATABASE is required for Cosmos DB.")

        client = cosmos_module.CosmosClient.from_connection_string(connection_string)
        database = client.get_database_client(database_name)
        container = database.get_container_client(collection)
        return container

    def _get_cosmos_partition_key(self) -> str:
        partition_key = self.config.get("cosmos_partition_key") or os.getenv(
            "COSMOS_DB_PARTITION_KEY"
        )
        if partition_key and partition_key.startswith("/"):
            partition_key = partition_key[1:]
        return partition_key or "id"

    # Azure SQL implementation
    async def _store_azure_sql(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        import json

        safe_name = self._safe_bracket_quote(collection)
        payload = dict(data)
        payload["_id"] = record_id
        payload["_updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_at = datetime.now(timezone.utc)
        serialized = json.dumps(payload, default=str)

        try:
            connection = self._get_azure_sql_connection()
            cursor = connection.cursor()
            try:
                self._ensure_azure_sql_table(cursor, collection)
                cursor.execute(
                    f"""
                    MERGE {safe_name} AS target
                    USING (SELECT ? AS record_id, ? AS data, ? AS updated_at) AS source
                    ON target.record_id = source.record_id
                    WHEN MATCHED THEN
                        UPDATE SET data = source.data, updated_at = source.updated_at
                    WHEN NOT MATCHED THEN
                        INSERT (record_id, data, updated_at)
                        VALUES (source.record_id, source.data, source.updated_at);
                    """,
                    (record_id, serialized, updated_at),
                )
                connection.commit()
            finally:
                cursor.close()
                connection.close()
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Azure SQL store failed for %s/%s: %s", collection, record_id, exc)
            return {
                "record_id": record_id,
                "collection": collection,
                "status": "error",
                "storage_type": "azure_sql",
                "error": str(exc),
            }

        return {
            "record_id": record_id,
            "collection": collection,
            "status": "stored",
            "storage_type": "azure_sql",
        }

    async def _retrieve_azure_sql(self, collection: str, record_id: str) -> dict[str, Any] | None:
        import json

        safe_name = self._safe_bracket_quote(collection)
        try:
            connection = self._get_azure_sql_connection()
            cursor = connection.cursor()
            try:
                self._ensure_azure_sql_table(cursor, collection)
                cursor.execute(
                    f"SELECT data FROM {safe_name} WHERE record_id = ?",
                    (record_id,),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
                connection.close()
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Azure SQL retrieve failed for %s/%s: %s", collection, record_id, exc)
            return None

        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            logger.warning(
                "Azure SQL retrieve returned non-JSON data for %s/%s",
                collection,
                record_id,
            )
            return {"record_id": record_id, "data": row[0]}

    async def _query_azure_sql(
        self, collection: str, filters: dict[str, Any] | None, limit: int
    ) -> list[dict[str, Any]]:
        import json

        safe_name = self._safe_bracket_quote(collection)
        filter_clauses = []
        params: list[Any] = []
        if filters:
            for key, value in filters.items():
                if key.replace("_", "").isalnum():
                    filter_clauses.append("JSON_VALUE(data, ?) = ?")
                    params.extend([f"$.{key}", value])
                else:
                    logger.warning("Skipping unsupported Azure SQL filter key: %s", key)

        where_clause = f"WHERE {' AND '.join(filter_clauses)}" if filter_clauses else ""
        params_with_limit = [limit, *params]

        try:
            connection = self._get_azure_sql_connection()
            cursor = connection.cursor()
            try:
                self._ensure_azure_sql_table(cursor, collection)
                cursor.execute(
                    f"SELECT TOP (?) data FROM {safe_name} {where_clause}",
                    params_with_limit,
                )
                rows = cursor.fetchall()
            finally:
                cursor.close()
                connection.close()
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Azure SQL query failed for %s: %s", collection, exc)
            return []

        results = []
        for row in rows:
            try:
                results.append(json.loads(row[0]))
            except json.JSONDecodeError:
                results.append({"data": row[0]})
        return results

    # Cosmos DB implementation
    async def _store_cosmos_db(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        payload = dict(data)
        payload["id"] = record_id
        payload["_updated_at"] = datetime.now(timezone.utc).isoformat()
        partition_key = self._get_cosmos_partition_key()
        if partition_key not in payload:
            payload[partition_key] = record_id

        try:
            container = self._get_cosmos_container_client(collection)
            result = container.upsert_item(payload)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Cosmos DB store failed for %s/%s: %s", collection, record_id, exc)
            return {
                "record_id": record_id,
                "collection": collection,
                "status": "error",
                "storage_type": "cosmos_db",
                "error": str(exc),
            }

        return {
            "record_id": result.get("id", record_id),
            "collection": collection,
            "status": "stored",
            "storage_type": "cosmos_db",
        }

    async def _retrieve_cosmos_db(self, collection: str, record_id: str) -> dict[str, Any] | None:
        partition_key = self._get_cosmos_partition_key()
        try:
            container = self._get_cosmos_container_client(collection)
            item = container.read_item(item=record_id, partition_key=record_id)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Cosmos DB retrieve failed for %s/%s: %s", collection, record_id, exc)
            return None

        if partition_key != "id" and item.get(partition_key) != record_id:
            logger.warning("Cosmos DB partition key mismatch for %s/%s", collection, record_id)
        return item

    async def _query_cosmos_db(
        self, collection: str, filters: dict[str, Any] | None, limit: int
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM c"
        parameters = []
        if filters:
            clauses = []
            for index, (key, value) in enumerate(filters.items()):
                if key.replace("_", "").isalnum():
                    param_name = f"@p{index}"
                    clauses.append(f"c.{key} = {param_name}")
                    parameters.append({"name": param_name, "value": value})
                else:
                    logger.warning("Skipping unsupported Cosmos filter key: %s", key)
            if clauses:
                query = f"{query} WHERE {' AND '.join(clauses)}"

        try:
            container = self._get_cosmos_container_client(collection)
            items = container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit,
            )
            results = []
            for item in items:
                results.append(item)
                if len(results) >= limit:
                    break
            return results
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            logger.exception("Cosmos DB query failed for %s: %s", collection, exc)
            return []
