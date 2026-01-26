"""
Agent 3: Approval Workflow Agent

Orchestrates human-in-the-loop approval processes across the PPM platform.
Handles routing, escalation, delegation, and audit trail for governance compliance.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

from agents.runtime import BaseAgent


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
        self.storage_path = Path(
            config.get("storage_path", "data/approval_chains.json") if config else "data/approval_chains.json"
        )
        self.notification_store_path = Path(
            config.get("notification_store_path", "data/approval_notifications.json")
            if config
            else "data/approval_notifications.json"
        )

    async def initialize(self) -> None:
        """Initialize approval workflow configurations and connections."""
        await super().initialize()
        self.logger.info("Initializing Approval Workflow Agent...")

        # Load approval policies and routing rules
        self.approval_policies = await self._load_approval_policies()
        await self._load_persisted_state()

        # Future work: Initialize Azure Service Bus subscriptions for approval events
        # Future work: Connect to Microsoft Graph API for user/role lookups

        self.logger.info("Approval Workflow Agent initialized successfully")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate approval request input data."""
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
        request_type = input_data["request_type"]
        request_id = input_data["request_id"]
        details = input_data["details"]

        self.logger.info(f"Processing {request_type} approval request: {request_id}")

        # Determine approvers based on routing rules
        approvers = await self._determine_approvers(request_type, details)

        # Create approval chain
        approval_chain = await self._create_approval_chain(
            request_id=request_id, request_type=request_type, approvers=approvers, details=details
        )

        # Send notifications
        notifications_sent = await self._send_approval_notifications(
            approval_chain=approval_chain, approvers=approvers, details=details
        )

        # Set escalation timers
        await self._schedule_escalations(approval_chain)

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

    async def _determine_approvers(self, request_type: str, details: dict[str, Any]) -> list[str]:
        """Determine required approvers based on request type and thresholds."""
        approvers = []

        if request_type == "budget_change":
            amount = details.get("amount", 0)

            # Threshold-based routing
            if amount < 10000:
                approvers = ["project_manager"]
            elif amount < 50000:
                approvers = ["project_manager", "sponsor"]
            elif amount < 100000:
                approvers = ["project_manager", "sponsor", "finance_director"]
            else:
                approvers = ["project_manager", "sponsor", "finance_director", "cfo"]

        elif request_type == "scope_change":
            approvers = ["project_manager", "sponsor", "change_control_board"]

        elif request_type == "procurement":
            amount = details.get("amount", 0)
            if amount < 25000:
                approvers = ["project_manager"]
            else:
                approvers = ["project_manager", "procurement_manager", "finance_director"]

        elif request_type == "phase_gate":
            approvers = ["project_manager", "sponsor", "steering_committee"]

        elif request_type == "resource_change":
            approvers = ["project_manager", "resource_manager"]

        # Future work: Check for delegation and substitute approvers
        # Future work: Query Azure AD for actual user IDs

        return approvers

    async def _create_approval_chain(
        self, request_id: str, request_type: str, approvers: list[str], details: dict[str, Any]
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
        }

        # Store in memory (Future work: persist to database)
        self.approval_chains[approval_id] = chain
        await self._persist_state()

        return chain

    async def _send_approval_notifications(
        self, approval_chain: dict[str, Any], approvers: list[str], details: dict[str, Any]
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
                await self._persist_notifications()

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

    async def _load_persisted_state(self) -> None:
        """Load persisted approval chains and notifications."""
        if self.storage_path.exists():
            self.approval_chains.update(json.loads(self.storage_path.read_text()))
        if self.notification_store_path.exists():
            self.notifications = json.loads(self.notification_store_path.read_text())

    async def _persist_state(self) -> None:
        """Persist approval chains to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.approval_chains, indent=2))
        temp_path.replace(self.storage_path)

    async def _persist_notifications(self) -> None:
        """Persist notification log to storage."""
        self.notification_store_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.notification_store_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.notifications, indent=2))
        temp_path.replace(self.notification_store_path)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Approval Workflow Agent resources...")
        # Future work: Close Service Bus connections
        # Future work: Cancel pending escalation timers
