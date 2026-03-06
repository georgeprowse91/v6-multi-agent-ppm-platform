"""
Utility functions, conditional imports, and shared helpers for the
Stakeholder & Communications Management Agent.
"""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
from connector_secrets import fetch_keyvault_secret, resolve_secret

if TYPE_CHECKING:
    from .stakeholder_communications_agent import StakeholderCommunicationsAgent


# ---------------------------------------------------------------------------
# Conditional / optional imports
# ---------------------------------------------------------------------------

def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


if _safe_find_spec("slack_sdk"):
    from slack_sdk import WebClient
else:
    WebClient = None

if _safe_find_spec("twilio.rest"):
    from twilio.rest import Client as TwilioClient
else:
    TwilioClient = None

if _safe_find_spec("azure.communication.email"):
    from azure.communication.email import EmailClient
else:
    EmailClient = None

if _safe_find_spec("azure.ai.textanalytics"):
    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential
else:
    TextAnalyticsClient = Any
    AzureKeyCredential = Any

if _safe_find_spec("connectors.salesforce.src.main"):
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


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

async def generate_stakeholder_id() -> str:
    """Generate unique stakeholder ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"STK-{timestamp}"


async def generate_plan_id() -> str:
    """Generate unique plan ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PLAN-{timestamp}"


async def generate_message_id() -> str:
    """Generate unique message ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"MSG-{timestamp}"


async def generate_feedback_id() -> str:
    """Generate unique feedback ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"FB-{timestamp}"


async def generate_event_id() -> str:
    """Generate unique event ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"EVT-{timestamp}"


# ---------------------------------------------------------------------------
# Token / secret resolution
# ---------------------------------------------------------------------------

def resolve_token(
    keyvault_url: str | None,
    env_name: str,
    secret_name_env: str,
    config: dict[str, Any] | None,
) -> str | None:
    configured = resolve_secret((config or {}).get(env_name.lower()))
    direct = resolve_secret(os.getenv(env_name))
    if configured:
        return configured
    if direct:
        return direct
    secret_name = resolve_secret(os.getenv(secret_name_env))
    return fetch_keyvault_secret(keyvault_url, secret_name)


# ---------------------------------------------------------------------------
# Communication history, events and workflows
# ---------------------------------------------------------------------------

def record_communication_history(agent: StakeholderCommunicationsAgent, record: dict[str, Any]) -> None:
    record["record_id"] = (
        record.get("record_id") or f"COM-{datetime.now(timezone.utc).isoformat()}"
    )
    record["created_at"] = record.get("created_at") or datetime.now(timezone.utc).isoformat()
    agent.history_store.add_record(record)


def publish_event(agent: StakeholderCommunicationsAgent, event_type: str, payload: dict[str, Any]) -> None:
    agent.service_bus_publisher.publish(event_type, payload)


def trigger_workflow(agent: StakeholderCommunicationsAgent, event_type: str, payload: dict[str, Any]) -> None:
    if not agent.logic_apps_trigger_url:
        return
    requests.post(
        agent.logic_apps_trigger_url,
        json={"event_type": event_type, "payload": payload},
        timeout=10,
    )


def publish_metrics_event(
    agent: StakeholderCommunicationsAgent,
    *,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    enriched = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    publish_event(agent, "stakeholder.communication.metrics", enriched)


# ---------------------------------------------------------------------------
# Stakeholder load / lookup
# ---------------------------------------------------------------------------

def load_stakeholder(
    agent: StakeholderCommunicationsAgent, tenant_id: str, stakeholder_id: str
) -> dict[str, Any] | None:
    stakeholder = agent.stakeholder_register.get(stakeholder_id)
    if stakeholder:
        return stakeholder
    stored = agent.stakeholder_store.get(tenant_id, stakeholder_id)
    if stored:
        agent.stakeholder_register[stakeholder_id] = stored
    return stored


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------

async def personalize_content(content: str, stakeholder: dict[str, Any]) -> str:
    """Personalize content for stakeholder."""
    personalized = content.replace("{name}", stakeholder.get("name", ""))
    personalized = personalized.replace("{role}", stakeholder.get("role", ""))
    return personalized


def safe_format_template(template: str, data: dict[str, Any]) -> str:
    safe_data = {key: value if value is not None else "" for key, value in data.items()}
    try:
        return template.format_map(safe_data)
    except (KeyError, ValueError):
        return template


def get_template(
    agent: StakeholderCommunicationsAgent, template_id: str | None, locale: str
) -> dict[str, Any]:
    if not template_id:
        return {}
    template = agent.communication_templates.get(template_id, {})
    return template.get(locale) or template.get(agent.default_locale, {})


# ---------------------------------------------------------------------------
# Graph API helper
# ---------------------------------------------------------------------------

async def graph_request(
    agent: StakeholderCommunicationsAgent,
    token: str | None,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not token:
        return {"status": "skipped", "reason": "missing_token"}
    url = f"{agent.graph_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
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


# ---------------------------------------------------------------------------
# Text analytics
# ---------------------------------------------------------------------------

def build_text_analytics_client(agent: StakeholderCommunicationsAgent):
    if not agent.text_analytics_endpoint or not agent.text_analytics_key:
        return None
    if not TextAnalyticsClient or not AzureKeyCredential:
        return None
    return TextAnalyticsClient(
        endpoint=agent.text_analytics_endpoint,
        credential=AzureKeyCredential(agent.text_analytics_key),
    )


async def analyze_text_sentiment(agent: StakeholderCommunicationsAgent, text: str) -> dict[str, Any]:
    """Analyze sentiment of text."""
    client = build_text_analytics_client(agent)
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
    if agent.text_analytics_endpoint and agent.text_analytics_key:
        payload = {"documents": [{"id": "1", "language": "en", "text": text}]}
        response = requests.post(
            f"{agent.text_analytics_endpoint.rstrip('/')}/text/analytics/v3.1/sentiment",
            headers={"Ocp-Apim-Subscription-Key": agent.text_analytics_key},
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
    return {"score": 0.5, "label": "neutral", "confidence": 0.8}


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

async def suggest_classification(stakeholder_data: dict[str, Any]) -> dict[str, Any]:
    """Suggest stakeholder classification."""
    role = stakeholder_data.get("role", "").lower()
    if "executive" in role or "director" in role:
        return {"influence": "high", "interest": "high", "engagement_level": "high"}
    elif "manager" in role:
        return {"influence": "medium", "interest": "high", "engagement_level": "medium"}
    else:
        return {"influence": "low", "interest": "medium", "engagement_level": "low"}


async def determine_engagement_strategy(influence: str, interest: str) -> dict[str, Any]:
    """Determine engagement strategy based on power-interest matrix."""
    if influence == "high" and interest == "high":
        return {
            "strategy": "manage_closely",
            "frequency": "weekly",
            "channels": ["email", "teams", "meetings"],
        }
    elif influence == "high" and interest == "low":
        return {
            "strategy": "keep_satisfied",
            "frequency": "bi-weekly",
            "channels": ["email", "meetings"],
        }
    elif influence == "low" and interest == "high":
        return {
            "strategy": "keep_informed",
            "frequency": "weekly",
            "channels": ["email", "portal"],
        }
    else:
        return {"strategy": "monitor", "frequency": "monthly", "channels": ["email"]}


# ---------------------------------------------------------------------------
# CRM integration
# ---------------------------------------------------------------------------

async def enrich_stakeholder_profile(
    agent: StakeholderCommunicationsAgent, stakeholder_data: dict[str, Any]
) -> dict[str, Any]:
    """Enrich stakeholder profile from CRM."""
    crm_profile = await sync_with_crm(agent, stakeholder_data)
    if crm_profile:
        stakeholder_data["crm_profile"] = crm_profile
        stakeholder_data["crm_synced_at"] = datetime.now(timezone.utc).isoformat()
    return stakeholder_data


async def sync_with_crm(
    agent: StakeholderCommunicationsAgent, stakeholder_data: dict[str, Any]
) -> dict[str, Any]:
    """Synchronize stakeholder profile with CRM connectors (e.g., Salesforce)."""
    if not SalesforceConfig or not _build_token_manager or not _build_client:
        return await sync_with_crm_rest(agent, stakeholder_data)
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
            "account": (
                (record.get("Account") or {}).get("Name")
                if isinstance(record.get("Account"), dict)
                else record.get("Account.Name")
            ),
            "email": record.get("Email"),
        }
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:  # noqa: BLE001
        agent.logger.warning("CRM sync failed: %s", exc)
        return await sync_with_crm_rest(agent, stakeholder_data)


async def sync_with_crm_rest(
    agent: StakeholderCommunicationsAgent, stakeholder_data: dict[str, Any]
) -> dict[str, Any]:
    if not (agent.crm_base_url and agent.crm_api_key):
        return {}
    email = stakeholder_data.get("email")
    if not email:
        return {}
    url = f"{agent.crm_base_url.rstrip('/')}/{agent.crm_profile_endpoint.lstrip('/')}"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {agent.crm_api_key}"},
            params={"email": email},
            timeout=agent.crm_timeout_seconds,
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
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:  # noqa: BLE001
        agent.logger.warning("CRM REST sync failed: %s", exc)
        return {}


async def upsert_crm_profile(
    agent: StakeholderCommunicationsAgent, stakeholder: dict[str, Any]
) -> dict[str, Any] | None:
    if not (agent.crm_base_url and agent.crm_api_key):
        return None
    url = f"{agent.crm_base_url.rstrip('/')}/{agent.crm_upsert_endpoint.lstrip('/')}"
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
            headers={"Authorization": f"Bearer {agent.crm_api_key}"},
            json=payload,
            timeout=agent.crm_timeout_seconds,
        )
        if response.status_code >= 400:
            return {"status": "error", "code": response.status_code}
        return {"status": "ok"}
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:  # noqa: BLE001
        agent.logger.warning("CRM upsert failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


# ---------------------------------------------------------------------------
# Consent check
# ---------------------------------------------------------------------------

async def has_consent(stakeholder: dict[str, Any], channel: str) -> bool:
    """Check consent and opt-out flags for stakeholder."""
    if stakeholder.get("opt_out"):
        return False
    if not stakeholder.get("consent", True):
        return False
    preferences = stakeholder.get("communication_preferences", {})
    if channel in preferences.get("opt_out_channels", []):
        return False
    return True


# ---------------------------------------------------------------------------
# Delivery channel resolution
# ---------------------------------------------------------------------------

def resolve_delivery_channels(
    message: dict[str, Any], stakeholder: dict[str, Any]
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


# ---------------------------------------------------------------------------
# Optimal send-time calculation
# ---------------------------------------------------------------------------

async def calculate_optimal_send_time(
    stakeholder: dict[str, Any], scheduled_send: str | None
) -> str | None:
    if scheduled_send:
        return scheduled_send
    preferences = stakeholder.get("communication_preferences", {})
    preferred_hour = preferences.get("preferred_send_hour")
    utc_offset = int(preferences.get("utc_offset_minutes") or 0)
    if preferred_hour is None:
        return None
    now_utc = datetime.now(timezone.utc)
    local_time = now_utc + timedelta(minutes=utc_offset)
    candidate = local_time.replace(hour=int(preferred_hour), minute=0, second=0, microsecond=0)
    if candidate <= local_time:
        candidate = candidate + timedelta(days=1)
    send_time = candidate - timedelta(minutes=utc_offset)
    return send_time.isoformat()


# ---------------------------------------------------------------------------
# Delivery schedule builder
# ---------------------------------------------------------------------------

def build_delivery_schedule(
    agent: StakeholderCommunicationsAgent,
    personalized_messages: list[dict[str, Any]],
    scheduled_start: str | None,
) -> list[dict[str, Any]]:
    if not personalized_messages:
        return []
    if scheduled_start:
        try:
            start_time = datetime.fromisoformat(scheduled_start)
        except ValueError:
            start_time = datetime.now(timezone.utc) + timedelta(minutes=5)
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
                start_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        else:
            start_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    batches = [
        personalized_messages[i : i + agent.delivery_batch_size]
        for i in range(0, len(personalized_messages), agent.delivery_batch_size)
    ]
    schedule = []
    for index, batch in enumerate(batches):
        scheduled_time = start_time + timedelta(minutes=index * agent.delivery_batch_interval)
        schedule.append(
            {
                "batch_id": f"{index + 1}",
                "scheduled_time": scheduled_time.isoformat(),
                "recipient_count": len(batch),
            }
        )
    return schedule


# ---------------------------------------------------------------------------
# Message content generation
# ---------------------------------------------------------------------------

async def generate_message_content(
    agent: StakeholderCommunicationsAgent,
    template: str,
    data: dict[str, Any],
    prompt_type: str | None = None,
    prompt: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Generate message content using NLG."""
    if agent.openai_endpoint and agent.openai_api_key and agent.openai_deployment:
        draft = await agent._generate_openai_text(
            template=template, data=data, prompt_type=prompt_type, prompt=prompt
        )
        if not draft.get("content") and template:
            return safe_format_template(template, data), {"provider": "template_fallback"}
        return draft.get("content", ""), draft
    if template:
        return safe_format_template(template, data), {"provider": "template"}
    return "Sample message content", {"provider": "fallback"}


async def generate_openai_text(
    agent: StakeholderCommunicationsAgent,
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
        f"{agent.openai_endpoint.rstrip('/')}/openai/deployments/"
        f"{agent.openai_deployment}/chat/completions"
    )
    response = requests.post(
        url,
        headers={"api-key": agent.openai_api_key},
        params={"api-version": agent.openai_api_version},
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


async def summarize_report(
    agent: StakeholderCommunicationsAgent, report: str, role: str, locale: str | None
) -> dict[str, Any]:
    """Summarize a report into concise content for a role."""
    if not report:
        return {"summary": "", "provider": "empty"}
    if agent.openai_endpoint and agent.openai_api_key and agent.openai_deployment:
        prompt = (
            f"Summarize the following report for the {role} role. "
            f"Use locale {locale or agent.default_locale} and keep it concise.\n\n{report}"
        )
        draft = await agent._generate_openai_text(
            template=report,
            data={"report": report, "role": role, "locale": locale},
            prompt_type="summary",
            prompt=prompt,
        )
        return {"summary": draft.get("content", ""), "provider": draft.get("provider")}
    short_summary = report[:500] + ("..." if len(report) > 500 else "")
    return {"summary": short_summary, "provider": "fallback"}


async def generate_meeting_agenda(
    agent: StakeholderCommunicationsAgent, event_data: dict[str, Any]
) -> list[str]:
    if not (agent.openai_endpoint and agent.openai_api_key and agent.openai_deployment):
        return []
    draft = await agent._generate_openai_text(
        template=event_data.get("description", ""),
        data=event_data,
        prompt_type="meeting_agenda",
        prompt=event_data.get("agenda_prompt"),
    )
    return [line.strip("- ").strip() for line in draft.get("content", "").splitlines() if line]


async def generate_action_items(
    agent: StakeholderCommunicationsAgent, context: dict[str, Any]
) -> list[str]:
    if not (agent.openai_endpoint and agent.openai_api_key and agent.openai_deployment):
        return []
    draft = await agent._generate_openai_text(
        template=context.get("summary", ""),
        data=context,
        prompt_type="action_items",
        prompt=context.get("action_items_prompt"),
    )
    return [line.strip("- ").strip() for line in draft.get("content", "").splitlines() if line]


# ---------------------------------------------------------------------------
# Engagement scoring
# ---------------------------------------------------------------------------

async def score_engagement_with_ml(
    agent: StakeholderCommunicationsAgent, metrics: dict[str, Any], baseline_score: float
) -> float | None:
    if not agent.azure_ml_endpoint or not agent.azure_ml_key:
        return None
    response = requests.post(
        agent.azure_ml_endpoint,
        headers={"Authorization": f"Bearer {agent.azure_ml_key}"},
        json={"metrics": metrics, "baseline_score": baseline_score},
        timeout=10,
    )
    if response.status_code >= 400:
        return None
    payload = response.json()
    return payload.get("score")


async def calculate_engagement_score(
    agent: StakeholderCommunicationsAgent, metrics: dict[str, Any]
) -> float:
    """Calculate engagement score from metrics."""
    messages_sent = metrics.get("messages_sent", 0)
    messages_opened = metrics.get("messages_opened", 0)
    messages_clicked = metrics.get("messages_clicked", 0)
    responses = metrics.get("responses_received", 0)
    events_attended = metrics.get("events_attended", 0)

    if messages_sent == 0:
        return 0

    open_rate = messages_opened / messages_sent if messages_sent > 0 else 0
    click_rate = messages_clicked / messages_sent if messages_sent > 0 else 0
    response_rate = responses / messages_sent if messages_sent > 0 else 0

    score = open_rate * 30 + click_rate * 30 + response_rate * 30 + events_attended * 10

    ml_score = await score_engagement_with_ml(agent, metrics, score)
    if ml_score is not None:
        return min(100, ml_score)
    return min(100, score)  # type: ignore


async def classify_engagement_level(score: float) -> str:
    """Classify engagement level based on score."""
    if score >= 70:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "minimal"


async def prioritize_outreach(engagement_score: float) -> str:
    if engagement_score >= 70:
        return "low"
    if engagement_score >= 40:
        return "medium"
    return "high"


async def calculate_overall_engagement(agent: StakeholderCommunicationsAgent) -> dict[str, Any]:
    """Calculate overall engagement metrics."""
    total_stakeholders = len(agent.engagement_metrics)
    if total_stakeholders == 0:
        return {"average_score": 0, "distribution": {}}

    scores = []
    for stakeholder_id, metrics in agent.engagement_metrics.items():
        score = await calculate_engagement_score(agent, metrics)
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


# ---------------------------------------------------------------------------
# Sentiment helpers
# ---------------------------------------------------------------------------

async def calculate_sentiment_trend(feedback_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate sentiment trend."""
    if not feedback_list:
        return {"current": 0, "trend": "stable"}
    scores = [f.get("sentiment", {}).get("score", 0) for f in feedback_list[-10:]]
    current = scores[-1] if scores else 0
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


async def calculate_overall_sentiment(agent: StakeholderCommunicationsAgent) -> dict[str, Any]:
    """Calculate overall sentiment across all stakeholders."""
    all_scores = []
    for stakeholder_id, feedback_list in agent.feedback.items():
        for feedback_item in feedback_list:
            score = feedback_item.get("sentiment", {}).get("score", 0)
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


async def trigger_sentiment_alert(
    agent: StakeholderCommunicationsAgent,
    stakeholder_id: str | None,
    sentiment: dict[str, Any],
    feedback_record: dict[str, Any],
) -> None:
    payload = {
        "stakeholder_id": stakeholder_id,
        "sentiment": sentiment,
        "feedback": feedback_record,
    }
    publish_event(agent, "stakeholder.sentiment.negative", payload)
    trigger_workflow(agent, "stakeholder.sentiment.negative", payload)


# ---------------------------------------------------------------------------
# Channel senders
# ---------------------------------------------------------------------------

async def send_via_channel(
    agent: StakeholderCommunicationsAgent,
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
        return await send_email(
            agent,
            stakeholder.get("email"),
            subject,
            content,
            attachments,
            use_graph=message.get("use_graph", True),
        )
    if channel == "teams":
        return await send_teams_message(
            agent,
            stakeholder.get("teams_id") or stakeholder.get("email"),
            content,
        )
    if channel == "slack":
        return await send_slack_message(
            agent,
            stakeholder.get("slack_channel") or stakeholder.get("slack_id"),
            content,
        )
    if channel == "sms":
        return await send_sms(agent, stakeholder.get("phone"), content)
    if channel in {"push", "portal"}:
        return await send_push(agent, stakeholder, subject, content)
    return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}


async def send_email(
    agent: StakeholderCommunicationsAgent,
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
    if agent.notification_service and not attachments:
        result = await agent.notification_service.send_email(
            recipient,
            subject,
            content,
            metadata={"provider_hint": "smtp"},
        )
        if result.get("status") != "failed":
            return {
                "status": "delivered",
                "sent_at": result.get("sent_at") or datetime.now(timezone.utc).isoformat(),
                "provider": result.get("provider"),
            }
    if use_graph and agent.exchange_token:
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
        response = await graph_request(
            agent, agent.exchange_token, "POST", "/me/sendMail", message_payload
        )
        status = "delivered" if response.get("status") != "error" else "failed"
        return {"status": status, "sent_at": datetime.now(timezone.utc).isoformat()}
    if agent.acs_connection_string and EmailClient:
        client = EmailClient.from_connection_string(agent.acs_connection_string)
        response = client.begin_send(
            {
                "content": {"subject": subject, "plainText": content},
                "recipients": {"to": [{"address": recipient}]},
                "senderAddress": agent.sendgrid_from_email or "noreply@example.com",
            }
        )
        response.result()
        return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}
    if agent.sendgrid_api_key:
        payload = {
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": {"email": agent.sendgrid_from_email or "noreply@example.com"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": content}],
        }
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {agent.sendgrid_api_key}"},
            json=payload,
            timeout=10,
        )
        if response.status_code < 400:
            return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}
        return {"status": "failed", "reason": response.text}
    return {"status": "failed", "reason": "no_email_provider"}


async def send_teams_message(
    agent: StakeholderCommunicationsAgent, recipient: str | None, content: str
) -> dict[str, Any]:
    if not agent.teams_token:
        return {"status": "failed", "reason": "missing_teams_configuration"}
    payload = {"body": {"contentType": "HTML", "content": content}}
    endpoint = None
    if recipient and "@" in recipient:
        endpoint = f"/users/{recipient}/chats"
    elif recipient:
        endpoint = f"/chats/{recipient}/messages"
    if not endpoint:
        return {"status": "failed", "reason": "missing_recipient"}
    response = await graph_request(agent, agent.teams_token, "POST", endpoint, payload)
    status = "delivered" if response.get("status") != "error" else "failed"
    return {"status": status, "sent_at": datetime.now(timezone.utc).isoformat()}


async def send_slack_message(
    agent: StakeholderCommunicationsAgent, channel: str | None, content: str
) -> dict[str, Any]:
    if not channel or not agent.slack_client:
        return {"status": "failed", "reason": "missing_slack_configuration"}
    response = agent.slack_client.chat_postMessage(channel=channel, text=content)
    return {
        "status": "delivered" if response.get("ok") else "failed",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


async def send_sms(
    agent: StakeholderCommunicationsAgent, phone: str | None, content: str
) -> dict[str, Any]:
    if not phone:
        return {"status": "failed", "reason": "missing_phone"}
    if agent.notification_service:
        sms_result = await agent.notification_service.send_sms(phone, content)
        if sms_result.get("status") != "failed":
            return sms_result
    if agent.twilio_client and agent.twilio_from_number:
        message = agent.twilio_client.messages.create(
            body=content,
            from_=agent.twilio_from_number,
            to=phone,
        )
        return {
            "status": "delivered",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sid": message.sid,
        }
    if agent.twilio_account_sid and agent.twilio_auth_token and agent.twilio_from_number:
        payload = {
            "From": agent.twilio_from_number,
            "To": phone,
            "Body": content,
        }
        auth = (agent.twilio_account_sid, agent.twilio_auth_token)
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{agent.twilio_account_sid}/Messages.json",
            data=payload,
            auth=auth,
            timeout=10,
        )
        if response.status_code < 400:
            return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}
        return {"status": "failed", "reason": response.text}
    return {"status": "failed", "reason": "no_sms_provider"}


async def send_push(
    agent: StakeholderCommunicationsAgent,
    stakeholder: dict[str, Any],
    subject: str,
    content: str,
) -> dict[str, Any]:
    if agent.notification_service and stakeholder.get("push_token"):
        push_result = await agent.notification_service.send_push_notification(
            stakeholder.get("push_token"), content
        )
        if push_result.get("status") != "failed":
            return push_result
    if agent.fcm_server_key and stakeholder.get("push_token"):
        payload = {
            "to": stakeholder.get("push_token"),
            "notification": {"title": subject, "body": content},
            "data": {"stakeholder_id": stakeholder.get("stakeholder_id")},
        }
        response = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={agent.fcm_server_key}"},
            json=payload,
            timeout=10,
        )
        if response.status_code < 400:
            return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}
        return {"status": "failed", "reason": response.text}
    if agent.push_endpoint:
        payload = {
            "stakeholder_id": stakeholder.get("stakeholder_id"),
            "subject": subject,
            "content": content,
            "channel": "push",
        }
        headers = {"Content-Type": "application/json"}
        if agent.push_api_key:
            headers["Authorization"] = f"Bearer {agent.push_api_key}"
        response = requests.post(agent.push_endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code < 400:
            return {"status": "delivered", "sent_at": datetime.now(timezone.utc).isoformat()}
        return {"status": "failed", "reason": response.text}
    return {"status": "failed", "reason": "no_push_provider"}


# ---------------------------------------------------------------------------
# Meeting time suggestions (Graph API)
# ---------------------------------------------------------------------------

async def suggest_meeting_times(
    agent: StakeholderCommunicationsAgent,
    stakeholder_ids: list[str],
    duration: int,
    time_window: dict[str, Any] | None,
) -> list[str]:
    """Suggest meeting times using Microsoft Graph meeting time suggestions."""
    attendees = []
    for stakeholder_id in stakeholder_ids:
        stakeholder = agent.stakeholder_register.get(stakeholder_id) or load_stakeholder(
            agent, "default", stakeholder_id
        )
        if stakeholder and stakeholder.get("email"):
            attendees.append({"emailAddress": {"address": stakeholder.get("email")}})
    if not attendees or not agent.exchange_token:
        return []
    start_time = (time_window or {}).get("start") or (
        datetime.now(timezone.utc) + timedelta(days=1)
    ).replace(hour=9, minute=0).isoformat()
    end_time = (time_window or {}).get("end") or (
        datetime.now(timezone.utc) + timedelta(days=7)
    ).replace(hour=17, minute=0).isoformat()
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
    response = await graph_request(
        agent, agent.exchange_token, "POST", "/me/findMeetingTimes", payload
    )
    suggestions = (
        response.get("meetingTimeSuggestions", []) if isinstance(response, dict) else []
    )
    return [
        suggestion.get("meetingTimeSlot", {}).get("start", {}).get("dateTime")
        for suggestion in suggestions
        if suggestion.get("meetingTimeSlot")
    ]


async def create_graph_event(
    agent: StakeholderCommunicationsAgent,
    event: dict[str, Any],
    attachments: list[dict[str, Any]] | list[str],
) -> dict[str, Any]:
    """Create a calendar event and send invites via Graph API."""
    if not agent.exchange_token:
        if agent.calendar_service:
            return agent.calendar_service.create_event(
                {
                    "title": event.get("title"),
                    "summary": event.get("title"),
                    "scheduled_time": event.get("scheduled_time"),
                    "description": event.get("description"),
                }
            )
        return {"status": "skipped", "reason": "missing_exchange_token"}
    scheduled_time = event.get("scheduled_time") or datetime.now(timezone.utc).isoformat()
    try:
        start_dt = datetime.fromisoformat(scheduled_time)
    except ValueError:
        start_dt = datetime.now(timezone.utc)
        scheduled_time = start_dt.isoformat()
    attendees = []
    for stakeholder_id in event.get("stakeholder_ids", []):
        stakeholder = agent.stakeholder_register.get(stakeholder_id)
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
                (start_dt + timedelta(minutes=event.get("duration_minutes", 60))).isoformat()
                if scheduled_time
                else None
            ),
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
    response = await graph_request(agent, agent.exchange_token, "POST", "/me/events", payload)
    return {
        "status": response.get("status", "ok"),
        "event_id": response.get("id"),
        "online_meeting_url": (response.get("onlineMeeting") or {}).get("joinUrl"),
        "scheduled_time": (response.get("start") or {}).get("dateTime"),
    }


async def propose_optimal_time(stakeholder_ids: list[str], duration: int) -> str:
    """Propose optimal meeting time considering time zones."""
    optimal_time = datetime.now(timezone.utc) + timedelta(days=1)
    optimal_time = optimal_time.replace(hour=10, minute=0, second=0, microsecond=0)
    return optimal_time.isoformat()


# ---------------------------------------------------------------------------
# Default templates
# ---------------------------------------------------------------------------

def load_default_templates() -> dict[str, dict[str, dict[str, str]]]:
    return {
        "project_status_update": {
            "en-AU": {
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
            "en-AU": {
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
            "en-AU": {
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
            "en-AU": {
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
            "en-AU": {
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
