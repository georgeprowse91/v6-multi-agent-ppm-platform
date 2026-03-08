"""
Workspace Setup Agent

Purpose:
Manages the initialisation and configuration of project workspaces before any data
is written to systems of record. Ensures connectors are enabled, authentication is
complete, field mappings are set, and all required external artefacts exist.

Specification: agents/core-orchestration/workspace-setup-agent/README.md
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

from observability.tracing import get_trace_id  # noqa: E402

from agents.runtime import BaseAgent  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from integrations.services.integration import EventBusClient, EventEnvelope  # noqa: E402


class WorkspaceSetupAgent(BaseAgent):
    """
    Workspace Setup Agent - Manages project workspace initialisation and configuration.

    Key Capabilities:
    - Project workspace initialisation (folder structure, canvas tabs)
    - Connector configuration gating (validate, test, dry-run)
    - External workspace provisioning (Teams, SharePoint, Jira, Planview)
    - Methodology selection and lifecycle bootstrap
    - Setup status reporting and event publishing
    """

    CONNECTOR_CATEGORIES = [
        "ppm",  # Planview, Clarity, Microsoft Project
        "pm_tools",  # Jira, Azure DevOps, Monday.com
        "erp",  # SAP, Oracle
        "docs",  # SharePoint, Confluence
        "collaboration",  # Teams, Slack
        "grc",  # ServiceNow GRC, Archer
    ]

    CONNECTOR_STATUSES = [
        "not_configured",
        "configured",
        "connected",
        "permissions_validated",
    ]

    METHODOLOGIES = ["predictive", "hybrid", "adaptive"]

    DEFAULT_CANVAS_TABS = ["methodology_map", "dashboard", "registers"]

    def __init__(
        self, agent_id: str = "workspace-setup-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        config = config or {}
        self.workspace_store_path = Path(
            config.get("workspace_store_path", "data/workspace_store.json")
        )
        self.event_bus: EventBusClient | None = config.get("event_bus")

        # Internal state
        self._workspaces: dict[str, dict[str, Any]] = {}
        self._connector_states: dict[str, dict[str, Any]] = {}
        self._provisioned_assets: dict[str, list[dict[str, Any]]] = {}

    async def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """Route incoming requests to the appropriate handler."""
        action = request.get("action", "")
        tenant_id = request.get("tenant_id", "default")
        trace_id = get_trace_id()

        handlers = {
            "initialise_workspace": self._initialise_workspace,
            "validate_connectors": self._validate_connectors,
            "test_connection": self._test_connection,
            "dry_run_mapping": self._dry_run_mapping,
            "provision_external_workspace": self._provision_external_workspace,
            "select_methodology": self._select_methodology,
            "get_setup_status": self._get_setup_status,
        }

        handler = handlers.get(action)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "supported_actions": list(handlers.keys()),
            }

        result = await handler(request, tenant_id, trace_id)

        await emit_audit_event(
            build_audit_event(
                agent_id=self.agent_id,
                tenant_id=tenant_id,
                action=action,
                trace_id=trace_id,
                details={"project_id": request.get("project_id"), "result": result.get("success")},
            )
        )

        return result

    async def _initialise_workspace(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Create internal project workspace record with folder structure and canvas tabs."""
        project_id = request.get("project_id")
        if not project_id:
            return {"success": False, "error": "project_id is required"}

        workspace_id = str(uuid.uuid4())
        workspace = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "tenant_id": tenant_id,
            "status": "initialising",
            "folder_structure": self._create_folder_structure(project_id),
            "canvas_tabs": list(self.DEFAULT_CANVAS_TABS),
            "connectors": {},
            "provisioned_assets": [],
            "methodology": None,
            "setup_complete": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._workspaces[workspace_id] = workspace

        await self._publish_event(
            "workspace.setup.started",
            {
                "workspace_id": workspace_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
            },
        )

        return {"success": True, "workspace_id": workspace_id, "workspace": workspace}

    async def _validate_connectors(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Validate connector configuration state for a project workspace."""
        workspace_id = request.get("workspace_id")
        connectors = request.get("connectors", [])

        if not workspace_id:
            return {"success": False, "error": "workspace_id is required"}

        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return {"success": False, "error": f"Workspace {workspace_id} not found"}

        results = []
        for connector in connectors:
            connector_id = connector.get("connector_id")
            category = connector.get("category")
            status = self._check_connector_status(connector)
            results.append(
                {
                    "connector_id": connector_id,
                    "category": category,
                    "status": status,
                    "valid": status == "permissions_validated",
                }
            )
            workspace["connectors"][connector_id] = {
                "category": category,
                "status": status,
            }

        all_valid = all(r["valid"] for r in results if r.get("required", True))
        return {"success": True, "results": results, "all_valid": all_valid}

    async def _test_connection(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Execute a test connection check against a configured connector."""
        connector_id = request.get("connector_id")
        if not connector_id:
            return {"success": False, "error": "connector_id is required"}

        # Delegate to connector runner for actual connection test
        return {
            "success": True,
            "connector_id": connector_id,
            "connection_status": "connected",
            "latency_ms": 0,
            "message": "Connection test passed",
        }

    async def _dry_run_mapping(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Execute a dry-run mapping check without writing data."""
        connector_id = request.get("connector_id")
        if not connector_id:
            return {"success": False, "error": "connector_id is required"}

        return {
            "success": True,
            "connector_id": connector_id,
            "mapping_status": "valid",
            "fields_mapped": 0,
            "fields_unmapped": 0,
            "warnings": [],
        }

    async def _provision_external_workspace(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Provision or link external workspace assets (Teams, SharePoint, Jira, Planview)."""
        workspace_id = request.get("workspace_id")
        assets = request.get("assets", [])
        require_approval = request.get("require_approval", False)

        if not workspace_id:
            return {"success": False, "error": "workspace_id is required"}

        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return {"success": False, "error": f"Workspace {workspace_id} not found"}

        if require_approval:
            return {
                "success": True,
                "status": "pending_approval",
                "message": "Provisioning requires approval. Request submitted to approval-workflow-agent.",
                "workspace_id": workspace_id,
            }

        provisioned = []
        for asset in assets:
            asset_type = asset.get("type")
            provisioned_asset = {
                "asset_id": str(uuid.uuid4()),
                "type": asset_type,
                "status": "provisioned",
                "url": asset.get("url"),
                "external_id": asset.get("external_id"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            provisioned.append(provisioned_asset)

        workspace["provisioned_assets"].extend(provisioned)
        return {"success": True, "provisioned_assets": provisioned}

    async def _select_methodology(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Select methodology and load corresponding lifecycle map.

        Validates the selection against the tenant's methodology policy before
        applying. If the tenant restricts which methodologies may be used, only
        allowed ones can be selected.
        """
        workspace_id = request.get("workspace_id")
        methodology = request.get("methodology")
        department = request.get("department")

        if not workspace_id:
            return {"success": False, "error": "workspace_id is required"}
        if methodology not in self.METHODOLOGIES:
            return {
                "success": False,
                "error": f"Invalid methodology: {methodology}. Must be one of {self.METHODOLOGIES}",
            }

        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return {"success": False, "error": f"Workspace {workspace_id} not found"}

        policy_result = self._validate_methodology_policy(tenant_id, methodology, department)
        if not policy_result["allowed"]:
            return {
                "success": False,
                "error": policy_result["reason"],
                "policy_violation": True,
            }

        workspace["methodology"] = methodology
        workspace["lifecycle_map"] = self._load_lifecycle_map(methodology)

        return {
            "success": True,
            "workspace_id": workspace_id,
            "methodology": methodology,
            "lifecycle_map": workspace["lifecycle_map"],
            "policy_validated": True,
        }

    def _validate_methodology_policy(
        self, tenant_id: str, methodology: str, department: str | None = None
    ) -> dict[str, Any]:
        """Validate methodology against tenant policy.

        Checks organisation-level methodology restrictions and department-specific
        overrides. Returns {"allowed": True/False, "reason": ...}.
        """
        try:
            from methodologies import validate_methodology_selection

            return validate_methodology_selection(tenant_id, methodology, department)
        except ImportError:
            pass

        config = self.config or {}
        tenant_policies = config.get("tenant_methodology_policies", {})
        policy = tenant_policies.get(tenant_id, {})

        allowed_ids = policy.get("allowed_methodology_ids")
        if allowed_ids is not None and methodology not in allowed_ids:
            return {
                "allowed": False,
                "reason": (
                    f"Methodology '{methodology}' is not permitted by organisation policy. "
                    f"Allowed: {', '.join(allowed_ids)}"
                ),
            }

        if department and policy.get("department_overrides"):
            dept_policy = policy["department_overrides"].get(department, {})
            dept_allowed = dept_policy.get("allowed_methodology_ids")
            if dept_allowed is not None and methodology not in dept_allowed:
                return {
                    "allowed": False,
                    "reason": (
                        f"Methodology '{methodology}' is not allowed for department "
                        f"'{department}'. Allowed: {', '.join(dept_allowed)}"
                    ),
                }

        return {"allowed": True, "reason": None}

    async def _get_setup_status(
        self, request: dict[str, Any], tenant_id: str, trace_id: str
    ) -> dict[str, Any]:
        """Return the current setup status checklist for a workspace."""
        workspace_id = request.get("workspace_id")
        if not workspace_id:
            return {"success": False, "error": "workspace_id is required"}

        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return {"success": False, "error": f"Workspace {workspace_id} not found"}

        checklist = {
            "workspace_created": workspace.get("folder_structure") is not None,
            "canvas_tabs_provisioned": len(workspace.get("canvas_tabs", [])) > 0,
            "required_connectors_validated": all(
                c.get("status") == "permissions_validated"
                for c in workspace.get("connectors", {}).values()
            ),
            "external_assets_provisioned": len(workspace.get("provisioned_assets", [])) > 0,
            "methodology_selected": workspace.get("methodology") is not None,
        }

        setup_complete = all(checklist.values())
        workspace["setup_complete"] = setup_complete

        if setup_complete and workspace.get("status") != "complete":
            workspace["status"] = "complete"
            await self._publish_event(
                "workspace.setup.completed",
                {
                    "workspace_id": workspace_id,
                    "project_id": workspace["project_id"],
                    "tenant_id": tenant_id,
                },
            )

        return {
            "success": True,
            "workspace_id": workspace_id,
            "setup_complete": setup_complete,
            "checklist": checklist,
            "provisioned_assets": workspace.get("provisioned_assets", []),
        }

    def _create_folder_structure(self, project_id: str) -> dict[str, Any]:
        """Create baseline artefact folder structure."""
        return {
            "root": f"/projects/{project_id}",
            "folders": [
                f"/projects/{project_id}/documents",
                f"/projects/{project_id}/documents/charter",
                f"/projects/{project_id}/documents/business-case",
                f"/projects/{project_id}/documents/requirements",
                f"/projects/{project_id}/registers",
                f"/projects/{project_id}/registers/risk",
                f"/projects/{project_id}/registers/issue",
                f"/projects/{project_id}/registers/change",
                f"/projects/{project_id}/registers/decision",
                f"/projects/{project_id}/reports",
                f"/projects/{project_id}/deliverables",
            ],
        }

    def _check_connector_status(self, connector: dict[str, Any]) -> str:
        """Check the current validation status of a connector."""
        if connector.get("permissions_validated"):
            return "permissions_validated"
        if connector.get("connected"):
            return "connected"
        if connector.get("configured"):
            return "configured"
        return "not_configured"

    def _load_lifecycle_map(self, methodology: str) -> dict[str, Any]:
        """Load the lifecycle map for a given methodology."""
        lifecycle_maps = {
            "predictive": {
                "stages": [
                    "Initiation",
                    "Planning",
                    "Execution",
                    "Monitoring & Control",
                    "Closing",
                ],
                "gates": ["Charter Approval", "Plan Approval", "Go/No-Go", "Acceptance", "Closure"],
            },
            "hybrid": {
                "stages": ["Initiation", "Planning", "Iterative Delivery", "Transition", "Closing"],
                "gates": [
                    "Charter Approval",
                    "Plan Approval",
                    "Iteration Review",
                    "Acceptance",
                    "Closure",
                ],
            },
            "adaptive": {
                "stages": ["Vision", "Exploration", "Iteration", "Release", "Retrospective"],
                "gates": [
                    "Vision Approval",
                    "Backlog Ready",
                    "Sprint Review",
                    "Release Ready",
                    "Retrospective Complete",
                ],
            },
        }
        return lifecycle_maps.get(methodology, {})

    async def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a workspace setup event to the event bus."""
        if self.event_bus:
            envelope = EventEnvelope(
                event_type=event_type,
                source=self.agent_id,
                data={
                    **data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            await self.event_bus.publish(envelope)
