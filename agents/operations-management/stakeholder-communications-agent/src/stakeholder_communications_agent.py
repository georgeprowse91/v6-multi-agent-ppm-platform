"""
Stakeholder & Communications Management Agent

Purpose:
Manages stakeholder identification, classification, engagement planning and communication
execution across the portfolio. Ensures stakeholders receive the right information at the
right time through appropriate channels, fostering engagement and monitoring sentiment.

Specification: agents/operations-management/stakeholder-communications-agent/README.md
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

from agents.common.connector_integration import CalendarIntegrationService, NotificationService
from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore
from connector_secrets import resolve_secret

# ---------------------------------------------------------------------------
# Package bootstrap: when this file is loaded via importlib.util.spec_from_
# file_location (e.g. from tests) it has no package context, so relative
# imports in sub-modules would fail.  We register the *src* directory as a
# synthetic package so that relative imports resolve correctly everywhere.
# ---------------------------------------------------------------------------
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

_PKG = "stakeholder_comms_pkg"

if not globals().get("__package__"):
    import types as _types

    # Create the synthetic parent package
    _pkg_mod = _types.ModuleType(_PKG)
    _pkg_mod.__path__ = [_SRC_DIR]  # type: ignore[attr-defined]
    _pkg_mod.__package__ = _PKG
    _pkg_mod.__file__ = os.path.join(_SRC_DIR, "__init__.py")
    sys.modules.setdefault(_PKG, _pkg_mod)

    # Set our own package so relative imports from this module work
    globals()["__package__"] = _PKG
    globals()["__spec__"] = None  # clear stale spec

    # Pre-register the actions sub-package skeleton so its __init__.py
    # relative imports (.classify_stakeholder, etc.) resolve correctly
    _actions_mod = _types.ModuleType(f"{_PKG}.actions")
    _actions_mod.__path__ = [os.path.join(_SRC_DIR, "actions")]  # type: ignore[attr-defined]
    _actions_mod.__package__ = f"{_PKG}.actions"
    _actions_mod.__file__ = os.path.join(_SRC_DIR, "actions", "__init__.py")
    sys.modules.setdefault(f"{_PKG}.actions", _actions_mod)

# Now relative imports work regardless of how this module was loaded.
from .stakeholder_models import CommunicationHistoryStore, ServiceBusPublisher  # noqa: E402
from .stakeholder_utils import (  # noqa: E402
    WebClient,
    TwilioClient,
    get_template,
    load_default_templates,
    resolve_delivery_channels,
    resolve_token,
    send_via_channel,
)
from .actions import (  # noqa: E402
    analyze_sentiment,
    classify_stakeholder,
    collect_feedback,
    create_communication_plan,
    edit_message,
    flush_digest_notifications,
    generate_communication_report,
    generate_message,
    get_stakeholder_dashboard,
    register_stakeholder,
    schedule_event,
    schedule_message,
    send_message,
    summarize_report,
    track_delivery_event,
    track_engagement,
    update_communication_preferences,
)


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

    def __init__(self, agent_id: str = "stakeholder-communications-agent", config: dict[str, Any] | None = None):
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
        self.exchange_token = resolve_token(
            self.keyvault_url, "EXCHANGE_TOKEN", "EXCHANGE_TOKEN_SECRET_NAME", config
        )
        self.teams_token = resolve_token(
            self.keyvault_url, "TEAMS_TOKEN", "TEAMS_TOKEN_SECRET_NAME", config
        )
        self.slack_token = resolve_token(
            self.keyvault_url, "SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN_SECRET_NAME", config
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
            (config or {}).get("azure_openai_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
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
            (config or {}).get("crm_timeout_seconds") or os.getenv("CRM_TIMEOUT_SECONDS", "10")
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

        self.slack_client = (
            WebClient(token=self.slack_token) if WebClient and self.slack_token else None
        )
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

        self.default_locale = (config or {}).get("default_locale", "en-AU")
        self.delivery_batch_size = int((config or {}).get("delivery_batch_size", 50))
        self.delivery_batch_interval = int(
            (config or {}).get("delivery_batch_interval_minutes", 15)
        )
        self.digest_window_minutes = int((config or {}).get("digest_window_minutes", 60))
        self.digest_batch_size = int((config or {}).get("digest_batch_size", 10))
        self.digest_queue: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.communication_templates = load_default_templates()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

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
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "register_stakeholder":
            stakeholder_data = input_data.get("stakeholder", {})
            required_fields = ["name", "email", "role"]
            for field in required_fields:
                if field not in stakeholder_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        return True

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

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
            return await register_stakeholder(self, tenant_id, input_data.get("stakeholder", {}))

        elif action == "classify_stakeholder":
            return await classify_stakeholder(
                self, tenant_id, input_data.get("stakeholder_id")  # type: ignore
            )

        elif action == "create_communication_plan":
            return await create_communication_plan(self, input_data.get("plan", {}))

        elif action == "generate_message":
            return await generate_message(self, input_data.get("message", {}))

        elif action == "edit_message":
            return await edit_message(
                self, input_data.get("message_id"), input_data.get("message", {})
            )

        elif action == "send_message":
            return await send_message(self, tenant_id, input_data.get("message_id"))  # type: ignore

        elif action == "schedule_message":
            return await schedule_message(self, tenant_id, input_data.get("message_id"))  # type: ignore

        elif action == "summarize_report":
            return await summarize_report(
                self,
                input_data.get("report", ""),
                input_data.get("role", "general"),
                input_data.get("locale"),
            )

        elif action == "update_communication_preferences":
            return await update_communication_preferences(
                self,
                tenant_id,
                input_data.get("stakeholder_id"),
                input_data.get("preferences", {}),
            )

        elif action == "collect_feedback":
            return await collect_feedback(self, input_data.get("feedback", {}))

        elif action == "analyze_sentiment":
            return await analyze_sentiment(self, input_data.get("stakeholder_id"))

        elif action == "schedule_event":
            return await schedule_event(self, input_data.get("event", {}))

        elif action == "track_engagement":
            return await track_engagement(self, input_data.get("stakeholder_id"))

        elif action == "track_delivery_event":
            return await track_delivery_event(
                self,
                tenant_id,
                input_data.get("message_id"),
                input_data.get("stakeholder_id"),
                input_data.get("event", {}),
            )

        elif action == "flush_digest_notifications":
            return await flush_digest_notifications(
                self, tenant_id, input_data.get("stakeholder_id")
            )

        elif action == "get_stakeholder_dashboard":
            return await get_stakeholder_dashboard(
                self, input_data.get("project_id"), input_data.get("filters", {})
            )

        elif action == "generate_communication_report":
            return await generate_communication_report(
                self, input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Thin delegation wrappers (preserve internal API for tests/callers)
    # ------------------------------------------------------------------

    def _resolve_delivery_channels(
        self, message: dict[str, Any], stakeholder: dict[str, Any]
    ) -> list[str]:
        return resolve_delivery_channels(message, stakeholder)

    async def _queue_digest_notifications(
        self, tenant_id: str, message: dict[str, Any]
    ) -> list[dict[str, Any]]:
        from .actions.delivery_actions import queue_digest_notifications
        return await queue_digest_notifications(self, tenant_id, message)

    async def _flush_digest_notifications(
        self, tenant_id: str, stakeholder_id: str | None
    ) -> dict[str, Any]:
        return await flush_digest_notifications(self, tenant_id, stakeholder_id)

    async def _send_via_channel(
        self,
        channel: str,
        stakeholder: dict[str, Any],
        message: dict[str, Any],
        content: str,
        subject_override: str | None = None,
    ) -> dict[str, Any]:
        return await send_via_channel(
            self, channel, stakeholder, message, content, subject_override
        )

    def _get_template(self, template_id: str | None, locale: str) -> dict[str, Any]:
        return get_template(self, template_id, locale)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

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
