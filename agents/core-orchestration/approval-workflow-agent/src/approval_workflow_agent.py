"""
Approval Workflow Agent

Orchestrates human-in-the-loop approval processes across the PPM platform.
Handles routing, escalation, delegation, and audit trail for governance compliance.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

import httpx  # noqa: E402
import yaml  # noqa: E402

from agents.common.connector_integration import NotificationService  # noqa: E402
from agents.runtime import BaseAgent  # noqa: E402
from integrations.services.integration import AnalyticsClient, EventBusClient, EventEnvelope  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402

from approval_utils import (  # noqa: E402
    ApprovalStore,
    DelegationClient,
    NotificationSubscriptionStore,
    NotificationTemplateEngine,
    RoleLookupClient,
    default_notification_templates,
)
from actions import (  # noqa: E402
    assess_risk_and_criticality,
    create_approval_chain,
    determine_approvers,
    handle_notification_action,
    record_decision,
    resolve_escalation_timeout,
    schedule_escalations,
    send_approval_notifications,
)
from actions.notification_delivery import send_digest_notifications  # noqa: E402
from actions.lifecycle import (  # noqa: E402
    initialize_graph_client,
    initialize_service_bus,
    prime_graph_approval_queue,
)


class ApprovalWorkflowAgent(BaseAgent):
    """
    Manages approval workflows with role-based routing, multi-level chains,
    delegation management, and escalation handling.
    """

    def __init__(
        self,
        agent_id: str = "approval-workflow-agent",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)
        self.approval_chains: dict[str, Any] = {}
        self.approval_policies: dict[str, Any] = {}
        self.delegation_records: dict[str, Any] = {}
        self.notifications: list[dict[str, Any]] = []
        self.notification_queue: dict[str, list[dict[str, Any]]] = {}
        self.digest_tasks: dict[str, asyncio.Task] = {}
        self.escalation_timers: dict[str, dict[str, Any]] = {}
        self.notification_service: NotificationService | None = None
        self.approval_event_queue: list[dict[str, Any]] = []
        self.analytics_client = AnalyticsClient()
        self.enable_event_publishing = (
            config.get("enable_event_publishing", True) if config else True
        )
        self.event_bus_client = (
            config.get("event_bus_client") if config else None
        ) or EventBusClient()
        self.service_bus_client: Any | None = None
        self.service_bus_admin: Any | None = None
        self.service_bus_topic: str | None = None
        self.service_bus_subscription: str | None = None
        self.service_bus_receiver = None
        self.graph_client: httpx.AsyncClient | None = None
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
        templates = (config or {}).get("notification_templates")
        template_root = Path(__file__).resolve().parent / "templates"
        default_locale = (config or {}).get("default_locale", "en")
        self.template_engine = NotificationTemplateEngine(templates, default_locale, template_root)
        if not self.template_engine.templates:
            self.template_engine.templates = default_notification_templates()
        _notification_store_path = (config or {}).get("notification_store_path")
        self.notification_store = NotificationSubscriptionStore(
            Path(_notification_store_path) if _notification_store_path else None
        )
        self.workflow_config = self._load_workflow_config()
        delegation_settings = self.workflow_config.get("delegation", {})
        self.delegation_enabled = delegation_settings.get("enabled", True)
        merged_rules = {
            **delegation_settings.get("rules", {}),
            **((config or {}).get("delegations", {})),
        }
        self.delegation_client = (config or {}).get("delegation_client") or DelegationClient(
            {
                "default_duration_days": delegation_settings.get("default_duration_days", 14),
                "rules": merged_rules,
            }
        )

    # ------------------------------------------------------------------
    # Configuration loading
    # ------------------------------------------------------------------

    def _load_workflow_config(self) -> dict[str, Any]:
        config_path = Path("ops/config/agents/approval_workflow.yaml")
        if not config_path.exists():
            return {}
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, yaml.YAMLError):
            return {}

    async def _load_approval_policies(self) -> dict[str, Any]:
        """Load approval policies and routing rules from configuration."""
        default_policies = {
            "budget_thresholds": [10000, 50000, 100000],
            "escalation_timeout_hours": 48,
            "risk_thresholds": {"high": 12, "medium": 24, "low": 48},
            "criticality_levels": {"critical": 6, "high": 12, "normal": 24, "low": 48},
            "reminder_before_deadline_hours": 24,
            "default_chain_type": "sequential",
            "digest_interval_minutes": 60,
            "response_time_threshold_hours": 48,
        }
        config_path = Path(
            self.config.get("approval_policies_path", "ops/config/agents/approval_policies.yaml")
            if self.config
            else "ops/config/agents/approval_policies.yaml"
        )
        fallback_path = Path("ops/config/approval_policies.json")
        if not config_path.exists():
            if not fallback_path.exists():
                self.logger.warning(
                    "Approval policies file not found at %s; using defaults.", config_path
                )
                return default_policies
            config_path = fallback_path
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                if config_path.suffix in {".yaml", ".yml"}:
                    data = yaml.safe_load(handle)
                else:
                    data = json.load(handle)
            if not isinstance(data, dict):
                self.logger.warning(
                    "Approval policies file %s did not contain an object; using defaults.",
                    config_path,
                )
                return default_policies
            return {**default_policies, **data}
        except (json.JSONDecodeError, yaml.YAMLError, OSError) as exc:
            self.logger.warning(
                "Failed to load approval policies from %s: %s; using defaults.",
                config_path,
                exc,
            )
            return default_policies

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize approval workflow configurations and connections."""
        await super().initialize()
        self.logger.info("Initializing Approval Workflow Agent...")

        # Load approval policies and routing rules
        self.approval_policies = await self._load_approval_policies()
        self.notification_service = NotificationService(
            self.config.get("notification", {}) if self.config else None
        )

        await initialize_service_bus(self)
        await initialize_graph_client(self)
        await prime_graph_approval_queue(self)
        self._subscribe_to_approval_responses()

        self.logger.info("Approval Workflow Agent initialized successfully")

    async def cleanup(self) -> None:
        if self.graph_client:
            await self.graph_client.aclose()
        if self.service_bus_client:
            self.service_bus_client.close()
        for task in list(self.digest_tasks.values()):
            if not task.done():
                task.cancel()
        for timer in list(self.escalation_timers.values()):
            task = timer.get("task")
            if task and not task.done():
                task.cancel()
        await super().cleanup()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate approval request input data."""
        if input_data.get("decision") and input_data.get("approval_id"):
            return True
        action = input_data.get("action")
        if action in {
            "subscribe_notifications",
            "unsubscribe_notifications",
            "record_notification_interaction",
            "update_notification_preferences",
        }:
            return True
        required_fields = ["request_type", "request_id", "requester", "details"]

        for field in required_fields:
            if field not in input_data:
                self.logger.error("Missing required field: %s", field)
                return False

        valid_types = [
            "budget_change",
            "scope_change",
            "procurement",
            "phase_gate",
            "resource_change",
            "resource_optimization",
        ]
        if input_data["request_type"] not in valid_types:
            self.logger.error("Invalid request_type: %s", input_data["request_type"])
            return False

        return True

    # ------------------------------------------------------------------
    # Core dispatch
    # ------------------------------------------------------------------

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
        if action := input_data.get("action"):
            return await handle_notification_action(self, action, input_data)
        if input_data.get("decision") and input_data.get("approval_id"):
            context = input_data.get("context", {})
            tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
            correlation_id = (
                context.get("correlation_id")
                or input_data.get("correlation_id")
                or str(uuid.uuid4())
            )
            return await record_decision(
                self,
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
        risk_score, criticality_level = assess_risk_and_criticality(
            request_type=request_type,
            details=details,
        )
        escalation_timeout_hours = resolve_escalation_timeout(
            self,
            risk_score=risk_score,
            criticality_level=criticality_level,
        )

        self.logger.info("Processing %s approval request: %s", request_type, request_id)

        # Determine approvers based on routing rules
        approvers, delegation_records, user_roles = await determine_approvers(
            self, tenant_id, request_type, details
        )

        # Create approval chain
        approval_chain = await create_approval_chain(
            self,
            tenant_id=tenant_id,
            request_id=request_id,
            request_type=request_type,
            approvers=approvers,
            details=details,
            delegation_records=delegation_records,
            user_roles=user_roles,
            risk_score=risk_score,
            criticality_level=criticality_level,
            escalation_timeout_hours=escalation_timeout_hours,
        )

        # Send notifications
        notifications_sent = await send_approval_notifications(
            self,
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approvers=approvers,
            details=details,
        )

        # Set escalation timers
        await schedule_escalations(
            self,
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approvers=approvers,
            details=details,
            risk_score=risk_score,
            criticality_level=criticality_level,
            escalation_timeout_hours=escalation_timeout_hours,
        )

        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="approval.created",
            outcome="success",
            resource_id=approval_chain["id"],
            metadata={
                "request_type": request_type,
                "approvers": approvers,
                "risk_score": risk_score,
                "criticality_level": criticality_level,
                "escalation_timeout_hours": escalation_timeout_hours,
            },
        )
        self._publish_approval_event(
            event_type="approval.created",
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            payload={
                "approval_id": approval_chain["id"],
                "request_id": request_id,
                "request_type": request_type,
                "approvers": approvers,
                "deadline": approval_chain["deadline"],
            },
        )
        if notifications_sent:
            self._publish_approval_event(
                event_type="approval.requested",
                tenant_id=tenant_id,
                approval_chain=approval_chain,
                payload={
                    "approval_id": approval_chain["id"],
                    "request_id": request_id,
                    "approvers": approvers,
                    "deadline": approval_chain["deadline"],
                },
            )

        return {
            "approval_id": approval_chain["id"],
            "approvers": approvers,
            "approval_chain": approval_chain["type"],
            "deadline": approval_chain["deadline"],
            "status": "pending",
            "notifications_sent": notifications_sent,
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "request_type": request_type,
                "escalation_scheduled": True,
                "risk_score": risk_score,
                "criticality_level": criticality_level,
                "escalation_timeout_hours": escalation_timeout_hours,
            },
        }

    # ------------------------------------------------------------------
    # Digest flush (public helper)
    # ------------------------------------------------------------------

    async def flush_digest_notifications(self, tenant_id: str, recipient: str) -> bool:
        return await send_digest_notifications(self, tenant_id=tenant_id, recipient=recipient)

    # ------------------------------------------------------------------
    # Event publishing & subscription
    # ------------------------------------------------------------------

    def _publish_approval_event(
        self,
        *,
        event_type: str,
        tenant_id: str,
        approval_chain: dict[str, Any] | None,
        payload: dict[str, Any],
    ) -> None:
        if not self.enable_event_publishing:
            return
        data = {
            **payload,
            "tenant_id": tenant_id,
            "approval_chain": approval_chain or {},
        }
        envelope = EventEnvelope(
            event_type=event_type,
            subject=payload.get("approval_id", "approval"),
            data=data,
            metadata={"tenant_id": tenant_id, "source": self.agent_id},
        )
        try:
            self.event_bus_client.publish_event(envelope)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Failed to publish approval event: %s", exc)

    def _subscribe_to_approval_responses(self) -> None:
        if not self.enable_event_publishing:
            return

        def handler(payload: dict[str, Any]) -> None:
            event_type = payload.get("event_type")
            if event_type not in {"approval.response", "approval.decision"}:
                return
            metadata = payload.get("metadata", {})
            if metadata.get("source") == self.agent_id:
                return
            data = payload.get("data", {})
            approval_id = data.get("approval_id")
            decision = data.get("decision")
            if not approval_id or not decision:
                return
            tenant_id = data.get("tenant_id") or metadata.get("tenant_id", "unknown")
            approver_id = data.get("approver_id", "unknown")
            comments = data.get("comments")
            correlation_id = metadata.get("correlation_id") or str(uuid.uuid4())
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    record_decision(
                        self,
                        approval_id=approval_id,
                        decision=decision,
                        approver_id=approver_id,
                        comments=comments,
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                    )
                )
            except RuntimeError:
                asyncio.run(
                    record_decision(
                        self,
                        approval_id=approval_id,
                        decision=decision,
                        approver_id=approver_id,
                        comments=comments,
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                    )
                )

        try:
            self.event_bus_client.subscribe(handler)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Failed to subscribe to approval responses: %s", exc)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

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
