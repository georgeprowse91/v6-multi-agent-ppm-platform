"""
Agent 3: Approval Workflow Agent

Orchestrates human-in-the-loop approval processes across the PPM platform.
Handles routing, escalation, delegation, and audit trail for governance compliance.
"""

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agents.runtime import BaseAgent

DATA_SYNC_ROOT = Path(__file__).resolve().parents[5] / "services" / "data-sync-service" / "src"
if str(DATA_SYNC_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_SYNC_ROOT))

from data_sync_status import StatusStore  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402

from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402


class ApprovalStore:
    def __init__(self, path: Path) -> None:
        self.store = StatusStore(path)

    def _key(self, tenant_id: str, approval_id: str) -> str:
        return f"{tenant_id}:{approval_id}"

    def create(self, tenant_id: str, approval_id: str, details: dict[str, Any]) -> None:
        key = self._key(tenant_id, approval_id)
        self.store.create(key, tenant_id, "pending")
        self.store.update(key, "pending", details)

    def update(
        self, tenant_id: str, approval_id: str, status: str, details: dict[str, Any]
    ) -> None:
        key = self._key(tenant_id, approval_id)
        self.store.update(key, status, details)

    def get(self, tenant_id: str, approval_id: str) -> dict[str, Any] | None:
        key = self._key(tenant_id, approval_id)
        record = self.store.get(key)
        if not record:
            return None
        return {
            "approval_id": approval_id,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "tenant_id": tenant_id,
            "details": record.details,
        }


class RoleLookupClient:
    def __init__(self, config: dict[str, Any] | None) -> None:
        self.config = config or {}
        self.role_directory = self.config.get("role_directory", {})

    async def get_users_for_roles(self, tenant_id: str, roles: list[str]) -> dict[str, list[str]]:
        resolved: dict[str, list[str]] = {}
        for role in roles:
            users = self.role_directory.get(role, [])
            resolved[role] = list(users)
        return resolved


class ApprovalWorkflowAgent(BaseAgent):
    """
    Manages approval workflows with role-based routing, multi-level chains,
    delegation management, and escalation handling.
    """

    def __init__(
        self,
        agent_id: str = "agent_003_approval_workflow",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)
        self.approval_chains: dict[str, Any] = {}
        self.approval_policies: dict[str, Any] = {}
        self.delegation_records: dict[str, Any] = {}
        self.notifications: list[dict[str, Any]] = []
        self.approval_store = ApprovalStore(
            Path(
                config.get("approval_store_path", "data/approval_store.json")
                if config
                else "data/approval_store.json"
            )
        )
        self.role_lookup = config.get("role_lookup") if config else None
        if self.role_lookup is None:
            self.role_lookup = RoleLookupClient(config)

    async def initialize(self) -> None:
        """Initialize approval workflow configurations and connections."""
        await super().initialize()
        self.logger.info("Initializing Approval Workflow Agent...")

        # Load approval policies and routing rules
        self.approval_policies = await self._load_approval_policies()

        # Future work: Initialize Azure Service Bus subscriptions for approval events
        # Future work: Connect to Microsoft Graph API for user/role lookups

        self.logger.info("Approval Workflow Agent initialized successfully")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate approval request input data."""
        if input_data.get("decision") and input_data.get("approval_id"):
            return True
        required_fields = ["request_type", "request_id", "requester", "details"]

        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"Missing required field: {field}")
                return False

        valid_types = [
            "budget_change",
            "scope_change",
            "procurement",
            "phase_gate",
            "resource_change",
        ]
        if input_data["request_type"] not in valid_types:
            self.logger.error(f"Invalid request_type: {input_data['request_type']}")
            return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process approval workflow request.

        Args:
            input_data: {
                "request_type": "budget_change" | "scope_change" | "procurement" | "phase_gate" | "resource_change",
                "request_id": "unique_request_id",
                "requester": "user_id",
                "details": {
                    "amount": 50000,  # For budget/procurement
                    "description": "Request description",
                    "justification": "Business justification",
                    "urgency": "high" | "medium" | "low"
                },
                "project_id": "optional_project_id"
            }

        Returns:
            {
                "approval_id": "unique_approval_id",
                "approvers": ["user_id1", "user_id2"],
                "approval_chain": "sequential" | "parallel",
                "deadline": "ISO datetime",
                "status": "pending" | "approved" | "rejected",
                "notifications_sent": true
            }
        """
        if input_data.get("decision") and input_data.get("approval_id"):
            context = input_data.get("context", {})
            tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
            correlation_id = (
                context.get("correlation_id")
                or input_data.get("correlation_id")
                or str(uuid.uuid4())
            )
            return await self._record_decision(
                approval_id=input_data["approval_id"],
                decision=input_data["decision"],
                approver_id=input_data.get("approver_id", "unknown"),
                comments=input_data.get("comments"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        request_type = input_data["request_type"]
        request_id = input_data["request_id"]
        details = input_data["details"]
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        self.logger.info(f"Processing {request_type} approval request: {request_id}")

        # Determine approvers based on routing rules
        approvers, delegation_records = await self._determine_approvers(
            tenant_id, request_type, details
        )

        # Create approval chain
        approval_chain = await self._create_approval_chain(
            tenant_id=tenant_id,
            request_id=request_id,
            request_type=request_type,
            approvers=approvers,
            details=details,
            delegation_records=delegation_records,
        )

        # Send notifications
        notifications_sent = await self._send_approval_notifications(
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approvers=approvers,
            details=details,
        )

        # Set escalation timers
        await self._schedule_escalations(approval_chain)

        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="approval.created",
            outcome="success",
            resource_id=approval_chain["id"],
            metadata={"request_type": request_type, "approvers": approvers},
        )

        return {
            "approval_id": approval_chain["id"],
            "approvers": approvers,
            "approval_chain": approval_chain["type"],
            "deadline": approval_chain["deadline"],
            "status": "pending",
            "notifications_sent": notifications_sent,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "request_type": request_type,
                "escalation_scheduled": True,
            },
        }

    async def _determine_approvers(
        self, tenant_id: str, request_type: str, details: dict[str, Any]
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Determine required approvers based on request type and thresholds."""
        roles = []

        if request_type == "budget_change":
            amount = details.get("amount", 0)

            # Threshold-based routing
            if amount < 10000:
                roles = ["project_manager"]
            elif amount < 50000:
                roles = ["project_manager", "sponsor"]
            elif amount < 100000:
                roles = ["project_manager", "sponsor", "finance_director"]
            else:
                roles = ["project_manager", "sponsor", "finance_director", "cfo"]

        elif request_type == "scope_change":
            roles = ["project_manager", "sponsor", "change_control_board"]

        elif request_type == "procurement":
            amount = details.get("amount", 0)
            if amount < 25000:
                roles = ["project_manager"]
            else:
                roles = ["project_manager", "procurement_manager", "finance_director"]

        elif request_type == "phase_gate":
            roles = ["project_manager", "sponsor", "steering_committee"]

        elif request_type == "resource_change":
            roles = ["project_manager", "resource_manager"]

        resolved = await self.role_lookup.get_users_for_roles(tenant_id, roles)
        approvers = []
        for role in roles:
            approvers.extend(resolved.get(role, []))
        approvers = list(dict.fromkeys(approvers))

        approvers, delegation_records = self._apply_delegations(approvers)
        return approvers, delegation_records

    async def _create_approval_chain(
        self,
        *,
        tenant_id: str,
        request_id: str,
        request_type: str,
        approvers: list[str],
        details: dict[str, Any],
        delegation_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create approval chain configuration."""
        approval_id = f"approval_{request_id}_{datetime.utcnow().timestamp()}"

        # Determine chain type based on request
        chain_type = "sequential" if len(approvers) > 2 else "parallel"

        # Calculate deadline based on urgency
        urgency = details.get("urgency", "medium")
        deadline_hours = {"high": 24, "medium": 72, "low": 120}
        deadline = datetime.utcnow() + timedelta(hours=deadline_hours[urgency])

        chain = {
            "id": approval_id,
            "request_id": request_id,
            "type": chain_type,
            "approvers": approvers,
            "deadline": deadline.isoformat(),
            "current_step": 0,
            "responses": {},
            "created_at": datetime.utcnow().isoformat(),
            "delegations": delegation_records,
        }

        self.approval_chains[approval_id] = chain
        self.approval_store.create(
            tenant_id,
            approval_id,
            {
                "request_type": request_type,
                "request_id": request_id,
                "approvers": approvers,
                "chain": chain,
                "notifications": [],
            },
        )

        return chain

    async def _send_approval_notifications(
        self,
        *,
        tenant_id: str,
        approval_chain: dict[str, Any],
        approvers: list[str],
        details: dict[str, Any],
    ) -> bool:
        """Send approval notifications to approvers via multiple channels."""
        try:
            for approver in approvers:
                # Future work: Use Azure Communication Services or Microsoft Graph
                # Future work: Send email via Office 365
                # Future work: Send Teams/Slack notification
                # Future work: Send mobile push via Azure Notification Hubs

                self.logger.info(f"Sending approval notification to {approver}")

                # Baseline for actual notification
                notification = {
                    "to": approver,
                    "subject": f"Approval Required: {details.get('description', 'N/A')}",
                    "deadline": approval_chain["deadline"],
                    "approval_id": approval_chain["id"],
                    "sent_at": datetime.utcnow().isoformat(),
                }
                self.notifications.append(notification)
                self._persist_notification(tenant_id, approval_chain["id"], notification)

                # Future work: Actual send implementation

            return True
        except Exception as e:
            self.logger.error(f"Failed to send notifications: {str(e)}")
            return False

    async def _schedule_escalations(self, approval_chain: dict[str, Any]) -> None:
        """Schedule escalation timers for overdue approvals."""
        # Future work: Integrate with Azure Functions or Durable Functions for timer triggers
        # Future work: Set reminder notifications 24h before deadline
        # Future work: Set escalation trigger at deadline

        self.logger.info(f"Escalation scheduled for approval {approval_chain['id']}")

    async def _load_approval_policies(self) -> dict[str, Any]:
        """Load approval policies and routing rules from configuration."""
        # Future work: Load from database or configuration file
        return {
            "budget_thresholds": [10000, 50000, 100000],
            "escalation_timeout_hours": 48,
            "reminder_before_deadline_hours": 24,
            "default_chain_type": "sequential",
        }

    def _persist_notification(
        self, tenant_id: str, approval_id: str, notification: dict[str, Any]
    ) -> None:
        existing = self.approval_store.get(tenant_id, approval_id)
        notifications = []
        if existing and isinstance(existing.get("details", {}).get("notifications"), list):
            notifications = list(existing["details"]["notifications"])
        notifications.append(notification)
        details = existing["details"] if existing else {}
        details["notifications"] = notifications
        self.approval_store.update(tenant_id, approval_id, "pending", details)

    def _apply_delegations(self, approvers: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        delegations = self.config.get("delegations", {}) if self.config else {}
        records: list[dict[str, Any]] = []
        resolved: list[str] = []
        for approver in approvers:
            delegate = delegations.get(approver)
            if delegate:
                records.append(
                    {
                        "delegator": approver,
                        "delegate": delegate,
                        "recorded_at": datetime.utcnow().isoformat(),
                    }
                )
                resolved.append(delegate)
            else:
                resolved.append(approver)
        return list(dict.fromkeys(resolved)), records

    async def _record_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        approver_id: str,
        comments: str | None,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        self.approval_store.update(
            tenant_id,
            approval_id,
            decision,
            {
                "decision": decision,
                "decided_by": approver_id,
                "decided_at": datetime.utcnow().isoformat(),
                "comments": comments,
            },
        )
        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="approval.decision",
            outcome="success",
            resource_id=approval_id,
            metadata={
                "decision": decision,
                "approver_id": approver_id,
                "comments": comments,
            },
        )
        return {
            "approval_id": approval_id,
            "decision": decision,
            "status": decision,
        }

    def _emit_audit_event(
        self,
        *,
        tenant_id: str,
        correlation_id: str,
        action: str,
        outcome: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = build_audit_event(
            tenant_id=tenant_id,
            action=action,
            outcome=outcome,
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=resource_id,
            resource_type="approval_workflow",
            metadata=metadata or {},
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Approval Workflow Agent resources...")
        # Future work: Close Service Bus connections
        # Future work: Cancel pending escalation timers
