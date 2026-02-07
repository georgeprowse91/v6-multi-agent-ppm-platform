"""
Agent 3: Approval Workflow Agent

Orchestrates human-in-the-loop approval processes across the PPM platform.
Handles routing, escalation, delegation, and audit trail for governance compliance.
"""

import asyncio
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Any

import httpx
from agents.common.connector_integration import NotificationService
from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore
from integrations.services.integration import AnalyticsClient, EventBusClient, EventEnvelope

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


class NotificationTemplateEngine:
    def __init__(self, templates: dict[str, dict[str, str]], default_locale: str = "en") -> None:
        self.templates = templates
        self.default_locale = default_locale

    def render(self, template_key: str, locale: str, context: dict[str, Any]) -> str:
        locale_templates = self.templates.get(locale) or self.templates.get(self.default_locale, {})
        raw_template = locale_templates.get(template_key) or ""
        return Template(raw_template).safe_substitute(context)


class NotificationSubscriptionStore:
    def __init__(self, path: Path) -> None:
        self.store = TenantStateStore(path)

    def get_preferences(self, tenant_id: str, recipient_id: str) -> dict[str, Any] | None:
        return self.store.get(tenant_id, recipient_id)

    def upsert_preferences(
        self, tenant_id: str, recipient_id: str, preferences: dict[str, Any]
    ) -> None:
        self.store.upsert(tenant_id, recipient_id, preferences)

    def delete_preferences(self, tenant_id: str, recipient_id: str) -> None:
        self.store.delete(tenant_id, recipient_id)


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
        templates = (config or {}).get("notification_templates") or self._default_templates()
        default_locale = (config or {}).get("default_locale", "en")
        self.template_engine = NotificationTemplateEngine(templates, default_locale)
        self.notification_store = NotificationSubscriptionStore(
            Path(
                config.get("notification_store_path", "data/approval_notification_store.json")
                if config
                else "data/approval_notification_store.json"
            )
        )

    async def initialize(self) -> None:
        """Initialize approval workflow configurations and connections."""
        await super().initialize()
        self.logger.info("Initializing Approval Workflow Agent...")

        # Load approval policies and routing rules
        self.approval_policies = await self._load_approval_policies()
        self.notification_service = NotificationService(
            self.config.get("notification", {}) if self.config else None
        )

        await self._initialize_service_bus()
        await self._initialize_graph_client()
        await self._prime_graph_approval_queue()
        self._subscribe_to_approval_responses()

        self.logger.info("Approval Workflow Agent initialized successfully")

    async def _initialize_service_bus(self) -> None:
        service_bus_config = self.config.get("service_bus", {})
        connection_string = service_bus_config.get("connection_string") or os.getenv(
            "SERVICE_BUS_CONNECTION_STRING"
        )
        if not connection_string:
            self.logger.info("Service Bus connection string not configured; skipping setup.")
            return
        if not importlib.util.find_spec("azure.servicebus"):
            self.logger.warning("Azure Service Bus SDK not installed; skipping setup.")
            return

        topic = service_bus_config.get("topic", "approval-events")
        subscription = service_bus_config.get("subscription", f"{self.agent_id}-approvals")
        from azure.servicebus import ServiceBusClient
        from azure.servicebus.management import ServiceBusAdministrationClient

        self.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
        self.service_bus_admin = ServiceBusAdministrationClient.from_connection_string(
            connection_string
        )
        self.service_bus_topic = topic
        self.service_bus_subscription = subscription
        self._ensure_service_bus_entities(topic, subscription)
        self.service_bus_receiver = self.service_bus_client.get_subscription_receiver(
            topic, subscription
        )
        self.logger.info(
            "Service Bus subscription ready for approvals: topic=%s subscription=%s",
            topic,
            subscription,
        )

    def _ensure_service_bus_entities(self, topic: str, subscription: str) -> None:
        if not self.service_bus_admin:
            return
        try:
            self.service_bus_admin.get_topic(topic)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            self.service_bus_admin.create_topic(topic)
        try:
            self.service_bus_admin.get_subscription(topic, subscription)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            self.service_bus_admin.create_subscription(topic, subscription)

    async def _initialize_graph_client(self) -> None:
        graph_config = self.config.get("graph", {})
        tenant_id = graph_config.get("tenant_id") or os.getenv("AZURE_TENANT_ID")
        client_id = graph_config.get("client_id") or os.getenv("AZURE_CLIENT_ID")
        client_secret = graph_config.get("client_secret") or os.getenv("AZURE_CLIENT_SECRET")
        if not tenant_id or not client_id or not client_secret:
            self.logger.info("Microsoft Graph credentials not configured; skipping setup.")
            return
        if not importlib.util.find_spec("msal"):
            self.logger.warning("MSAL not installed; skipping Microsoft Graph setup.")
            return

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        import msal

        app = msal.ConfidentialClientApplication(
            client_id=client_id, authority=authority, client_credential=client_secret
        )
        scopes = graph_config.get("scopes") or ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_silent(scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=scopes)
        access_token = result.get("access_token") if result else None
        if not access_token:
            self.logger.warning("Failed to acquire Microsoft Graph access token.")
            return

        self.graph_client = httpx.AsyncClient(
            base_url="https://graph.microsoft.com/v1.0",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=graph_config.get("timeout", 10.0),
        )

    async def _prime_graph_approval_queue(self) -> None:
        if not self.graph_client:
            return

        graph_config = self.config.get("graph", {})
        user_id = graph_config.get("user_id") or os.getenv("GRAPH_USER_ID")
        if not user_id:
            self.logger.info("Graph user_id not configured; skipping approval queue priming.")
            return

        message_limit = graph_config.get("message_limit", 10)
        task_limit = graph_config.get("task_limit", 10)
        approval_messages = await self._fetch_graph_messages(user_id, message_limit)
        approval_tasks = await self._fetch_graph_tasks(user_id, task_limit)
        self.approval_event_queue.extend(approval_messages)
        self.approval_event_queue.extend(approval_tasks)
        self.logger.info(
            "Primed approval queue with %s Graph messages and %s tasks.",
            len(approval_messages),
            len(approval_tasks),
        )

    async def _fetch_graph_messages(
        self, user_id: str, limit: int
    ) -> list[dict[str, Any]]:
        if not self.graph_client:
            return []
        response = await self.graph_client.get(
            f"/users/{user_id}/messages",
            params={"$top": limit, "$search": "\"approval\""},
            headers={"ConsistencyLevel": "eventual"},
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {"source": "graph", "type": "message", "payload": item}
            for item in payload.get("value", [])
        ]

    async def _fetch_graph_tasks(self, user_id: str, limit: int) -> list[dict[str, Any]]:
        if not self.graph_client:
            return []
        graph_config = self.config.get("graph", {})
        task_list_id = graph_config.get("task_list_id")
        if not task_list_id:
            task_list_id = await self._resolve_graph_task_list_id(user_id)
        if not task_list_id:
            return []
        response = await self.graph_client.get(
            f"/users/{user_id}/todo/lists/{task_list_id}/tasks",
            params={"$top": limit, "$search": "\"approval\""},
            headers={"ConsistencyLevel": "eventual"},
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {"source": "graph", "type": "task", "payload": item}
            for item in payload.get("value", [])
        ]

    async def _resolve_graph_task_list_id(self, user_id: str) -> str | None:
        if not self.graph_client:
            return None
        response = await self.graph_client.get(f"/users/{user_id}/todo/lists")
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("value", []):
            if "approval" in (item.get("displayName") or "").lower():
                return item.get("id")
        return None

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
        if action := input_data.get("action"):
            return await self._handle_notification_action(action, input_data)
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
        approvers, delegation_records, user_roles = await self._determine_approvers(
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
            user_roles=user_roles,
        )

        # Send notifications
        notifications_sent = await self._send_approval_notifications(
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approvers=approvers,
            details=details,
        )

        # Set escalation timers
        await self._schedule_escalations(
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approvers=approvers,
            details=details,
        )

        self._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="approval.created",
            outcome="success",
            resource_id=approval_chain["id"],
            metadata={"request_type": request_type, "approvers": approvers},
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
                "created_at": datetime.utcnow().isoformat(),
                "request_type": request_type,
                "escalation_scheduled": True,
            },
        }

    async def _determine_approvers(
        self, tenant_id: str, request_type: str, details: dict[str, Any]
    ) -> tuple[list[str], list[dict[str, Any]], dict[str, list[str]]]:
        """Determine required approvers based on request type and thresholds."""
        roles: list[str] = []

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
        user_roles: dict[str, list[str]] = {}
        for role in roles:
            role_users = resolved.get(role, [])
            approvers.extend(role_users)
            for user_id in role_users:
                user_roles.setdefault(user_id, []).append(role)
        approvers = list(dict.fromkeys(approvers))

        approvers, delegation_records = self._apply_delegations(approvers)
        return approvers, delegation_records, user_roles

    async def _create_approval_chain(
        self,
        *,
        tenant_id: str,
        request_id: str,
        request_type: str,
        approvers: list[str],
        details: dict[str, Any],
        delegation_records: list[dict[str, Any]],
        user_roles: dict[str, list[str]],
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
            "request_type": request_type,
            "type": chain_type,
            "approvers": approvers,
            "deadline": deadline.isoformat(),
            "current_step": 0,
            "responses": {},
            "created_at": datetime.utcnow().isoformat(),
            "delegations": delegation_records,
            "user_roles": user_roles,
        }

        self.approval_chains[approval_id] = chain
        self.approval_store.create(
            tenant_id,
            approval_id,
            {
                "request_type": request_type,
                "request_id": request_id,
                "approvers": approvers,
                "user_roles": user_roles,
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
        """Send approval notifications to approvers across configured channels."""
        webhook = os.getenv("NOTIFICATION_WEBHOOK_URL")
        notification_results: list[bool] = []
        payloads: list[dict[str, Any]] = []

        for approver in approvers:
            self.logger.info("Sending approval notification to %s", approver)
            context = self._build_notification_context(
                tenant_id=tenant_id,
                approval_chain=approval_chain,
                approver=approver,
                details=details,
            )
            preferences = self._resolve_notification_preferences(
                tenant_id=tenant_id,
                approver=approver,
                approval_chain=approval_chain,
            )
            locale = preferences.get("locale", self.template_engine.default_locale)
            subject = self.template_engine.render("approval_request_subject", locale, context)
            body = self.template_engine.render("approval_request_body", locale, context)
            chat_message = self.template_engine.render("approval_request_chat", locale, context)
            push_message = self.template_engine.render("approval_request_push", locale, context)

            notification = {
                "to": approver,
                "subject": subject,
                "body": body,
                "deadline": approval_chain["deadline"],
                "approval_id": approval_chain["id"],
                "sent_at": datetime.utcnow().isoformat(),
                "channels": preferences.get("channels", {}),
                "delivery": preferences.get("delivery", "immediate"),
            }
            result = await self._dispatch_notification(
                tenant_id=tenant_id,
                recipient=approver,
                notification=notification,
                subject=subject,
                body=body,
                chat_message=chat_message,
                push_message=push_message,
                preferences=preferences,
            )
            notification_results.append(result)
            self.notifications.append(notification)
            self._persist_notification(tenant_id, approval_chain["id"], notification)
            if webhook:
                payloads.append(
                    {
                        "user": approver,
                        "approval_request_id": approval_chain["request_id"],
                        "message": body,
                        "deadline": approval_chain["deadline"],
                    }
                )

        if webhook and payloads:
            tasks = [self._post_webhook(webhook, payload) for payload in payloads]
            await asyncio.gather(*tasks)
        elif not webhook:
            self.logger.warning(
                "NOTIFICATION_WEBHOOK_URL not set; webhook notifications will be skipped."
            )

        return any(notification_results) or bool(webhook)

    async def _send_notification(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if not self.notification_service:
            self.logger.warning(
                "Notification service not initialized; falling back to log-only notification."
            )
            self.logger.info(f"Notification to {recipient}: {subject}")
            return False
        result = await self.notification_service.send_email(recipient, subject, body, metadata)
        status = result.get("status")
        if status in {"sent", "sent_mock", "pending"}:
            return True
        self.logger.warning(
            "Notification service failed to send email to %s with status %s", recipient, status
        )
        return False

    async def _dispatch_notification(
        self,
        *,
        tenant_id: str,
        recipient: str,
        notification: dict[str, Any],
        subject: str,
        body: str,
        chat_message: str,
        push_message: str,
        preferences: dict[str, Any],
    ) -> bool:
        delivery = preferences.get("delivery", "immediate")
        if delivery == "digest":
            self._queue_digest_notification(
                tenant_id=tenant_id,
                recipient=recipient,
                notification=notification,
                subject=subject,
                body=body,
                chat_message=chat_message,
                push_message=push_message,
                preferences=preferences,
            )
            return True
        return await self._deliver_notification(
            tenant_id=tenant_id,
            recipient=recipient,
            notification=notification,
            subject=subject,
            body=body,
            chat_message=chat_message,
            push_message=push_message,
            preferences=preferences,
        )

    async def _deliver_notification(
        self,
        *,
        tenant_id: str,
        recipient: str,
        notification: dict[str, Any],
        subject: str,
        body: str,
        chat_message: str,
        push_message: str,
        preferences: dict[str, Any],
    ) -> bool:
        channels = preferences.get("channels", {})
        results: list[bool] = []

        email_channel = channels.get("email")
        if email_channel:
            email_address = email_channel.get("address") if isinstance(email_channel, dict) else email_channel
            results.append(
                await self._send_notification(
                    recipient=email_address,
                    subject=subject,
                    body=body,
                    metadata={
                        "approval_id": notification["approval_id"],
                        "deadline": notification["deadline"],
                        "html_body": channels.get("email_html"),
                    },
                )
            )

        teams_channel = channels.get("teams")
        if teams_channel and self.notification_service:
            teams_result = await self.notification_service.send_teams_message(
                team_id=teams_channel.get("team_id"),
                channel_id=teams_channel.get("channel_id"),
                message=chat_message,
                chat_id=teams_channel.get("chat_id"),
                user_id=teams_channel.get("user_id"),
            )
            results.append(teams_result.get("status") in {"sent", "sent_mock"})

        slack_channel = channels.get("slack")
        if slack_channel and self.notification_service:
            slack_result = await self.notification_service.send_slack_message(
                destination=slack_channel.get("channel") or slack_channel.get("user_id"),
                message=chat_message,
            )
            results.append(slack_result.get("status") in {"sent", "sent_mock"})

        push_channel = channels.get("push")
        if push_channel and self.notification_service:
            destinations = push_channel.get("destinations", [])
            for destination in destinations:
                push_result = await self.notification_service.send_push_notification(
                    destination, push_message
                )
                results.append(push_result.get("status") in {"sent", "sent_mock"})

        delivered = any(results)
        self._record_delivery_metric(
            tenant_id=tenant_id,
            recipient=recipient,
            approval_id=notification["approval_id"],
            delivered=delivered,
            channels=list(channels.keys()),
        )
        return delivered

    def _queue_digest_notification(
        self,
        *,
        tenant_id: str,
        recipient: str,
        notification: dict[str, Any],
        subject: str,
        body: str,
        chat_message: str,
        push_message: str,
        preferences: dict[str, Any],
    ) -> None:
        key = f"{tenant_id}:{recipient}"
        entry = {
            "notification": notification,
            "subject": subject,
            "body": body,
            "chat_message": chat_message,
            "push_message": push_message,
            "preferences": preferences,
        }
        self.notification_queue.setdefault(key, []).append(entry)
        if key not in self.digest_tasks or self.digest_tasks[key].done():
            interval_minutes = preferences.get("digest_interval_minutes") or self.approval_policies.get(
                "digest_interval_minutes", 60
            )
            self.digest_tasks[key] = asyncio.create_task(
                self._send_digest_notifications_after_delay(
                    tenant_id=tenant_id,
                    recipient=recipient,
                    interval_minutes=interval_minutes,
                )
            )

    async def _send_digest_notifications_after_delay(
        self, *, tenant_id: str, recipient: str, interval_minutes: int
    ) -> None:
        await asyncio.sleep(interval_minutes * 60)
        await self._send_digest_notifications(tenant_id=tenant_id, recipient=recipient)

    async def _send_digest_notifications(self, *, tenant_id: str, recipient: str) -> bool:
        key = f"{tenant_id}:{recipient}"
        entries = self.notification_queue.pop(key, [])
        if not entries:
            return False
        latest = entries[-1]
        preferences = latest["preferences"]
        locale = preferences.get("locale", self.template_engine.default_locale)
        context = {
            "recipient": recipient,
            "count": len(entries),
            "items": self._format_digest_entries(entries),
            "generated_at": datetime.utcnow().isoformat(),
        }
        subject = self.template_engine.render("approval_digest_subject", locale, context)
        body = self.template_engine.render("approval_digest_body", locale, context)
        return await self._deliver_notification(
            tenant_id=tenant_id,
            recipient=recipient,
            notification=latest["notification"],
            subject=subject,
            body=body,
            chat_message=body,
            push_message=subject,
            preferences=preferences,
        )

    async def flush_digest_notifications(self, tenant_id: str, recipient: str) -> bool:
        return await self._send_digest_notifications(tenant_id=tenant_id, recipient=recipient)

    def _format_digest_entries(self, entries: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for entry in entries:
            notification = entry["notification"]
            lines.append(
                f"- {notification['subject']} (approval {notification['approval_id']}, "
                f"deadline {notification['deadline']})"
            )
        return "\n".join(lines)

    def _build_notification_context(
        self,
        *,
        tenant_id: str,
        approval_chain: dict[str, Any],
        approver: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "approval_id": approval_chain["id"],
            "request_id": approval_chain["request_id"],
            "request_type": approval_chain.get("request_type") or details.get("request_type") or details.get("type") or "",
            "description": details.get("description", "Approval required"),
            "justification": details.get("justification", ""),
            "amount": details.get("amount", ""),
            "urgency": details.get("urgency", ""),
            "project_id": details.get("project_id") or approval_chain.get("project_id", ""),
            "deadline": approval_chain["deadline"],
            "approver": approver,
        }

    def _resolve_notification_preferences(
        self,
        *,
        tenant_id: str,
        approver: str,
        approval_chain: dict[str, Any],
    ) -> dict[str, Any]:
        routing = (self.config or {}).get("notification_routing", {})
        default_prefs = routing.get("default", {})
        user_prefs = routing.get("users", {}).get(approver, {})
        group_prefs: dict[str, Any] = {}
        for role in approval_chain.get("user_roles", {}).get(approver, []):
            group_prefs = self._merge_preferences(group_prefs, routing.get("groups", {}).get(role, {}))
        stored = self.notification_store.get_preferences(tenant_id, approver) or {}
        preferences = self._merge_preferences(
            self._merge_preferences(self._merge_preferences(default_prefs, group_prefs), user_prefs),
            stored,
        )

        channels = preferences.setdefault("channels", {})
        if not channels.get("email") and "@" in approver:
            channels["email"] = {"address": approver}
        preferences.setdefault("delivery", "immediate")
        preferences.setdefault("locale", self.template_engine.default_locale)
        return preferences

    def _merge_preferences(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        if not base:
            return dict(override)
        merged = dict(base)
        for key, value in override.items():
            if key == "channels":
                merged.setdefault("channels", {})
                merged["channels"] = {**merged["channels"], **value}
            else:
                merged[key] = value
        return merged

    def _record_delivery_metric(
        self,
        *,
        tenant_id: str,
        recipient: str,
        approval_id: str,
        delivered: bool,
        channels: list[str],
    ) -> None:
        metadata = {
            "tenant_id": tenant_id,
            "recipient": recipient,
            "approval_id": approval_id,
            "channels": channels,
        }
        if delivered:
            self.analytics_client.record_event("approval.notification.sent", metadata)
            self.analytics_client.record_metric("approval.notification.sent.count", 1, metadata)
        else:
            self.analytics_client.record_event("approval.notification.failed", metadata)
            self.analytics_client.record_metric("approval.notification.failed.count", 1, metadata)

    def _record_interaction_metric(
        self,
        *,
        tenant_id: str,
        recipient: str,
        approval_id: str,
        interaction: str,
    ) -> None:
        metadata = {
            "tenant_id": tenant_id,
            "recipient": recipient,
            "approval_id": approval_id,
            "interaction": interaction,
        }
        self.analytics_client.record_event("approval.notification.interaction", metadata)
        self.analytics_client.record_metric(
            f"approval.notification.{interaction}.count", 1, metadata
        )

    def _record_response_metric(
        self,
        *,
        tenant_id: str,
        approval_id: str,
        approver_id: str,
        response_time_seconds: float,
        decision: str,
    ) -> None:
        metadata = {
            "tenant_id": tenant_id,
            "approval_id": approval_id,
            "approver_id": approver_id,
            "decision": decision,
        }
        self.analytics_client.record_metric(
            "approval.response_time.seconds", response_time_seconds, metadata
        )
        self.analytics_client.record_event("approval.decision.recorded", metadata)
        self._adjust_delivery_strategy(
            tenant_id=tenant_id,
            approver_id=approver_id,
            response_time_seconds=response_time_seconds,
        )

    def _adjust_delivery_strategy(
        self, *, tenant_id: str, approver_id: str, response_time_seconds: float
    ) -> None:
        threshold_hours = self.approval_policies.get("response_time_threshold_hours", 48)
        existing = self.notification_store.get_preferences(tenant_id, approver_id) or {}
        delivery = existing.get("delivery", "immediate")
        if response_time_seconds > threshold_hours * 3600 and delivery != "digest":
            updated = {**existing, "delivery": "digest"}
            self.notification_store.upsert_preferences(tenant_id, approver_id, updated)

    async def _post_webhook(self, url: str, payload: dict[str, Any]) -> None:
        """Post a JSON payload to the configured webhook."""
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.logger.error(f"Failed to send notification to {url}: {exc}")

    async def _schedule_escalations(
        self,
        *,
        tenant_id: str,
        approval_chain: dict[str, Any],
        approvers: list[str],
        details: dict[str, Any],
    ) -> None:
        """Schedule escalation notifications based on the configured policy."""
        escalation_timeout_hours = self.approval_policies.get("escalation_timeout_hours", 48)
        delay_seconds = int(escalation_timeout_hours * 3600)

        if not approvers:
            return

        scheduled_at = datetime.utcnow()
        escalation_at = scheduled_at + timedelta(seconds=delay_seconds)
        self.escalation_timers[approval_chain["id"]] = {
            "scheduled_at": scheduled_at.isoformat(),
            "escalation_at": escalation_at.isoformat(),
            "timeout_hours": escalation_timeout_hours,
        }

        async def escalation_task() -> None:
            await asyncio.sleep(delay_seconds)
            await self._send_approval_notifications(
                tenant_id=tenant_id,
                approval_chain=approval_chain,
                approvers=approvers,
                details=details,
            )
            self.escalation_timers[approval_chain["id"]]["last_escalated_at"] = (
                datetime.utcnow().isoformat()
            )

        task = asyncio.create_task(escalation_task())
        self.escalation_timers[approval_chain["id"]]["task"] = task
        self.logger.info(f"Escalation scheduled for approval {approval_chain['id']}")

    async def _load_approval_policies(self) -> dict[str, Any]:
        """Load approval policies and routing rules from configuration."""
        default_policies = {
            "budget_thresholds": [10000, 50000, 100000],
            "escalation_timeout_hours": 48,
            "reminder_before_deadline_hours": 24,
            "default_chain_type": "sequential",
            "digest_interval_minutes": 60,
            "response_time_threshold_hours": 48,
        }
        config_path = Path(
            self.config.get("approval_policies_path", "config/approval_policies.json")
            if self.config
            else "config/approval_policies.json"
        )
        if not config_path.exists():
            self.logger.warning(
                "Approval policies file not found at %s; using defaults.", config_path
            )
            return default_policies
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                self.logger.warning(
                    "Approval policies file %s did not contain an object; using defaults.",
                    config_path,
                )
                return default_policies
            return {**default_policies, **data}
        except (json.JSONDecodeError, OSError) as exc:
            self.logger.warning(
                "Failed to load approval policies from %s: %s; using defaults.",
                config_path,
                exc,
            )
            return default_policies

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
        response_time_seconds = None
        existing = self.approval_store.get(tenant_id, approval_id)
        if existing:
            created_at = existing.get("details", {}).get("chain", {}).get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    response_time_seconds = (
                        datetime.now(timezone.utc) - created_dt.replace(tzinfo=timezone.utc)
                    ).total_seconds()
                except ValueError:
                    response_time_seconds = None
        self.approval_store.update(
            tenant_id,
            approval_id,
            decision,
            {
                "decision": decision,
                "decided_by": approver_id,
                "decided_at": datetime.utcnow().isoformat(),
                "comments": comments,
                "response_time_seconds": response_time_seconds,
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
        if response_time_seconds is not None:
            self._record_response_metric(
                tenant_id=tenant_id,
                approval_id=approval_id,
                approver_id=approver_id,
                response_time_seconds=response_time_seconds,
                decision=decision,
            )
        self._publish_approval_event(
            event_type="approval.decision",
            tenant_id=tenant_id,
            approval_chain=existing.get("details", {}).get("chain") if existing else {},
            payload={
                "approval_id": approval_id,
                "decision": decision,
                "approver_id": approver_id,
                "comments": comments,
            },
        )
        if decision in {"approved", "rejected"}:
            self._publish_approval_event(
                event_type=f"approval.{decision}",
                tenant_id=tenant_id,
                approval_chain=existing.get("details", {}).get("chain") if existing else {},
                payload={
                    "approval_id": approval_id,
                    "approver_id": approver_id,
                    "comments": comments,
                },
            )
        return {
            "approval_id": approval_id,
            "decision": decision,
            "status": decision,
        }

    async def _handle_notification_action(
        self, action: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        tenant_id = input_data.get("tenant_id") or input_data.get("context", {}).get(
            "tenant_id", "unknown"
        )
        recipient = input_data.get("recipient") or input_data.get("user_id")
        if action == "subscribe_notifications":
            preferences = input_data.get("preferences", {})
            if recipient:
                existing = self.notification_store.get_preferences(tenant_id, recipient) or {}
                merged = self._merge_preferences(existing, preferences)
                self.notification_store.upsert_preferences(tenant_id, recipient, merged)
                return {"status": "subscribed", "recipient": recipient, "preferences": merged}
            return {"status": "failed", "reason": "recipient_required"}
        if action == "unsubscribe_notifications":
            if recipient:
                self.notification_store.delete_preferences(tenant_id, recipient)
                return {"status": "unsubscribed", "recipient": recipient}
            return {"status": "failed", "reason": "recipient_required"}
        if action == "update_notification_preferences":
            if recipient:
                preferences = input_data.get("preferences", {})
                self.notification_store.upsert_preferences(tenant_id, recipient, preferences)
                return {"status": "updated", "recipient": recipient, "preferences": preferences}
            return {"status": "failed", "reason": "recipient_required"}
        if action == "record_notification_interaction":
            approval_id = input_data.get("approval_id")
            interaction = input_data.get("interaction")
            if not recipient or not approval_id or not interaction:
                return {"status": "failed", "reason": "missing_fields"}
            self._record_interaction_metric(
                tenant_id=tenant_id,
                recipient=recipient,
                approval_id=approval_id,
                interaction=interaction,
            )
            return {
                "status": "recorded",
                "approval_id": approval_id,
                "recipient": recipient,
                "interaction": interaction,
            }
        return {"status": "failed", "reason": "unsupported_action"}

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
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
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
                    self._record_decision(
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
                    self._record_decision(
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
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("Failed to subscribe to approval responses: %s", exc)

    def _default_templates(self) -> dict[str, dict[str, str]]:
        return {
            "en": {
                "approval_request_subject": "Approval required: ${description}",
                "approval_request_body": (
                    "Hello ${approver},\n\n"
                    "An approval decision is required for request ${request_id}.\n"
                    "Description: ${description}\n"
                    "Urgency: ${urgency}\n"
                    "Deadline: ${deadline}\n\n"
                    "Please review and submit your decision."
                ),
                "approval_request_chat": (
                    "Approval required for request ${request_id}: ${description} "
                    "(deadline ${deadline})."
                ),
                "approval_request_push": "Approval required: ${description} (deadline ${deadline})",
                "approval_digest_subject": "You have ${count} pending approvals",
                "approval_digest_body": (
                    "Here is your approval digest:\n"
                    "${items}\n"
                    "Generated at ${generated_at}."
                ),
                "approval_decision_subject": "Approval ${decision} for ${request_id}",
                "approval_decision_body": (
                    "Approval ${decision} for request ${request_id} by ${approver}.\n"
                    "Comments: ${comments}"
                ),
            },
            "es": {
                "approval_request_subject": "Aprobación requerida: ${description}",
                "approval_request_body": (
                    "Hola ${approver},\n\n"
                    "Se requiere una decisión de aprobación para la solicitud ${request_id}.\n"
                    "Descripción: ${description}\n"
                    "Urgencia: ${urgency}\n"
                    "Fecha límite: ${deadline}\n\n"
                    "Revisa y envía tu decisión."
                ),
                "approval_request_chat": (
                    "Aprobación requerida para la solicitud ${request_id}: ${description} "
                    "(fecha límite ${deadline})."
                ),
                "approval_request_push": "Aprobación requerida: ${description} (fecha límite ${deadline})",
                "approval_digest_subject": "Tienes ${count} aprobaciones pendientes",
                "approval_digest_body": (
                    "Resumen de aprobaciones:\n"
                    "${items}\n"
                    "Generado a las ${generated_at}."
                ),
                "approval_decision_subject": "Aprobación ${decision} para ${request_id}",
                "approval_decision_body": (
                    "Aprobación ${decision} para la solicitud ${request_id} por ${approver}.\n"
                    "Comentarios: ${comments}"
                ),
            },
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
