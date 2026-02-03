"""
Agent 21: Stakeholder & Communications Management Agent

Purpose:
Manages stakeholder identification, classification, engagement planning and communication
execution across the portfolio. Ensures stakeholders receive the right information at the
right time through appropriate channels, fostering engagement and monitoring sentiment.

Specification: agents/operations-management/agent-21-stakeholder-comms/README.md
"""

from datetime import datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

import requests

from agents.common.connector_integration import CalendarIntegrationService, NotificationService
from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore
from connectors.sdk.src.secrets import fetch_keyvault_secret, resolve_secret

if importlib.util.find_spec("slack_sdk"):
    from slack_sdk import WebClient
else:
    WebClient = None

if importlib.util.find_spec("twilio.rest"):
    from twilio.rest import Client as TwilioClient
else:
    TwilioClient = None

if importlib.util.find_spec("azure.communication.email"):
    from azure.communication.email import EmailClient
else:
    EmailClient = None

if importlib.util.find_spec("azure.ai.textanalytics"):
    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential
else:
    TextAnalyticsClient = None
    AzureKeyCredential = None

if importlib.util.find_spec("azure.servicebus"):
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
else:
    ServiceBusClient = None
    ServiceBusMessage = None

if importlib.util.find_spec("sqlalchemy"):
    from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, Text, create_engine
else:
    create_engine = None
    Table = None
    Column = None
    String = None
    Text = None
    DateTime = None
    MetaData = None
    JSON = None

if importlib.util.find_spec("connectors.salesforce.src.main"):
    from connectors.salesforce.src.main import (
        SalesforceConfig,
        _build_client,
        _build_token_manager,
        _request_with_refresh,
    )
else:
    SalesforceConfig = None
    _build_client = None
    _build_token_manager = None
    _request_with_refresh = None


class CommunicationHistoryStore:
    """Persist communications history to a database backend."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self._engine = None
        self._table = None
        self._sqlite_conn = None
        if create_engine:
            self._engine = create_engine(db_url, future=True)
            metadata = MetaData()
            metadata_table = Table(
                "communications_history",
                metadata,
                Column("record_id", String, primary_key=True),
                Column("stakeholder_id", String),
                Column("channel", String),
                Column("subject", String),
                Column("status", String),
                Column("content", Text),
                Column("metadata", JSON),
                Column("created_at", DateTime),
            )
            metadata.create_all(self._engine)
            self._table = metadata_table
        else:
            self._sqlite_conn = sqlite3.connect(self._sqlite_path(db_url))
            self._sqlite_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS communications_history (
                    record_id TEXT PRIMARY KEY,
                    stakeholder_id TEXT,
                    channel TEXT,
                    subject TEXT,
                    status TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
                """
            )
            self._sqlite_conn.commit()

    def _sqlite_path(self, db_url: str) -> str:
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "")
        if db_url.startswith("sqlite://"):
            return db_url.replace("sqlite://", "")
        return ":memory:"

    def add_record(self, record: dict[str, Any]) -> None:
        if self._engine and self._table is not None:
            with self._engine.begin() as conn:
                conn.execute(self._table.insert().values(**record))
            return
        if self._sqlite_conn:
            self._sqlite_conn.execute(
                """
                INSERT OR REPLACE INTO communications_history (
                    record_id, stakeholder_id, channel, subject, status, content, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("record_id"),
                    record.get("stakeholder_id"),
                    record.get("channel"),
                    record.get("subject"),
                    record.get("status"),
                    record.get("content"),
                    json.dumps(record.get("metadata")),
                    record.get("created_at"),
                ),
            )
            self._sqlite_conn.commit()

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
        if self._sqlite_conn:
            self._sqlite_conn.close()


class ServiceBusPublisher:
    """Publish communication events to Azure Service Bus."""

    def __init__(
        self, connection_string: str | None, topic_name: str | None, queue_name: str | None
    ) -> None:
        self.connection_string = connection_string
        self.topic_name = topic_name
        self.queue_name = queue_name
        self.enabled = bool(connection_string) and ServiceBusClient is not None and ServiceBusMessage

    def publish(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled or (not self.topic_name and not self.queue_name):
            return {"status": "skipped", "reason": "service_bus_unavailable"}
        body = json.dumps({"event_type": event_type, "payload": payload})
        with ServiceBusClient.from_connection_string(self.connection_string) as client:
            if self.topic_name:
                with client.get_topic_sender(self.topic_name) as sender:
                    sender.send_messages(ServiceBusMessage(body))
            else:
                with client.get_queue_sender(self.queue_name) as sender:
                    sender.send_messages(ServiceBusMessage(body))
        return {"status": "published", "event_type": event_type}


class StakeholderCommunicationsAgent(BaseAgent):
    """
    Stakeholder & Communications Management Agent - Manages stakeholder engagement and communications.

    Key Capabilities:
    - Stakeholder register and profiling
    - Stakeholder classification and segmentation
    - Communication plan creation
    - Message generation and scheduling
    - Feedback collection and sentiment analysis
    - Event and meeting coordination
    - Communication tracking and analytics
    - Stakeholder engagement dashboards
    """

    def __init__(self, agent_id: str = "agent_021", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.communication_channels = (
            config.get(
                "communication_channels", ["email", "teams", "slack", "sms", "push", "portal"]
            )
            if config
            else ["email", "teams", "slack", "sms", "push", "portal"]
        )

        self.engagement_levels = (
            config.get("engagement_levels", ["high", "medium", "low", "minimal"])
            if config
            else ["high", "medium", "low", "minimal"]
        )

        self.sentiment_threshold = config.get("sentiment_threshold", -0.3) if config else -0.3

        stakeholder_store_path = (
            Path(config.get("stakeholder_store_path", "data/stakeholders.json"))
            if config
            else Path("data/stakeholders.json")
        )
        self.stakeholder_store = TenantStateStore(stakeholder_store_path)

        # Data stores (will be replaced with database)
        self.stakeholder_register: dict[str, Any] = {}
        self.communication_plans: dict[str, Any] = {}
        self.messages: dict[str, Any] = {}
        self.feedback: dict[str, Any] = {}
        self.events: dict[str, Any] = {}
        self.engagement_metrics: dict[str, Any] = {}

        # Secret + integration configuration
        self.keyvault_url = resolve_secret(
            (config or {}).get("keyvault_url") or os.getenv("COMMUNICATIONS_KEYVAULT_URL")
        )
        self.exchange_token = self._resolve_token(
            "EXCHANGE_TOKEN", "EXCHANGE_TOKEN_SECRET_NAME", config
        )
        self.teams_token = self._resolve_token("TEAMS_TOKEN", "TEAMS_TOKEN_SECRET_NAME", config)
        self.slack_token = self._resolve_token(
            "SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN_SECRET_NAME", config
        )
        self.graph_base_url = (config or {}).get(
            "graph_base_url", os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")
        )

        self.acs_connection_string = resolve_secret(
            (config or {}).get("acs_connection_string")
            or os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
        )
        self.sendgrid_api_key = resolve_secret(
            (config or {}).get("sendgrid_api_key") or os.getenv("SENDGRID_API_KEY")
        )
        self.sendgrid_from_email = resolve_secret(
            (config or {}).get("sendgrid_from_email") or os.getenv("SENDGRID_FROM_EMAIL")
        )
        self.twilio_account_sid = resolve_secret(
            (config or {}).get("twilio_account_sid") or os.getenv("TWILIO_ACCOUNT_SID")
        )
        self.twilio_auth_token = resolve_secret(
            (config or {}).get("twilio_auth_token") or os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.twilio_from_number = resolve_secret(
            (config or {}).get("twilio_from_number") or os.getenv("TWILIO_FROM_NUMBER")
        )
        self.push_endpoint = resolve_secret(
            (config or {}).get("push_endpoint") or os.getenv("PUSH_NOTIFICATION_ENDPOINT")
        )
        self.push_api_key = resolve_secret(
            (config or {}).get("push_api_key") or os.getenv("PUSH_NOTIFICATION_API_KEY")
        )
        self.fcm_server_key = resolve_secret(
            (config or {}).get("fcm_server_key") or os.getenv("FCM_SERVER_KEY")
        )

        self.openai_endpoint = resolve_secret(
            (config or {}).get("azure_openai_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.openai_api_key = resolve_secret(
            (config or {}).get("azure_openai_api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        )
        self.openai_deployment = resolve_secret(
            (config or {}).get("azure_openai_deployment")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
        self.openai_api_version = (config or {}).get(
            "azure_openai_api_version", os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        )

        self.text_analytics_endpoint = resolve_secret(
            (config or {}).get("text_analytics_endpoint")
            or os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
        )
        self.text_analytics_key = resolve_secret(
            (config or {}).get("text_analytics_key") or os.getenv("AZURE_TEXT_ANALYTICS_KEY")
        )

        self.azure_ml_endpoint = resolve_secret(
            (config or {}).get("azure_ml_endpoint") or os.getenv("AZURE_ML_ENDPOINT")
        )
        self.azure_ml_key = resolve_secret(
            (config or {}).get("azure_ml_key") or os.getenv("AZURE_ML_API_KEY")
        )

        self.logic_apps_trigger_url = resolve_secret(
            (config or {}).get("logic_apps_trigger_url")
            or os.getenv("LOGIC_APPS_TRIGGER_URL")
            or os.getenv("POWER_AUTOMATE_TRIGGER_URL")
        )

        self.crm_base_url = resolve_secret(
            (config or {}).get("crm_base_url") or os.getenv("CRM_BASE_URL")
        )
        self.crm_api_key = resolve_secret(
            (config or {}).get("crm_api_key") or os.getenv("CRM_API_KEY")
        )
        self.crm_profile_endpoint = (config or {}).get(
            "crm_profile_endpoint", os.getenv("CRM_PROFILE_ENDPOINT", "/api/stakeholders/profile")
        )
        self.crm_upsert_endpoint = (config or {}).get(
            "crm_upsert_endpoint", os.getenv("CRM_UPSERT_ENDPOINT", "/api/stakeholders")
        )
        self.crm_timeout_seconds = int(
            (config or {}).get("crm_timeout_seconds")
            or os.getenv("CRM_TIMEOUT_SECONDS", "10")
        )

        self.service_bus_connection_string = resolve_secret(
            (config or {}).get("service_bus_connection_string")
            or os.getenv("SERVICE_BUS_CONNECTION_STRING")
        )
        self.service_bus_topic = resolve_secret(
            (config or {}).get("service_bus_topic") or os.getenv("SERVICE_BUS_TOPIC")
        )
        self.service_bus_queue = resolve_secret(
            (config or {}).get("service_bus_queue") or os.getenv("SERVICE_BUS_QUEUE")
        )

        self.db_url = (config or {}).get(
            "stakeholder_comms_db_url",
            os.getenv("STAKEHOLDER_COMMS_DB_URL", "sqlite:///data/stakeholder_comms.db"),
        )
        self.history_store = CommunicationHistoryStore(self.db_url)
        self.service_bus_publisher = ServiceBusPublisher(
            self.service_bus_connection_string, self.service_bus_topic, self.service_bus_queue
        )

        self.slack_client = WebClient(token=self.slack_token) if WebClient and self.slack_token else None
        self.twilio_client = (
            TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
            if TwilioClient and self.twilio_account_sid and self.twilio_auth_token
            else None
        )
        self.notification_service = NotificationService(
            (config or {}).get("notification") if config else None
        )
        self.calendar_service = CalendarIntegrationService(
            (config or {}).get("calendar") if config else None
        )

        self.default_locale = (config or {}).get("default_locale", "en-US")
        self.delivery_batch_size = int((config or {}).get("delivery_batch_size", 50))
        self.delivery_batch_interval = int((config or {}).get("delivery_batch_interval_minutes", 15))
        self.digest_window_minutes = int((config or {}).get("digest_window_minutes", 60))
        self.digest_batch_size = int((config or {}).get("digest_batch_size", 10))
        self.digest_queue: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.communication_templates = self._load_default_templates()

    async def initialize(self) -> None:
        """Initialize database connections, communication platforms, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Stakeholder & Communications Management Agent...")


        self.logger.info("Stakeholder & Communications Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "register_stakeholder",
            "classify_stakeholder",
            "create_communication_plan",
            "generate_message",
            "edit_message",
            "send_message",
            "schedule_message",
            "summarize_report",
            "update_communication_preferences",
            "collect_feedback",
            "analyze_sentiment",
            "schedule_event",
            "track_engagement",
            "track_delivery_event",
            "flush_digest_notifications",
            "get_stakeholder_dashboard",
            "generate_communication_report",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "register_stakeholder":
            stakeholder_data = input_data.get("stakeholder", {})
            required_fields = ["name", "email", "role"]
            for field in required_fields:
                if field not in stakeholder_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process stakeholder and communications management requests.

        Args:
            input_data: {
                "action": "register_stakeholder" | "classify_stakeholder" |
                          "create_communication_plan" | "generate_message" |
                          "send_message" | "collect_feedback" | "analyze_sentiment" |
                          "schedule_event" | "track_engagement" |
                          "get_stakeholder_dashboard" | "generate_communication_report",
                "stakeholder": Stakeholder data,
                "plan": Communication plan data,
                "message": Message data,
                "feedback": Feedback data,
                "event": Event data,
                "stakeholder_id": Stakeholder identifier,
                "project_id": Project identifier,
                "filters": Query filters
            }

        Returns:
            Response based on action
        """
        action = input_data.get("action", "get_stakeholder_dashboard")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "register_stakeholder":
            return await self._register_stakeholder(tenant_id, input_data.get("stakeholder", {}))

        elif action == "classify_stakeholder":
            return await self._classify_stakeholder(
                tenant_id, input_data.get("stakeholder_id")  # type: ignore
            )

        elif action == "create_communication_plan":
            return await self._create_communication_plan(input_data.get("plan", {}))

        elif action == "generate_message":
            return await self._generate_message(input_data.get("message", {}))

        elif action == "edit_message":
            return await self._edit_message(
                input_data.get("message_id"), input_data.get("message", {})
            )

        elif action == "send_message":
            return await self._send_message(tenant_id, input_data.get("message_id"))  # type: ignore

        elif action == "schedule_message":
            return await self._schedule_message(tenant_id, input_data.get("message_id"))  # type: ignore

        elif action == "summarize_report":
            return await self._summarize_report(
                input_data.get("report", ""),
                input_data.get("role", "general"),
                input_data.get("locale"),
            )

        elif action == "update_communication_preferences":
            return await self._update_communication_preferences(
                tenant_id,
                input_data.get("stakeholder_id"),
                input_data.get("preferences", {}),
            )

        elif action == "collect_feedback":
            return await self._collect_feedback(input_data.get("feedback", {}))

        elif action == "analyze_sentiment":
            return await self._analyze_sentiment(input_data.get("stakeholder_id"))

        elif action == "schedule_event":
            return await self._schedule_event(input_data.get("event", {}))

        elif action == "track_engagement":
            return await self._track_engagement(input_data.get("stakeholder_id"))

        elif action == "track_delivery_event":
            return await self._track_delivery_event(
                tenant_id,
                input_data.get("message_id"),
                input_data.get("stakeholder_id"),
                input_data.get("event", {}),
            )

        elif action == "flush_digest_notifications":
            return await self._flush_digest_notifications(
                tenant_id, input_data.get("stakeholder_id")
            )

        elif action == "get_stakeholder_dashboard":
            return await self._get_stakeholder_dashboard(
                input_data.get("project_id"), input_data.get("filters", {})
            )

        elif action == "generate_communication_report":
            return await self._generate_communication_report(
                input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _register_stakeholder(
        self, tenant_id: str, stakeholder_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Register new stakeholder."""
        self.logger.info(f"Registering stakeholder: {stakeholder_data.get('name')}")

        # Generate stakeholder ID
        stakeholder_id = await self._generate_stakeholder_id()

        # Enrich profile from CRM
        await self._enrich_stakeholder_profile(stakeholder_data)

        # Suggest classification
        suggested_classification = await self._suggest_classification(stakeholder_data)

        # Create stakeholder profile
        stakeholder = {
            "stakeholder_id": stakeholder_id,
            "name": stakeholder_data.get("name"),
            "email": stakeholder_data.get("email"),
            "phone": stakeholder_data.get("phone"),
            "role": stakeholder_data.get("role"),
            "organization": stakeholder_data.get("organization"),
            "location": stakeholder_data.get("location"),
            "influence": suggested_classification.get("influence", "medium"),
            "interest": suggested_classification.get("interest", "medium"),
            "engagement_level": suggested_classification.get("engagement_level", "medium"),
            "preferred_channels": stakeholder_data.get("preferred_channels", ["email"]),
            "time_zone": stakeholder_data.get("time_zone", "UTC"),
            "communication_preferences": stakeholder_data.get("communication_preferences", {}),
            "consent": stakeholder_data.get("consent", True),
            "opt_out": stakeholder_data.get("opt_out", False),
            "projects": stakeholder_data.get("projects", []),
            "engagement_score": 0,
            "sentiment_score": 0,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store stakeholder
        self.stakeholder_register[stakeholder_id] = stakeholder
        self.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())

        # Initialize engagement metrics
        self.engagement_metrics[stakeholder_id] = {
            "messages_sent": 0,
            "messages_opened": 0,
            "messages_clicked": 0,
            "responses_received": 0,
            "events_attended": 0,
        }

        crm_sync = await self._upsert_crm_profile(stakeholder)
        if crm_sync:
            stakeholder["crm_upserted_at"] = datetime.utcnow().isoformat()
            stakeholder["crm_upsert_status"] = crm_sync
            self.stakeholder_register[stakeholder_id] = stakeholder
            self.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())

        self._publish_event(
            "stakeholder.profile.registered",
            {"stakeholder_id": stakeholder_id, "crm_sync": crm_sync},
        )
        self._trigger_workflow(
            "stakeholder.profile.registered",
            {"stakeholder_id": stakeholder_id, "crm_sync": crm_sync},
        )

        return {
            "stakeholder_id": stakeholder_id,
            "name": stakeholder["name"],
            "suggested_classification": suggested_classification,
            "next_steps": "Classify stakeholder and add to communication plans",
        }

    async def _classify_stakeholder(self, tenant_id: str, stakeholder_id: str) -> dict[str, Any]:
        """Classify stakeholder using power-interest matrix."""
        self.logger.info(f"Classifying stakeholder: {stakeholder_id}")

        stakeholder = self._load_stakeholder(tenant_id, stakeholder_id)
        if not stakeholder:
            raise ValueError(f"Stakeholder not found: {stakeholder_id}")

        # Classify based on influence and interest
        influence = stakeholder.get("influence", "medium")
        interest = stakeholder.get("interest", "medium")

        # Determine engagement strategy
        engagement_strategy = await self._determine_engagement_strategy(influence, interest)

        # Update stakeholder
        stakeholder["engagement_strategy"] = engagement_strategy
        self.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())


        return {
            "stakeholder_id": stakeholder_id,
            "influence": influence,
            "interest": interest,
            "engagement_strategy": engagement_strategy,
            "recommended_frequency": engagement_strategy.get("frequency"),
        }

    async def _create_communication_plan(self, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Create communication plan."""
        self.logger.info(f"Creating communication plan: {plan_data.get('name')}")

        # Generate plan ID
        plan_id = await self._generate_plan_id()

        # Validate schedule and stakeholders
        stakeholder_ids = plan_data.get("stakeholder_ids", [])
        valid_stakeholders = [s_id for s_id in stakeholder_ids if s_id in self.stakeholder_register]

        # Create communication plan
        plan = {
            "plan_id": plan_id,
            "project_id": plan_data.get("project_id"),
            "name": plan_data.get("name"),
            "objectives": plan_data.get("objectives", []),
            "stakeholder_ids": valid_stakeholders,
            "channel": plan_data.get("channel", "email"),
            "frequency": plan_data.get("frequency", "weekly"),
            "schedule": plan_data.get("schedule", []),
            "template_id": plan_data.get("template_id"),
            "status": "Active",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store plan
        self.communication_plans[plan_id] = plan


        return {
            "plan_id": plan_id,
            "name": plan["name"],
            "stakeholders": len(valid_stakeholders),
            "channel": plan["channel"],
            "frequency": plan["frequency"],
        }

    async def _generate_message(self, message_data: dict[str, Any]) -> dict[str, Any]:
        """Generate personalized message."""
        self.logger.info(f"Generating message: {message_data.get('subject')}")

        # Generate message ID
        message_id = await self._generate_message_id()

        # Get stakeholder for personalization
        stakeholder_ids = message_data.get("stakeholder_ids", [])

        template_id = message_data.get("template_id")
        locale = message_data.get("locale") or self.default_locale
        template_payload = self._get_template(template_id, locale) if template_id else {}
        template_body = message_data.get("template", template_payload.get("body", ""))
        template_subject = message_data.get("subject", template_payload.get("subject"))

        summary = None
        if message_data.get("report") or message_data.get("summary_source"):
            summary = await self._summarize_report(
                message_data.get("report") or message_data.get("summary_source", ""),
                message_data.get("summary_role", "general"),
                locale,
            )

        message_payload = dict(message_data.get("data", {}))
        if summary:
            message_payload["summary"] = summary.get("summary")

        # Generate content using NLG or templates
        content, generation_metadata = await self._generate_message_content(
            template_body,
            message_payload,
            message_data.get("prompt_type"),
            message_data.get("prompt"),
        )
        subject = template_subject or message_data.get("subject", "")
        if subject:
            subject = self._safe_format_template(subject, message_payload)

        # Personalize for each stakeholder
        personalized_messages = []
        for stakeholder_id in stakeholder_ids:
            stakeholder = self.stakeholder_register.get(stakeholder_id)
            if stakeholder:
                personalized_content = await self._personalize_content(content, stakeholder)
                if subject:
                    personalized_subject = await self._personalize_content(subject, stakeholder)
                else:
                    personalized_subject = ""
                delivery_time = await self._calculate_optimal_send_time(
                    stakeholder,
                    message_data.get("scheduled_send"),
                )
                personalized_messages.append(
                    {
                        "stakeholder_id": stakeholder_id,
                        "content": personalized_content,
                        "subject": personalized_subject,
                        "scheduled_time": delivery_time,
                    }
                )

        # Create message
        message = {
            "message_id": message_id,
            "project_id": message_data.get("project_id"),
            "subject": subject or message_data.get("subject"),
            "content": content,
            "generation_metadata": generation_metadata,
            "personalized_messages": personalized_messages,
            "channel": message_data.get("channel", "email"),
            "scheduled_send": message_data.get("scheduled_send"),
            "delivery_mode": message_data.get("delivery_mode", "immediate"),
            "attachments": message_data.get("attachments", []),
            "status": "Draft",
            "review_required": generation_metadata.get("provider") == "azure_openai",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store message
        self.messages[message_id] = message


        return {
            "message_id": message_id,
            "subject": message["subject"],
            "recipients": len(personalized_messages),
            "channel": message["channel"],
            "status": "Draft",
            "preview": content[:200],
        }

    async def _schedule_message(self, tenant_id: str, message_id: str) -> dict[str, Any]:
        """Schedule message delivery in batches."""
        message = self.messages.get(message_id)
        if not message:
            raise ValueError(f"Message not found: {message_id}")
        batch_schedule = self._build_delivery_schedule(
            message.get("personalized_messages", []),
            message.get("scheduled_send"),
        )
        message["delivery_batches"] = batch_schedule
        message["status"] = "Scheduled"
        message["scheduled_at"] = datetime.utcnow().isoformat()
        return {
            "message_id": message_id,
            "status": "Scheduled",
            "batch_count": len(batch_schedule),
            "schedule": batch_schedule,
        }

    async def _edit_message(self, message_id: str | None, message_data: dict[str, Any]) -> dict[str, Any]:
        """Edit a draft message before sending."""
        if not message_id or message_id not in self.messages:
            raise ValueError("Message not found for editing")
        message = self.messages[message_id]
        if "subject" in message_data:
            message["subject"] = message_data.get("subject")
        if "content" in message_data:
            message["content"] = message_data.get("content")
        if "template" in message_data or "data" in message_data:
            content, generation_metadata = await self._generate_message_content(
                message_data.get("template", message.get("content", "")),
                message_data.get("data", {}),
                message_data.get("prompt_type"),
                message_data.get("prompt"),
            )
            message["content"] = content
            message["generation_metadata"] = generation_metadata
        personalized_messages = []
        for personalized in message.get("personalized_messages", []):
            stakeholder_id = personalized.get("stakeholder_id")
            stakeholder = self.stakeholder_register.get(stakeholder_id)
            if stakeholder:
                personalized_content = await self._personalize_content(message["content"], stakeholder)
                personalized_messages.append(
                    {"stakeholder_id": stakeholder_id, "content": personalized_content}
                )
        message["personalized_messages"] = personalized_messages
        message["status"] = "Draft"
        return {
            "message_id": message_id,
            "status": "Draft",
            "subject": message.get("subject"),
            "preview": message.get("content", "")[:200],
        }

    async def _send_message(self, tenant_id: str, message_id: str) -> dict[str, Any]:
        """Send message to stakeholders."""
        self.logger.info(f"Sending message: {message_id}")

        message = self.messages.get(message_id)
        if not message:
            raise ValueError(f"Message not found: {message_id}")
        if message.get("delivery_mode") == "scheduled":
            scheduled = await self._schedule_message(tenant_id, message_id)
            return {
                "message_id": message_id,
                "status": "Scheduled",
                "batch_count": scheduled.get("batch_count"),
            }
        if message.get("delivery_mode") == "digest":
            queued = await self._queue_digest_notifications(tenant_id, message)
            return {
                "message_id": message_id,
                "status": "Queued",
                "queued_notifications": queued,
            }

        # Send via appropriate channel
        channel = message.get("channel", "email")
        delivery_results = []

        for personalized in message.get("personalized_messages", []):
            stakeholder_id = personalized.get("stakeholder_id")
            stakeholder = self._load_stakeholder(tenant_id, stakeholder_id)

            if not stakeholder:
                continue
            delivery_channels = self._resolve_delivery_channels(message, stakeholder)
            for delivery_channel in delivery_channels:
                if not await self._has_consent(stakeholder, delivery_channel):
                    delivery_results.append(
                        {
                            "stakeholder_id": stakeholder_id,
                            "channel": delivery_channel,
                            "status": "skipped_no_consent",
                            "sent_at": None,
                        }
                    )
                    continue

                result = await self._send_via_channel(
                    delivery_channel,
                    stakeholder,
                    message,
                    personalized.get("content"),
                    personalized.get("subject"),
                )

                delivery_results.append(
                    {
                        "stakeholder_id": stakeholder_id,
                        "channel": delivery_channel,
                        "status": result.get("status"),
                        "sent_at": result.get("sent_at"),
                    }
                )

                if stakeholder_id in self.engagement_metrics:
                    self.engagement_metrics[stakeholder_id]["messages_sent"] += 1

        # Update message status
        message["status"] = "Sent"
        message["sent_at"] = datetime.utcnow().isoformat()
        message["delivery_results"] = delivery_results

        self._record_communication_history(
            {
                "stakeholder_id": None,
                "channel": channel,
                "subject": message.get("subject"),
                "status": "sent",
                "content": message.get("content"),
                "metadata": {
                    "message_id": message_id,
                    "delivery_results": delivery_results,
                },
            }
        )
        self._publish_metrics_event(
            tenant_id=tenant_id,
            event_type="message_sent",
            payload={
                "message_id": message_id,
                "channel": channel,
                "delivery_results": delivery_results,
            },
        )
        self._publish_event(
            "stakeholder.message.sent",
            {"message_id": message_id, "delivery_results": delivery_results},
        )
        self._trigger_workflow(
            "stakeholder.message.sent",
            {"message_id": message_id, "delivery_results": delivery_results},
        )

        return {
            "message_id": message_id,
            "status": "Sent",
            "recipients": len(delivery_results),
            "successful_deliveries": len(
                [r for r in delivery_results if r["status"] == "delivered"]
            ),
            "sent_at": message["sent_at"],
        }

    async def _update_communication_preferences(
        self,
        tenant_id: str,
        stakeholder_id: str | None,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        if not stakeholder_id:
            raise ValueError("stakeholder_id is required")
        stakeholder = self._load_stakeholder(tenant_id, stakeholder_id)
        if not stakeholder:
            raise ValueError(f"Stakeholder not found: {stakeholder_id}")
        stakeholder["communication_preferences"] = preferences
        if preferences.get("preferred_channels"):
            stakeholder["preferred_channels"] = preferences["preferred_channels"]
        if "opt_out" in preferences:
            stakeholder["opt_out"] = bool(preferences["opt_out"])
        self.stakeholder_store.upsert(tenant_id, stakeholder_id, stakeholder.copy())
        return {
            "stakeholder_id": stakeholder_id,
            "preferences": stakeholder.get("communication_preferences", {}),
            "preferred_channels": stakeholder.get("preferred_channels", []),
        }

    async def _track_delivery_event(
        self,
        tenant_id: str,
        message_id: str | None,
        stakeholder_id: str | None,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        if not message_id or message_id not in self.messages:
            raise ValueError("message_id not found")
        if not stakeholder_id:
            raise ValueError("stakeholder_id is required")
        event_type = event.get("type", "delivered")
        message = self.messages[message_id]
        if stakeholder_id in self.engagement_metrics:
            metrics = self.engagement_metrics[stakeholder_id]
            if event_type == "opened":
                metrics["messages_opened"] += 1
            elif event_type == "clicked":
                metrics["messages_clicked"] += 1
            elif event_type == "responded":
                metrics["responses_received"] += 1
        self._record_communication_history(
            {
                "stakeholder_id": stakeholder_id,
                "channel": message.get("channel"),
                "subject": message.get("subject"),
                "status": event_type,
                "content": event.get("details"),
                "metadata": {"message_id": message_id, "event": event},
            }
        )
        self._publish_event(
            f"stakeholder.message.{event_type}",
            {"message_id": message_id, "stakeholder_id": stakeholder_id, "event": event},
        )
        self._publish_metrics_event(
            tenant_id=tenant_id,
            event_type="message_engagement",
            payload={
                "message_id": message_id,
                "stakeholder_id": stakeholder_id,
                "event_type": event_type,
                "event": event,
            },
        )
        return {"message_id": message_id, "stakeholder_id": stakeholder_id, "event": event_type}

    async def _collect_feedback(self, feedback_data: dict[str, Any]) -> dict[str, Any]:
        """Collect stakeholder feedback."""
        self.logger.info(f"Collecting feedback from: {feedback_data.get('stakeholder_id')}")

        # Generate feedback ID
        feedback_id = await self._generate_feedback_id()

        # Perform sentiment analysis
        sentiment = await self._analyze_text_sentiment(feedback_data.get("comments", ""))

        # Create feedback record
        feedback_record = {
            "feedback_id": feedback_id,
            "stakeholder_id": feedback_data.get("stakeholder_id"),
            "project_id": feedback_data.get("project_id"),
            "message_id": feedback_data.get("message_id"),
            "survey_response": feedback_data.get("survey_response", {}),
            "comments": feedback_data.get("comments"),
            "rating": feedback_data.get("rating"),
            "sentiment": sentiment,
            "received_at": datetime.utcnow().isoformat(),
        }

        # Store feedback
        if feedback_data.get("stakeholder_id") not in self.feedback:
            self.feedback[feedback_data.get("stakeholder_id")] = []  # type: ignore

        self.feedback[feedback_data.get("stakeholder_id")].append(feedback_record)  # type: ignore

        # Update stakeholder sentiment score
        stakeholder = self.stakeholder_register.get(feedback_data.get("stakeholder_id"))  # type: ignore
        if stakeholder:
            stakeholder["sentiment_score"] = sentiment.get("score", 0)
            stakeholder["last_feedback_date"] = datetime.utcnow().isoformat()
            self.stakeholder_store.upsert(
                feedback_data.get("tenant_id", "default"),
                stakeholder.get("stakeholder_id"),
                stakeholder.copy(),
            )

        # Update engagement metrics
        stakeholder_id = feedback_data.get("stakeholder_id")
        if stakeholder_id in self.engagement_metrics:
            self.engagement_metrics[stakeholder_id]["responses_received"] += 1

        self._record_communication_history(
            {
                "stakeholder_id": feedback_data.get("stakeholder_id"),
                "channel": "feedback",
                "subject": "Stakeholder feedback",
                "status": "received",
                "content": feedback_data.get("comments"),
                "metadata": {"feedback_id": feedback_id, "sentiment": sentiment},
            }
        )
        self._publish_event(
            "stakeholder.feedback.received",
            {
                "feedback_id": feedback_id,
                "stakeholder_id": feedback_data.get("stakeholder_id"),
                "sentiment": sentiment,
            },
        )

        if sentiment.get("score", 0) < self.sentiment_threshold:
            await self._trigger_sentiment_alert(
                feedback_data.get("stakeholder_id"), sentiment, feedback_record
            )

        return {
            "feedback_id": feedback_id,
            "stakeholder_id": feedback_record["stakeholder_id"],
            "sentiment": sentiment,
            "alert_triggered": sentiment.get("score", 0) < self.sentiment_threshold,
        }

    async def _analyze_sentiment(self, stakeholder_id: str | None) -> dict[str, Any]:
        """Analyze stakeholder sentiment trends."""
        self.logger.info(f"Analyzing sentiment for stakeholder: {stakeholder_id}")

        if stakeholder_id:
            # Analyze single stakeholder
            stakeholder_feedback = self.feedback.get(stakeholder_id, [])
            sentiment_trend = await self._calculate_sentiment_trend(stakeholder_feedback)

            return {
                "stakeholder_id": stakeholder_id,
                "current_sentiment": sentiment_trend.get("current"),
                "trend": sentiment_trend.get("trend"),
                "feedback_count": len(stakeholder_feedback),
            }
        else:
            # Analyze all stakeholders
            overall_sentiment = await self._calculate_overall_sentiment()
            return {
                "overall_sentiment": overall_sentiment,
                "stakeholders_analyzed": len(self.feedback),
            }

    async def _schedule_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Schedule event or meeting."""
        self.logger.info(f"Scheduling event: {event_data.get('title')}")

        # Generate event ID
        event_id = await self._generate_event_id()

        meeting_suggestions = await self._suggest_meeting_times(
            event_data.get("stakeholder_ids", []),
            event_data.get("duration", 60),
            event_data.get("time_window"),
        )
        optimal_time = meeting_suggestions[0] if meeting_suggestions else await self._propose_optimal_time(
            event_data.get("stakeholder_ids", []), event_data.get("duration", 60)
        )

        agenda = event_data.get("agenda", [])
        if not agenda and event_data.get("generate_agenda", True):
            agenda = await self._generate_meeting_agenda(event_data)

        # Create event
        event = {
            "event_id": event_id,
            "project_id": event_data.get("project_id"),
            "title": event_data.get("title"),
            "description": event_data.get("description"),
            "scheduled_time": event_data.get("scheduled_time", optimal_time),
            "duration_minutes": event_data.get("duration", 60),
            "stakeholder_ids": event_data.get("stakeholder_ids", []),
            "agenda": agenda,
            "location": event_data.get("location", "virtual"),
            "meeting_link": event_data.get("meeting_link"),
            "rsvp_status": {},
            "status": "Scheduled",
            "created_at": datetime.utcnow().isoformat(),
        }

        graph_event = None
        if event_data.get("use_graph", True):
            graph_event = await self._create_graph_event(event, event_data.get("attachments", []))
            if graph_event.get("online_meeting_url"):
                event["meeting_link"] = graph_event.get("online_meeting_url")
            if graph_event.get("scheduled_time"):
                event["scheduled_time"] = graph_event.get("scheduled_time")
            event["graph_event_id"] = graph_event.get("event_id")

        # Store event
        self.events[event_id] = event

        self._record_communication_history(
            {
                "stakeholder_id": None,
                "channel": "calendar",
                "subject": event.get("title"),
                "status": "scheduled",
                "content": event.get("description"),
                "metadata": {
                    "event_id": event_id,
                    "meeting_link": event.get("meeting_link"),
                    "graph_event": graph_event,
                },
            }
        )
        self._publish_event(
            "stakeholder.meeting.scheduled",
            {
                "event_id": event_id,
                "scheduled_time": event.get("scheduled_time"),
                "meeting_link": event.get("meeting_link"),
            },
        )
        self._trigger_workflow(
            "stakeholder.meeting.scheduled",
            {
                "event_id": event_id,
                "scheduled_time": event.get("scheduled_time"),
                "meeting_link": event.get("meeting_link"),
            },
        )

        return {
            "event_id": event_id,
            "title": event["title"],
            "scheduled_time": event["scheduled_time"],
            "invitees": len(event["stakeholder_ids"]),
            "optimal_time_suggested": optimal_time,
            "meeting_suggestions": meeting_suggestions,
        }

    async def _track_engagement(self, stakeholder_id: str | None) -> dict[str, Any]:
        """Track stakeholder engagement metrics."""
        self.logger.info(f"Tracking engagement for stakeholder: {stakeholder_id}")

        if stakeholder_id:
            # Track single stakeholder
            stakeholder = self.stakeholder_register.get(stakeholder_id)
            if not stakeholder:
                raise ValueError(f"Stakeholder not found: {stakeholder_id}")

            metrics = self.engagement_metrics.get(stakeholder_id, {})

            # Calculate engagement score
            engagement_score = await self._calculate_engagement_score(metrics)

            # Update stakeholder
            stakeholder["engagement_score"] = engagement_score

            return {
                "stakeholder_id": stakeholder_id,
                "engagement_score": engagement_score,
                "metrics": metrics,
                "engagement_level": await self._classify_engagement_level(engagement_score),
                "outreach_priority": await self._prioritize_outreach(engagement_score),
            }
        else:
            # Track all stakeholders
            overall_engagement = await self._calculate_overall_engagement()
            return {
                "overall_engagement": overall_engagement,
                "stakeholders_tracked": len(self.engagement_metrics),
            }

    async def _get_stakeholder_dashboard(
        self, project_id: str | None, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Get stakeholder dashboard data."""
        self.logger.info(f"Getting stakeholder dashboard for project: {project_id}")

        # Get stakeholder summary
        stakeholder_summary = await self._get_stakeholder_summary(project_id)

        # Get engagement metrics
        engagement_overview = await self._get_engagement_overview(project_id)

        # Get sentiment trends
        sentiment_trends = await self._get_sentiment_trends(project_id)

        # Get upcoming communications
        upcoming_communications = await self._get_upcoming_communications(project_id)

        return {
            "project_id": project_id,
            "stakeholder_summary": stakeholder_summary,
            "engagement_overview": engagement_overview,
            "sentiment_trends": sentiment_trends,
            "upcoming_communications": upcoming_communications,
            "dashboard_generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_communication_report(
        self, report_type: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate communication report."""
        self.logger.info(f"Generating {report_type} communication report")

        if report_type == "summary":
            return await self._generate_summary_report(filters)
        elif report_type == "engagement":
            return await self._generate_engagement_report(filters)
        elif report_type == "sentiment":
            return await self._generate_sentiment_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    # Helper methods

    def _resolve_token(
        self, env_name: str, secret_name_env: str, config: dict[str, Any] | None
    ) -> str | None:
        configured = resolve_secret((config or {}).get(env_name.lower()))
        direct = resolve_secret(os.getenv(env_name))
        if configured:
            return configured
        if direct:
            return direct
        secret_name = resolve_secret(os.getenv(secret_name_env))
        return fetch_keyvault_secret(self.keyvault_url, secret_name)

    def _record_communication_history(self, record: dict[str, Any]) -> None:
        record["record_id"] = record.get("record_id") or f"COM-{datetime.utcnow().isoformat()}"
        record["created_at"] = record.get("created_at") or datetime.utcnow().isoformat()
        self.history_store.add_record(record)

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.service_bus_publisher.publish(event_type, payload)

    def _trigger_workflow(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.logic_apps_trigger_url:
            return
        requests.post(
            self.logic_apps_trigger_url,
            json={"event_type": event_type, "payload": payload},
            timeout=10,
        )

    async def _graph_request(
        self, token: str | None, method: str, endpoint: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not token:
            return {"status": "skipped", "reason": "missing_token"}
        url = f"{self.graph_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            return {"status": "error", "code": response.status_code, "details": response.text}
        if response.text:
            try:
                return response.json()
            except ValueError:
                return {"status": "ok", "raw": response.text}
        return {"status": "ok"}

    def _build_text_analytics_client(self) -> TextAnalyticsClient | None:
        if not self.text_analytics_endpoint or not self.text_analytics_key:
            return None
        if not TextAnalyticsClient or not AzureKeyCredential:
            return None
        return TextAnalyticsClient(
            endpoint=self.text_analytics_endpoint,
            credential=AzureKeyCredential(self.text_analytics_key),
        )

    async def _generate_stakeholder_id(self) -> str:
        """Generate unique stakeholder ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"STK-{timestamp}"

    async def _generate_plan_id(self) -> str:
        """Generate unique plan ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PLAN-{timestamp}"

    async def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"MSG-{timestamp}"

    async def _generate_feedback_id(self) -> str:
        """Generate unique feedback ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"FB-{timestamp}"

    async def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"EVT-{timestamp}"

    async def _enrich_stakeholder_profile(self, stakeholder_data: dict[str, Any]) -> dict[str, Any]:
        """Enrich stakeholder profile from CRM."""
        crm_profile = await self._sync_with_crm(stakeholder_data)
        if crm_profile:
            stakeholder_data["crm_profile"] = crm_profile
            stakeholder_data["crm_synced_at"] = datetime.utcnow().isoformat()
        return stakeholder_data

    async def _suggest_classification(self, stakeholder_data: dict[str, Any]) -> dict[str, Any]:
        """Suggest stakeholder classification."""
        role = stakeholder_data.get("role", "").lower()

        if "executive" in role or "director" in role:
            return {"influence": "high", "interest": "high", "engagement_level": "high"}
        elif "manager" in role:
            return {"influence": "medium", "interest": "high", "engagement_level": "medium"}
        else:
            return {"influence": "low", "interest": "medium", "engagement_level": "low"}

    async def _sync_with_crm(self, stakeholder_data: dict[str, Any]) -> dict[str, Any]:
        """Synchronize stakeholder profile with CRM connectors (e.g., Salesforce)."""
        if not SalesforceConfig or not _build_token_manager or not _build_client:
            return await self._sync_with_crm_rest(stakeholder_data)
        email = stakeholder_data.get("email")
        if not email:
            return {}
        try:
            token_url = os.getenv("SALESFORCE_TOKEN_URL") or ""
            rate_limit = int(os.getenv("SALESFORCE_RATE_LIMIT_PER_MINUTE", "300"))
            config = SalesforceConfig.from_env(token_url, rate_limit)
            token_manager = _build_token_manager(config)
            client = _build_client(config, token_manager)
            query = (
                os.getenv("SALESFORCE_CONTACT_QUERY")
                or "SELECT Id, Name, Title, Account.Name, Email FROM Contact WHERE Email='{email}'"
            )
            endpoint = (
                os.getenv("SALESFORCE_CONTACT_ENDPOINT")
                or f"/services/data/v57.0/query/?q={query.format(email=email)}"
            )
            response = _request_with_refresh(client, token_manager, "GET", endpoint)
            payload = response.json() if hasattr(response, "json") else {}
            records = payload.get("records", []) if isinstance(payload, dict) else []
            if not records:
                return {}
            record = records[0]
            return {
                "crm_source": "salesforce",
                "crm_id": record.get("Id"),
                "name": record.get("Name"),
                "title": record.get("Title"),
                "account": (record.get("Account") or {}).get("Name")
                if isinstance(record.get("Account"), dict)
                else record.get("Account.Name"),
                "email": record.get("Email"),
            }
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # noqa: BLE001
            self.logger.warning("CRM sync failed: %s", exc)
            return await self._sync_with_crm_rest(stakeholder_data)

    async def _sync_with_crm_rest(self, stakeholder_data: dict[str, Any]) -> dict[str, Any]:
        if not (self.crm_base_url and self.crm_api_key):
            return {}
        email = stakeholder_data.get("email")
        if not email:
            return {}
        url = f"{self.crm_base_url.rstrip('/')}/{self.crm_profile_endpoint.lstrip('/')}"
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.crm_api_key}"},
                params={"email": email},
                timeout=self.crm_timeout_seconds,
            )
            if response.status_code >= 400:
                return {}
            payload = response.json()
            if not payload:
                return {}
            return {
                "crm_source": payload.get("source", "rest"),
                "crm_id": payload.get("id") or payload.get("crm_id"),
                "name": payload.get("name"),
                "title": payload.get("title"),
                "account": payload.get("account"),
                "email": payload.get("email") or email,
                "raw": payload,
            }
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # noqa: BLE001
            self.logger.warning("CRM REST sync failed: %s", exc)
            return {}

    async def _upsert_crm_profile(self, stakeholder: dict[str, Any]) -> dict[str, Any] | None:
        if not (self.crm_base_url and self.crm_api_key):
            return None
        url = f"{self.crm_base_url.rstrip('/')}/{self.crm_upsert_endpoint.lstrip('/')}"
        payload = {
            "stakeholder_id": stakeholder.get("stakeholder_id"),
            "name": stakeholder.get("name"),
            "email": stakeholder.get("email"),
            "role": stakeholder.get("role"),
            "organization": stakeholder.get("organization"),
            "influence": stakeholder.get("influence"),
            "interest": stakeholder.get("interest"),
            "engagement_level": stakeholder.get("engagement_level"),
            "engagement_score": stakeholder.get("engagement_score"),
            "sentiment_score": stakeholder.get("sentiment_score"),
        }
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.crm_api_key}"},
                json=payload,
                timeout=self.crm_timeout_seconds,
            )
            if response.status_code >= 400:
                return {"status": "error", "code": response.status_code}
            return {"status": "ok"}
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # noqa: BLE001
            self.logger.warning("CRM upsert failed: %s", exc)
            return {"status": "error", "reason": str(exc)}

    async def _determine_engagement_strategy(self, influence: str, interest: str) -> dict[str, Any]:
        """Determine engagement strategy based on power-interest matrix."""
        # High influence, high interest: Manage closely
        if influence == "high" and interest == "high":
            return {
                "strategy": "manage_closely",
                "frequency": "weekly",
                "channels": ["email", "teams", "meetings"],
            }
        # High influence, low interest: Keep satisfied
        elif influence == "high" and interest == "low":
            return {
                "strategy": "keep_satisfied",
                "frequency": "bi-weekly",
                "channels": ["email", "meetings"],
            }
        # Low influence, high interest: Keep informed
        elif influence == "low" and interest == "high":
            return {
                "strategy": "keep_informed",
                "frequency": "weekly",
                "channels": ["email", "portal"],
            }
        # Low influence, low interest: Monitor
        else:
            return {"strategy": "monitor", "frequency": "monthly", "channels": ["email"]}

    async def _generate_message_content(
        self,
        template: str,
        data: dict[str, Any],
        prompt_type: str | None = None,
        prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate message content using NLG."""
        if self.openai_endpoint and self.openai_api_key and self.openai_deployment:
            draft = await self._generate_openai_text(
                template=template, data=data, prompt_type=prompt_type, prompt=prompt
            )
            if not draft.get("content") and template:
                return self._safe_format_template(template, data), {"provider": "template_fallback"}
            return draft.get("content", ""), draft
        if template:
            return self._safe_format_template(template, data), {"provider": "template"}
        return "Sample message content", {"provider": "fallback"}

    async def _has_consent(self, stakeholder: dict[str, Any], channel: str) -> bool:
        """Check consent and opt-out flags for stakeholder."""
        if stakeholder.get("opt_out"):
            return False
        if not stakeholder.get("consent", True):
            return False
        preferences = stakeholder.get("communication_preferences", {})
        if channel in preferences.get("opt_out_channels", []):
            return False
        return True

    def _resolve_delivery_channels(
        self, message: dict[str, Any], stakeholder: dict[str, Any]
    ) -> list[str]:
        channel_config = message.get("channels") or message.get("channel", "email")
        preferences = stakeholder.get("communication_preferences", {})
        preferred = (
            preferences.get("preferred_channels")
            or stakeholder.get("preferred_channels")
            or ["email"]
        )
        fallback = preferences.get("fallback_channels", [])
        if isinstance(channel_config, list):
            channels = channel_config
        elif channel_config in {"auto", "preferred"}:
            channels = preferred
        else:
            channels = [channel_config]
        for fallback_channel in fallback:
            if fallback_channel not in channels:
                channels.append(fallback_channel)
        return [channel for channel in channels if channel]

    async def _queue_digest_notifications(
        self, tenant_id: str, message: dict[str, Any]
    ) -> list[dict[str, Any]]:
        queued_entries: list[dict[str, Any]] = []
        now = datetime.utcnow()
        for personalized in message.get("personalized_messages", []):
            stakeholder_id = personalized.get("stakeholder_id")
            if not stakeholder_id:
                continue
            scheduled_time = personalized.get("scheduled_time")
            if scheduled_time:
                send_after = scheduled_time
            else:
                send_after = (now + timedelta(minutes=self.digest_window_minutes)).isoformat()
            key = (tenant_id, stakeholder_id)
            entry = {
                "message_id": message.get("message_id"),
                "subject": personalized.get("subject") or message.get("subject"),
                "content": personalized.get("content"),
                "queued_at": now.isoformat(),
                "send_after": send_after,
                "project_id": message.get("project_id"),
            }
            self.digest_queue.setdefault(key, []).append(entry)
            queued_entries.append({"stakeholder_id": stakeholder_id, "send_after": send_after})
            if len(self.digest_queue.get(key, [])) >= self.digest_batch_size:
                await self._flush_digest_notifications(tenant_id, stakeholder_id)
        return queued_entries

    async def _flush_digest_notifications(
        self, tenant_id: str, stakeholder_id: str | None
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        flushed: list[dict[str, Any]] = []
        for (queued_tenant, queued_stakeholder), items in list(self.digest_queue.items()):
            if queued_tenant != tenant_id:
                continue
            if stakeholder_id and queued_stakeholder != stakeholder_id:
                continue
            due_items = []
            for item in items:
                try:
                    send_after = datetime.fromisoformat(item["send_after"])
                except (TypeError, ValueError):
                    send_after = now
                if send_after <= now:
                    due_items.append(item)
            if not due_items:
                continue
            stakeholder = self._load_stakeholder(tenant_id, queued_stakeholder)
            if not stakeholder:
                continue
            digest_payload = await self._build_digest_payload(stakeholder, due_items)
            digest_message = {
                "subject": digest_payload["subject"],
                "content": digest_payload["body"],
                "channel": "preferred",
                "attachments": [],
            }
            delivery_channels = self._resolve_delivery_channels(digest_message, stakeholder)
            results = []
            for channel in delivery_channels:
                if not await self._has_consent(stakeholder, channel):
                    results.append({"channel": channel, "status": "skipped_no_consent"})
                    continue
                result = await self._send_via_channel(
                    channel,
                    stakeholder,
                    digest_message,
                    digest_payload["body"],
                    digest_payload["subject"],
                )
                results.append({"channel": channel, "status": result.get("status")})
                if queued_stakeholder in self.engagement_metrics:
                    self.engagement_metrics[queued_stakeholder]["messages_sent"] += 1
            self.digest_queue[(queued_tenant, queued_stakeholder)] = [
                item for item in items if item not in due_items
            ]
            self._record_communication_history(
                {
                    "stakeholder_id": queued_stakeholder,
                    "channel": ",".join(delivery_channels),
                    "subject": digest_payload["subject"],
                    "status": "sent",
                    "content": digest_payload["body"],
                    "metadata": {"digest_items": len(due_items), "results": results},
                }
            )
            flushed.append(
                {
                    "stakeholder_id": queued_stakeholder,
                    "digest_items": len(due_items),
                    "channels": delivery_channels,
                }
            )
        return {"status": "flushed", "digests": flushed}

    def _load_stakeholder(self, tenant_id: str, stakeholder_id: str) -> dict[str, Any] | None:
        stakeholder = self.stakeholder_register.get(stakeholder_id)
        if stakeholder:
            return stakeholder
        stored = self.stakeholder_store.get(tenant_id, stakeholder_id)
        if stored:
            self.stakeholder_register[stakeholder_id] = stored
        return stored

    async def _personalize_content(self, content: str, stakeholder: dict[str, Any]) -> str:
        """Personalize content for stakeholder."""
        # Replace baselines with stakeholder data
        personalized = content.replace("{name}", stakeholder.get("name", ""))
        personalized = personalized.replace("{role}", stakeholder.get("role", ""))
        return personalized

    async def _build_digest_payload(
        self, stakeholder: dict[str, Any], items: list[dict[str, Any]]
    ) -> dict[str, str]:
        digest_items = "\n".join(
            f"- {item.get('subject') or 'Update'}"
            for item in items
            if item.get("subject") or item.get("content")
        )
        summary_source = "\n\n".join(item.get("content", "") for item in items)
        summary = await self._summarize_report(
            summary_source,
            stakeholder.get("role", "general"),
            stakeholder.get("locale") or self.default_locale,
        )
        template = self._get_template("digest_update", stakeholder.get("locale") or self.default_locale)
        subject = template.get("subject", "Update digest")
        body_template = template.get("body", "{digest_items}")
        payload = {
            "name": stakeholder.get("name", ""),
            "project_name": stakeholder.get("project_name", "your project"),
            "digest_items": digest_items,
            "summary": summary.get("summary", ""),
        }
        return {
            "subject": self._safe_format_template(subject, payload),
            "body": self._safe_format_template(body_template, payload),
        }

    async def _calculate_optimal_send_time(
        self, stakeholder: dict[str, Any], scheduled_send: str | None
    ) -> str | None:
        if scheduled_send:
            return scheduled_send
        preferences = stakeholder.get("communication_preferences", {})
        preferred_hour = preferences.get("preferred_send_hour")
        utc_offset = int(preferences.get("utc_offset_minutes") or 0)
        if preferred_hour is None:
            return None
        now_utc = datetime.utcnow()
        local_time = now_utc + timedelta(minutes=utc_offset)
        candidate = local_time.replace(
            hour=int(preferred_hour), minute=0, second=0, microsecond=0
        )
        if candidate <= local_time:
            candidate = candidate + timedelta(days=1)
        send_time = candidate - timedelta(minutes=utc_offset)
        return send_time.isoformat()

    def _publish_metrics_event(
        self, *, tenant_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        enriched = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "recorded_at": datetime.utcnow().isoformat(),
            **payload,
        }
        self._publish_event("stakeholder.communication.metrics", enriched)

    async def _send_via_channel(
        self,
        channel: str,
        stakeholder: dict[str, Any],
        message: dict[str, Any],
        content: str,
        subject_override: str | None = None,
    ) -> dict[str, Any]:
        """Send message via communication channel."""
        subject = subject_override or message.get("subject", "")
        attachments = message.get("attachments", [])
        if channel == "email":
            return await self._send_email(
                stakeholder.get("email"),
                subject,
                content,
                attachments,
                use_graph=message.get("use_graph", True),
            )
        if channel == "teams":
            return await self._send_teams_message(
                stakeholder.get("teams_id") or stakeholder.get("email"),
                content,
            )
        if channel == "slack":
            return await self._send_slack_message(
                stakeholder.get("slack_channel") or stakeholder.get("slack_id"),
                content,
            )
        if channel == "sms":
            return await self._send_sms(stakeholder.get("phone"), content)
        if channel in {"push", "portal"}:
            return await self._send_push(stakeholder, subject, content)
        return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}

    async def _analyze_text_sentiment(self, text: str) -> dict[str, Any]:
        """Analyze sentiment of text."""
        client = self._build_text_analytics_client()
        if client:
            response = client.analyze_sentiment([text])[0]
            score = response.confidence_scores.positive - response.confidence_scores.negative
            return {
                "score": score,
                "label": response.sentiment,
                "confidence": max(
                    response.confidence_scores.positive,
                    response.confidence_scores.neutral,
                    response.confidence_scores.negative,
                ),
            }
        if self.text_analytics_endpoint and self.text_analytics_key:
            payload = {"documents": [{"id": "1", "language": "en", "text": text}]}
            response = requests.post(
                f"{self.text_analytics_endpoint.rstrip('/')}/text/analytics/v3.1/sentiment",
                headers={"Ocp-Apim-Subscription-Key": self.text_analytics_key},
                json=payload,
                timeout=10,
            )
            if response.status_code < 400:
                document = response.json().get("documents", [{}])[0]
                score = document.get("confidenceScores", {}).get("positive", 0) - document.get(
                    "confidenceScores", {}
                ).get("negative", 0)
                return {
                    "score": score,
                    "label": document.get("sentiment", "neutral"),
                    "confidence": max(document.get("confidenceScores", {}).values() or [0]),
                }
        return {"score": 0.5, "label": "neutral", "confidence": 0.8}  # -1 to 1

    async def _calculate_sentiment_trend(
        self, feedback_list: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate sentiment trend."""
        if not feedback_list:
            return {"current": 0, "trend": "stable"}

        # Get recent sentiment scores
        scores = [f.get("sentiment", {}).get("score", 0) for f in feedback_list[-10:]]
        current = scores[-1] if scores else 0

        # Simple trend calculation
        if len(scores) >= 2:
            if current > scores[0]:
                trend = "improving"
            elif current < scores[0]:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {"current": current, "trend": trend}

    async def _calculate_overall_sentiment(self) -> dict[str, Any]:
        """Calculate overall sentiment across all stakeholders."""
        all_scores = []
        for stakeholder_id, feedback_list in self.feedback.items():
            for feedback in feedback_list:
                score = feedback.get("sentiment", {}).get("score", 0)
                all_scores.append(score)

        if not all_scores:
            return {"average": 0, "distribution": {}}

        average = sum(all_scores) / len(all_scores)
        positive = len([s for s in all_scores if s > 0.3])
        neutral = len([s for s in all_scores if -0.3 <= s <= 0.3])
        negative = len([s for s in all_scores if s < -0.3])

        return {
            "average": average,
            "distribution": {"positive": positive, "neutral": neutral, "negative": negative},
        }

    async def _propose_optimal_time(self, stakeholder_ids: list[str], duration: int) -> str:
        """Propose optimal meeting time considering time zones."""
        # Baseline: suggest tomorrow at 10 AM UTC
        optimal_time = datetime.utcnow() + timedelta(days=1)
        optimal_time = optimal_time.replace(hour=10, minute=0, second=0, microsecond=0)
        return optimal_time.isoformat()

    async def _suggest_meeting_times(
        self,
        stakeholder_ids: list[str],
        duration: int,
        time_window: dict[str, Any] | None,
    ) -> list[str]:
        """Suggest meeting times using Microsoft Graph meeting time suggestions."""
        attendees = []
        for stakeholder_id in stakeholder_ids:
            stakeholder = self.stakeholder_register.get(stakeholder_id) or self._load_stakeholder(
                "default", stakeholder_id
            )
            if stakeholder and stakeholder.get("email"):
                attendees.append({"emailAddress": {"address": stakeholder.get("email")}})
        if not attendees or not self.exchange_token:
            return []
        start_time = (
            (time_window or {}).get("start")
            or (datetime.utcnow() + timedelta(days=1)).replace(hour=9, minute=0).isoformat()
        )
        end_time = (
            (time_window or {}).get("end")
            or (datetime.utcnow() + timedelta(days=7)).replace(hour=17, minute=0).isoformat()
        )
        payload = {
            "attendees": attendees,
            "meetingDuration": f"PT{duration}M",
            "timeConstraint": {
                "timeslots": [
                    {
                        "start": {"dateTime": start_time, "timeZone": "UTC"},
                        "end": {"dateTime": end_time, "timeZone": "UTC"},
                    }
                ]
            },
        }
        response = await self._graph_request(
            self.exchange_token, "POST", "/me/findMeetingTimes", payload
        )
        suggestions = response.get("meetingTimeSuggestions", []) if isinstance(response, dict) else []
        return [
            suggestion.get("meetingTimeSlot", {})
            .get("start", {})
            .get("dateTime")
            for suggestion in suggestions
            if suggestion.get("meetingTimeSlot")
        ]

    async def _create_graph_event(
        self, event: dict[str, Any], attachments: list[dict[str, Any]] | list[str]
    ) -> dict[str, Any]:
        """Create a calendar event and send invites via Graph API."""
        if not self.exchange_token:
            if self.calendar_service:
                return self.calendar_service.create_event(
                    {
                        "title": event.get("title"),
                        "summary": event.get("title"),
                        "scheduled_time": event.get("scheduled_time"),
                        "description": event.get("description"),
                    }
                )
            return {"status": "skipped", "reason": "missing_exchange_token"}
        scheduled_time = event.get("scheduled_time") or datetime.utcnow().isoformat()
        try:
            start_dt = datetime.fromisoformat(scheduled_time)
        except ValueError:
            start_dt = datetime.utcnow()
            scheduled_time = start_dt.isoformat()
        attendees = []
        for stakeholder_id in event.get("stakeholder_ids", []):
            stakeholder = self.stakeholder_register.get(stakeholder_id)
            if stakeholder and stakeholder.get("email"):
                attendees.append(
                    {
                        "emailAddress": {"address": stakeholder.get("email")},
                        "type": "required",
                    }
                )
        payload = {
            "subject": event.get("title"),
            "body": {"contentType": "HTML", "content": event.get("description") or ""},
            "start": {"dateTime": scheduled_time, "timeZone": "UTC"},
            "end": {
                "dateTime": (
                    start_dt + timedelta(minutes=event.get("duration_minutes", 60))
                ).isoformat()
                if scheduled_time
                else None,
                "timeZone": "UTC",
            },
            "attendees": attendees,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }
        if attachments:
            payload["attachments"] = []
            for attachment in attachments:
                if isinstance(attachment, dict):
                    payload["attachments"].append(attachment)
                else:
                    payload["attachments"].append(
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": Path(attachment).name,
                            "contentBytes": "",
                        }
                    )
        response = await self._graph_request(self.exchange_token, "POST", "/me/events", payload)
        return {
            "status": response.get("status", "ok"),
            "event_id": response.get("id"),
            "online_meeting_url": (response.get("onlineMeeting") or {}).get("joinUrl"),
            "scheduled_time": (response.get("start") or {}).get("dateTime"),
        }

    async def _send_email(
        self,
        recipient: str | None,
        subject: str,
        content: str,
        attachments: list[str] | list[dict[str, Any]],
        *,
        use_graph: bool = True,
    ) -> dict[str, Any]:
        """Send email via Graph or fallback providers."""
        if not recipient:
            return {"status": "failed", "reason": "missing_recipient"}
        if self.notification_service and not attachments:
            result = await self.notification_service.send_email(
                recipient,
                subject,
                content,
                metadata={"provider_hint": "smtp"},
            )
            if result.get("status") != "failed":
                return {
                    "status": "delivered",
                    "sent_at": result.get("sent_at") or datetime.utcnow().isoformat(),
                    "provider": result.get("provider"),
                }
        if use_graph and self.exchange_token:
            message_payload = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": content},
                    "toRecipients": [{"emailAddress": {"address": recipient}}],
                },
                "saveToSentItems": True,
            }
            if attachments:
                message_payload["message"]["attachments"] = []
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        message_payload["message"]["attachments"].append(attachment)
                    else:
                        message_payload["message"]["attachments"].append(
                            {
                                "@odata.type": "#microsoft.graph.fileAttachment",
                                "name": Path(attachment).name,
                                "contentBytes": "",
                            }
                        )
            response = await self._graph_request(
                self.exchange_token, "POST", "/me/sendMail", message_payload
            )
            status = "delivered" if response.get("status") != "error" else "failed"
            return {"status": status, "sent_at": datetime.utcnow().isoformat()}
        if self.acs_connection_string and EmailClient:
            client = EmailClient.from_connection_string(self.acs_connection_string)
            response = client.begin_send(
                {
                    "content": {"subject": subject, "plainText": content},
                    "recipients": {"to": [{"address": recipient}]},
                    "senderAddress": self.sendgrid_from_email or "noreply@example.com",
                }
            )
            response.result()
            return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}
        if self.sendgrid_api_key:
            payload = {
                "personalizations": [{"to": [{"email": recipient}]}],
                "from": {"email": self.sendgrid_from_email or "noreply@example.com"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": content}],
            }
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {self.sendgrid_api_key}"},
                json=payload,
                timeout=10,
            )
            if response.status_code < 400:
                return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}
            return {"status": "failed", "reason": response.text}
        return {"status": "failed", "reason": "no_email_provider"}

    async def _send_teams_message(self, recipient: str | None, content: str) -> dict[str, Any]:
        if not self.teams_token:
            return {"status": "failed", "reason": "missing_teams_configuration"}
        payload = {"body": {"contentType": "HTML", "content": content}}
        endpoint = None
        if recipient and "@" in recipient:
            endpoint = f"/users/{recipient}/chats"
        elif recipient:
            endpoint = f"/chats/{recipient}/messages"
        if not endpoint:
            return {"status": "failed", "reason": "missing_recipient"}
        response = await self._graph_request(self.teams_token, "POST", endpoint, payload)
        status = "delivered" if response.get("status") != "error" else "failed"
        return {"status": status, "sent_at": datetime.utcnow().isoformat()}

    async def _send_slack_message(self, channel: str | None, content: str) -> dict[str, Any]:
        if not channel or not self.slack_client:
            return {"status": "failed", "reason": "missing_slack_configuration"}
        response = self.slack_client.chat_postMessage(channel=channel, text=content)
        return {
            "status": "delivered" if response.get("ok") else "failed",
            "sent_at": datetime.utcnow().isoformat(),
        }

    async def _send_sms(self, phone: str | None, content: str) -> dict[str, Any]:
        if not phone:
            return {"status": "failed", "reason": "missing_phone"}
        if self.notification_service:
            sms_result = await self.notification_service.send_sms(phone, content)
            if sms_result.get("status") != "failed":
                return sms_result
        if self.twilio_client and self.twilio_from_number:
            message = self.twilio_client.messages.create(
                body=content,
                from_=self.twilio_from_number,
                to=phone,
            )
            return {"status": "delivered", "sent_at": datetime.utcnow().isoformat(), "sid": message.sid}
        if self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number:
            payload = {
                "From": self.twilio_from_number,
                "To": phone,
                "Body": content,
            }
            auth = (self.twilio_account_sid, self.twilio_auth_token)
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json",
                data=payload,
                auth=auth,
                timeout=10,
            )
            if response.status_code < 400:
                return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}
            return {"status": "failed", "reason": response.text}
        return {"status": "failed", "reason": "no_sms_provider"}

    async def _send_push(
        self, stakeholder: dict[str, Any], subject: str, content: str
    ) -> dict[str, Any]:
        if self.notification_service and stakeholder.get("push_token"):
            push_result = await self.notification_service.send_push_notification(
                stakeholder.get("push_token"), content
            )
            if push_result.get("status") != "failed":
                return push_result
        if self.fcm_server_key and stakeholder.get("push_token"):
            payload = {
                "to": stakeholder.get("push_token"),
                "notification": {"title": subject, "body": content},
                "data": {"stakeholder_id": stakeholder.get("stakeholder_id")},
            }
            response = requests.post(
                "https://fcm.googleapis.com/fcm/send",
                headers={"Authorization": f"key={self.fcm_server_key}"},
                json=payload,
                timeout=10,
            )
            if response.status_code < 400:
                return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}
            return {"status": "failed", "reason": response.text}
        if self.push_endpoint:
            payload = {
                "stakeholder_id": stakeholder.get("stakeholder_id"),
                "subject": subject,
                "content": content,
                "channel": "push",
            }
            headers = {"Content-Type": "application/json"}
            if self.push_api_key:
                headers["Authorization"] = f"Bearer {self.push_api_key}"
            response = requests.post(
                self.push_endpoint, json=payload, headers=headers, timeout=10
            )
            if response.status_code < 400:
                return {"status": "delivered", "sent_at": datetime.utcnow().isoformat()}
            return {"status": "failed", "reason": response.text}
        return {"status": "failed", "reason": "no_push_provider"}

    async def _generate_openai_text(
        self,
        template: str,
        data: dict[str, Any],
        prompt_type: str | None,
        prompt: str | None,
    ) -> dict[str, Any]:
        """Generate text using Azure OpenAI."""
        formatted_template = template.format(**data) if template else ""
        base_prompt = prompt or formatted_template
        instructions = {
            "status_summary": "Summarize project status for stakeholders.",
            "meeting_agenda": "Generate a concise meeting agenda.",
            "action_items": "Generate clear action items with owners and due dates.",
            "personalized_update": "Craft a personalized stakeholder update.",
            "summary": "Summarize the report for the target stakeholder role.",
        }
        system_prompt = instructions.get(prompt_type or "", "Generate a stakeholder communication.")
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": base_prompt or json.dumps(data)},
            ],
            "temperature": 0.4,
        }
        url = (
            f"{self.openai_endpoint.rstrip('/')}/openai/deployments/"
            f"{self.openai_deployment}/chat/completions"
        )
        response = requests.post(
            url,
            headers={"api-key": self.openai_api_key},
            params={"api-version": self.openai_api_version},
            json=payload,
            timeout=20,
        )
        if response.status_code >= 400:
            return {"content": base_prompt or "", "provider": "openai_error"}
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "content": content,
            "provider": "azure_openai",
            "usage": data.get("usage"),
        }

    async def _generate_meeting_agenda(self, event_data: dict[str, Any]) -> list[str]:
        if not (self.openai_endpoint and self.openai_api_key and self.openai_deployment):
            return []
        draft = await self._generate_openai_text(
            template=event_data.get("description", ""),
            data=event_data,
            prompt_type="meeting_agenda",
            prompt=event_data.get("agenda_prompt"),
        )
        return [line.strip("- ").strip() for line in draft.get("content", "").splitlines() if line]

    async def _generate_action_items(self, context: dict[str, Any]) -> list[str]:
        if not (self.openai_endpoint and self.openai_api_key and self.openai_deployment):
            return []
        draft = await self._generate_openai_text(
            template=context.get("summary", ""),
            data=context,
            prompt_type="action_items",
            prompt=context.get("action_items_prompt"),
        )
        return [line.strip("- ").strip() for line in draft.get("content", "").splitlines() if line]

    async def _summarize_report(
        self, report: str, role: str, locale: str | None
    ) -> dict[str, Any]:
        """Summarize a report into concise content for a role."""
        if not report:
            return {"summary": "", "provider": "empty"}
        if self.openai_endpoint and self.openai_api_key and self.openai_deployment:
            prompt = (
                f"Summarize the following report for the {role} role. "
                f"Use locale {locale or self.default_locale} and keep it concise.\n\n{report}"
            )
            draft = await self._generate_openai_text(
                template=report,
                data={"report": report, "role": role, "locale": locale},
                prompt_type="summary",
                prompt=prompt,
            )
            return {"summary": draft.get("content", ""), "provider": draft.get("provider")}
        short_summary = report[:500] + ("..." if len(report) > 500 else "")
        return {"summary": short_summary, "provider": "fallback"}

    def _safe_format_template(self, template: str, data: dict[str, Any]) -> str:
        safe_data = {key: value if value is not None else "" for key, value in data.items()}
        try:
            return template.format_map(safe_data)
        except (KeyError, ValueError):
            return template

    def _get_template(self, template_id: str | None, locale: str) -> dict[str, Any]:
        if not template_id:
            return {}
        template = self.communication_templates.get(template_id, {})
        return template.get(locale) or template.get(self.default_locale, {})

    def _build_delivery_schedule(
        self, personalized_messages: list[dict[str, Any]], scheduled_start: str | None
    ) -> list[dict[str, Any]]:
        if not personalized_messages:
            return []
        if scheduled_start:
            try:
                start_time = datetime.fromisoformat(scheduled_start)
            except ValueError:
                start_time = datetime.utcnow() + timedelta(minutes=5)
        else:
            scheduled_times = [
                message.get("scheduled_time")
                for message in personalized_messages
                if message.get("scheduled_time")
            ]
            if scheduled_times:
                try:
                    earliest = min(datetime.fromisoformat(ts) for ts in scheduled_times)
                    start_time = earliest
                except ValueError:
                    start_time = datetime.utcnow() + timedelta(minutes=5)
            else:
                start_time = datetime.utcnow() + timedelta(minutes=5)
        batches = [
            personalized_messages[i : i + self.delivery_batch_size]
            for i in range(0, len(personalized_messages), self.delivery_batch_size)
        ]
        schedule = []
        for index, batch in enumerate(batches):
            scheduled_time = start_time + timedelta(minutes=index * self.delivery_batch_interval)
            schedule.append(
                {
                    "batch_id": f"{index + 1}",
                    "scheduled_time": scheduled_time.isoformat(),
                    "recipient_count": len(batch),
                }
            )
        return schedule

    def _load_default_templates(self) -> dict[str, dict[str, dict[str, str]]]:
        return {
            "project_status_update": {
                "en-US": {
                    "subject": "Project status update: {project_name}",
                    "body": (
                        "Hello {name},\n\n"
                        "Here is the latest status update for {project_name}:\n"
                        "{summary}\n\n"
                        "Key milestones:\n{milestones}\n\n"
                        "Regards,\nPMO"
                    ),
                },
                "es-ES": {
                    "subject": "Actualización de estado del proyecto: {project_name}",
                    "body": (
                        "Hola {name},\n\n"
                        "Aquí está la actualización más reciente de {project_name}:\n"
                        "{summary}\n\n"
                        "Hitos clave:\n{milestones}\n\n"
                        "Saludos,\nPMO"
                    ),
                },
            },
            "risk_alert": {
                "en-US": {
                    "subject": "Risk alert: {risk_title}",
                    "body": (
                        "Hello {name},\n\n"
                        "A new risk has been identified:\n"
                        "{risk_details}\n\n"
                        "Recommended actions:\n{mitigation_plan}\n"
                    ),
                }
            },
            "risk_alert_summary": {
                "en-US": {
                    "subject": "Risk summary for {project_name}",
                    "body": (
                        "Hello {name},\n\n"
                        "Summary of active risks for {project_name}:\n"
                        "{risk_details}\n\n"
                        "Top mitigations:\n{mitigation_plan}\n"
                    ),
                },
                "fr-FR": {
                    "subject": "Résumé des risques pour {project_name}",
                    "body": (
                        "Bonjour {name},\n\n"
                        "Résumé des risques actifs pour {project_name}:\n"
                        "{risk_details}\n\n"
                        "Principales mesures:\n{mitigation_plan}\n"
                    ),
                },
            },
            "deployment_outcome": {
                "en-US": {
                    "subject": "Deployment outcome: {release_name}",
                    "body": (
                        "Hello {name},\n\n"
                        "Deployment status: {deployment_status}\n"
                        "Summary:\n{summary}\n\n"
                        "Next steps:\n{next_steps}\n"
                    ),
                }
            },
            "digest_update": {
                "en-US": {
                    "subject": "Your update digest: {project_name}",
                    "body": (
                        "Hello {name},\n\n"
                        "Here is your digest for {project_name}:\n"
                        "{digest_items}\n\n"
                        "Summary:\n{summary}\n\n"
                        "Regards,\nPMO"
                    ),
                },
                "es-ES": {
                    "subject": "Resumen de actualizaciones: {project_name}",
                    "body": (
                        "Hola {name},\n\n"
                        "Aquí está tu resumen para {project_name}:\n"
                        "{digest_items}\n\n"
                        "Resumen:\n{summary}\n\n"
                        "Saludos,\nPMO"
                    ),
                },
            },
        }

    async def _score_engagement_with_ml(
        self, metrics: dict[str, Any], baseline_score: float
    ) -> float | None:
        if not self.azure_ml_endpoint or not self.azure_ml_key:
            return None
        response = requests.post(
            self.azure_ml_endpoint,
            headers={"Authorization": f"Bearer {self.azure_ml_key}"},
            json={"metrics": metrics, "baseline_score": baseline_score},
            timeout=10,
        )
        if response.status_code >= 400:
            return None
        payload = response.json()
        return payload.get("score")

    async def _prioritize_outreach(self, engagement_score: float) -> str:
        if engagement_score >= 70:
            return "low"
        if engagement_score >= 40:
            return "medium"
        return "high"

    async def _trigger_sentiment_alert(
        self,
        stakeholder_id: str | None,
        sentiment: dict[str, Any],
        feedback_record: dict[str, Any],
    ) -> None:
        payload = {
            "stakeholder_id": stakeholder_id,
            "sentiment": sentiment,
            "feedback": feedback_record,
        }
        self._publish_event("stakeholder.sentiment.negative", payload)
        self._trigger_workflow("stakeholder.sentiment.negative", payload)

    async def _calculate_engagement_score(self, metrics: dict[str, Any]) -> float:
        """Calculate engagement score from metrics."""
        messages_sent = metrics.get("messages_sent", 0)
        messages_opened = metrics.get("messages_opened", 0)
        messages_clicked = metrics.get("messages_clicked", 0)
        responses = metrics.get("responses_received", 0)
        events_attended = metrics.get("events_attended", 0)

        if messages_sent == 0:
            return 0

        # Weighted score
        open_rate = messages_opened / messages_sent if messages_sent > 0 else 0
        click_rate = messages_clicked / messages_sent if messages_sent > 0 else 0
        response_rate = responses / messages_sent if messages_sent > 0 else 0

        score = open_rate * 30 + click_rate * 30 + response_rate * 30 + events_attended * 10

        ml_score = await self._score_engagement_with_ml(metrics, score)
        if ml_score is not None:
            return min(100, ml_score)
        return min(100, score)  # type: ignore

    async def _classify_engagement_level(self, score: float) -> str:
        """Classify engagement level based on score."""
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"

    async def _calculate_overall_engagement(self) -> dict[str, Any]:
        """Calculate overall engagement metrics."""
        total_stakeholders = len(self.engagement_metrics)
        if total_stakeholders == 0:
            return {"average_score": 0, "distribution": {}}

        scores = []
        for stakeholder_id, metrics in self.engagement_metrics.items():
            score = await self._calculate_engagement_score(metrics)
            scores.append(score)

        average = sum(scores) / len(scores) if scores else 0

        return {
            "average_score": average,
            "stakeholders_tracked": total_stakeholders,
            "distribution": {
                "high": len([s for s in scores if s >= 70]),
                "medium": len([s for s in scores if 40 <= s < 70]),
                "low": len([s for s in scores if 20 <= s < 40]),
                "minimal": len([s for s in scores if s < 20]),
            },
        }

    async def _get_stakeholder_summary(self, project_id: str | None) -> dict[str, Any]:
        """Get stakeholder summary."""
        return {
            "total_stakeholders": len(self.stakeholder_register),
            "by_engagement_level": {"high": 0, "medium": 0, "low": 0},
        }

    async def _get_engagement_overview(self, project_id: str | None) -> dict[str, Any]:
        """Get engagement overview."""
        return await self._calculate_overall_engagement()

    async def _get_sentiment_trends(self, project_id: str | None) -> dict[str, Any]:
        """Get sentiment trends."""
        return await self._calculate_overall_sentiment()

    async def _get_upcoming_communications(self, project_id: str | None) -> list[dict[str, Any]]:
        """Get upcoming communications."""
        upcoming = []
        for message_id, message in self.messages.items():
            if message.get("status") == "Draft" and message.get("scheduled_send"):
                upcoming.append(
                    {
                        "message_id": message_id,
                        "subject": message.get("subject"),
                        "scheduled_send": message.get("scheduled_send"),
                    }
                )
        return upcoming[:10]

    async def _generate_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate summary communication report."""
        return {"report_type": "summary", "data": {}, "generated_at": datetime.utcnow().isoformat()}

    async def _generate_engagement_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate engagement report."""
        return {
            "report_type": "engagement",
            "data": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_sentiment_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate sentiment report."""
        return {
            "report_type": "sentiment",
            "data": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Stakeholder & Communications Management Agent...")
        self.history_store.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "stakeholder_registry",
            "stakeholder_profiling",
            "stakeholder_classification",
            "stakeholder_segmentation",
            "communication_planning",
            "communication_preferences",
            "message_generation",
            "message_personalization",
            "message_scheduling",
            "multi_channel_delivery",
            "template_management",
            "intelligent_summarization",
            "delivery_batching",
            "feedback_collection",
            "sentiment_analysis",
            "event_scheduling",
            "meeting_coordination",
            "engagement_tracking",
            "engagement_scoring",
            "communication_analytics",
            "delivery_tracking",
            "stakeholder_dashboards",
            "communication_reporting",
        ]
