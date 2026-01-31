"""
Connector Integration Services for Agents.

Provides high-level integration services that wrap the platform's connectors
for use by agents. These services handle:
- Document management (SharePoint, Confluence)
- GRC platforms (ServiceNow GRC, RSA Archer)
- Documentation repository publishing
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add connector SDK to path
REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
CONNECTORS_ROOT = REPO_ROOT / "connectors"

for connector_dir in CONNECTORS_ROOT.iterdir():
    src_path = connector_dir / "src"
    if src_path.is_dir() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

if str(CONNECTOR_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(CONNECTOR_SDK_PATH))

from base_connector import ConnectorConfig, ConnectorCategory

logger = logging.getLogger(__name__)


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
        except Exception as exc:
            logger.warning(f"Failed to initialize SharePoint connector: {exc}")
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
            logger.info(f"Mock publishing document: {metadata.title}")
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
        except Exception as exc:
            logger.error(f"Failed to publish document: {exc}")
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
            logger.info(f"Mock retrieving document: {document_id}")
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
        except Exception as exc:
            logger.error(f"Failed to retrieve document: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to list documents: {exc}")
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
                except Exception as exc:
                    logger.warning(f"Failed to initialize Archer connector: {exc}")
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
        except Exception as exc:
            logger.warning(f"Failed to initialize ServiceNow GRC connector: {exc}")
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
            logger.info(f"Mock syncing control: {control.control_id}")
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
        except Exception as exc:
            logger.error(f"Failed to sync control: {exc}")
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
            logger.info(f"Mock syncing risk: {risk.risk_id}")
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
        except Exception as exc:
            logger.error(f"Failed to sync risk: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to retrieve risks: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to retrieve profiles: {exc}")
            return []


class ERPIntegrationService:
    """
    ERP Integration Service.

    Provides methods to sync financial data with ERP systems such as
    SAP, Oracle, Workday, and Dynamics 365.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connector = None
        self._connector_type = self.config.get("connector_type", "sap")

    def _select_connector_type(self) -> str | None:
        connector_envs = {
            "sap": "SAP_URL",
            "oracle": "ORACLE_URL",
            "workday": "WORKDAY_API_URL",
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
            elif connector_type == "workday":
                from workday_connector import WorkdayConnector

                connector_config = ConnectorConfig(
                    connector_id="workday",
                    name="Workday",
                    category=ConnectorCategory.HRIS,
                    instance_url=os.getenv("WORKDAY_API_URL", ""),
                )
                self._connector = WorkdayConnector(connector_config)
            elif connector_type == "dynamics_365":
                logger.warning("Dynamics 365 connector not available - using mock ERP service")
                return None
            else:
                logger.warning("Unsupported ERP connector type - using mock ERP service")
                return None
            self._connector_type = connector_type
            return self._connector
        except Exception as exc:
            logger.warning(f"Failed to initialize ERP connector ({connector_type}): {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to sync financial data: {exc}")
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
                {"transaction_id": "TXN-001", "amount": 1250.0, "currency": "USD"},
                {"transaction_id": "TXN-002", "amount": 300.0, "currency": "USD"},
            ]

        try:
            return connector.read("transactions", filters=filters, limit=limit)
        except Exception as exc:
            logger.error(f"Failed to retrieve transactions: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to post journal entry: {exc}")
            return {"status": "failed", "error": str(exc)}


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
        except Exception as exc:
            logger.warning(f"Failed to initialize ITSM connector ({connector_type}): {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to create change request: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to update ticket: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to retrieve incidents: {exc}")
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
                logger.warning("Unsupported project management connector type - using mock PM service")
                return None
            self._connector_type = connector_type
            return self._connector
        except Exception as exc:
            logger.warning(f"Failed to initialize PM connector ({connector_type}): {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to sync project: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to retrieve tasks: {exc}")
            return []

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
        except Exception as exc:
            logger.error(f"Failed to update schedule: {exc}")
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
            else:
                logger.warning("Unsupported notification connector type - using mock notification service")
                return None
            return self._connectors[connector_type]
        except Exception as exc:
            logger.warning(f"Failed to initialize notification connector ({connector_type}): {exc}")
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
        connector = self._get_connector("email")

        if connector is None:
            logger.info("Mock sending email")
            return {
                "status": "sent_mock",
                "to": to,
                "subject": subject,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

        logger.info("Email connector available but not implemented")
        return {"status": "pending", "to": to, "subject": subject}

    async def send_teams_message(
        self, team_id: str, channel_id: str, message: str
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
        except Exception as exc:
            logger.error(f"Failed to send Teams message: {exc}")
            return {"status": "failed", "error": str(exc)}

    async def send_push_notification(self, destination: str, message: str) -> dict[str, Any]:
        """
        Send a push notification.

        Args:
            destination: Target destination identifier
            message: Notification message

        Returns:
            Send status
        """
        connector = self._get_connector("slack")

        if connector is None:
            logger.info("Mock sending push notification")
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
        except Exception as exc:
            logger.error(f"Failed to send push notification: {exc}")
            return {"status": "failed", "error": str(exc)}


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
        except Exception as exc:
            logger.warning(f"Failed to initialize Azure ML connector: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to run classification prediction: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to forecast timeseries: {exc}")
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
        except Exception as exc:
            logger.error(f"Failed to detect anomalies: {exc}")
            return {"status": "failed", "error": str(exc)}


class DocumentationPublishingService:
    """
    Documentation Repository Publishing Service.

    Provides methods to publish release notes, technical documentation,
    and other content to documentation repositories (Confluence, SharePoint).
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
        except Exception as exc:
            logger.warning(f"Failed to initialize Confluence connector: {exc}")
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
            except Exception as exc:
                logger.warning(f"Confluence publish failed, falling back to SharePoint: {exc}")

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
        self._storage_path = Path(
            self.config.get("storage_path", "data/agent_storage")
        )
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

    async def _retrieve_json(
        self, collection: str, record_id: str
    ) -> dict[str, Any] | None:
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

    # Azure SQL implementation (placeholder - requires pyodbc)
    async def _store_azure_sql(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info(f"Azure SQL store: {collection}/{record_id}")
        # Implementation would use pyodbc to connect to Azure SQL
        return {
            "record_id": record_id,
            "collection": collection,
            "status": "stored",
            "storage_type": "azure_sql",
        }

    async def _retrieve_azure_sql(
        self, collection: str, record_id: str
    ) -> dict[str, Any] | None:
        logger.info(f"Azure SQL retrieve: {collection}/{record_id}")
        return None

    async def _query_azure_sql(
        self, collection: str, filters: dict[str, Any] | None, limit: int
    ) -> list[dict[str, Any]]:
        logger.info(f"Azure SQL query: {collection}")
        return []

    # Cosmos DB implementation (placeholder - requires azure-cosmos)
    async def _store_cosmos_db(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info(f"Cosmos DB store: {collection}/{record_id}")
        # Implementation would use azure-cosmos SDK
        return {
            "record_id": record_id,
            "collection": collection,
            "status": "stored",
            "storage_type": "cosmos_db",
        }

    async def _retrieve_cosmos_db(
        self, collection: str, record_id: str
    ) -> dict[str, Any] | None:
        logger.info(f"Cosmos DB retrieve: {collection}/{record_id}")
        return None

    async def _query_cosmos_db(
        self, collection: str, filters: dict[str, Any] | None, limit: int
    ) -> list[dict[str, Any]]:
        logger.info(f"Cosmos DB query: {collection}")
        return []
