"""
Service Bus and Microsoft Graph lifecycle initialization for the Approval Workflow Agent.

Handles external service connections setup during agent initialization.
"""

from __future__ import annotations

import importlib.util
import os
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from approval_workflow_agent import ApprovalWorkflowAgent


async def initialize_service_bus(agent: ApprovalWorkflowAgent) -> None:
    service_bus_config = agent.config.get("service_bus", {})
    connection_string = service_bus_config.get("connection_string") or os.getenv(
        "SERVICE_BUS_CONNECTION_STRING"
    )
    if not connection_string:
        agent.logger.info("Service Bus connection string not configured; skipping setup.")
        return
    if not importlib.util.find_spec("azure.servicebus"):
        agent.logger.warning("Azure Service Bus SDK not installed; skipping setup.")
        return

    topic = service_bus_config.get("topic", "approval-events")
    subscription = service_bus_config.get("subscription", f"{agent.agent_id}-approvals")
    from azure.servicebus import ServiceBusClient
    from azure.servicebus.management import ServiceBusAdministrationClient

    agent.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
    agent.service_bus_admin = ServiceBusAdministrationClient.from_connection_string(
        connection_string
    )
    agent.service_bus_topic = topic
    agent.service_bus_subscription = subscription
    _ensure_service_bus_entities(agent, topic, subscription)
    agent.service_bus_receiver = agent.service_bus_client.get_subscription_receiver(
        topic, subscription
    )
    agent.logger.info(
        "Service Bus subscription ready for approvals: topic=%s subscription=%s",
        topic,
        subscription,
    )


def _ensure_service_bus_entities(
    agent: ApprovalWorkflowAgent, topic: str, subscription: str
) -> None:
    if not agent.service_bus_admin:
        return
    try:
        agent.service_bus_admin.get_topic(topic)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        agent.service_bus_admin.create_topic(topic)
    try:
        agent.service_bus_admin.get_subscription(topic, subscription)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        agent.service_bus_admin.create_subscription(topic, subscription)


async def initialize_graph_client(agent: ApprovalWorkflowAgent) -> None:
    graph_config = agent.config.get("graph", {})
    tenant_id = graph_config.get("tenant_id") or os.getenv("AZURE_TENANT_ID")
    client_id = graph_config.get("client_id") or os.getenv("AZURE_CLIENT_ID")
    client_secret = graph_config.get("client_secret") or os.getenv("AZURE_CLIENT_SECRET")
    if not tenant_id or not client_id or not client_secret:
        agent.logger.info("Microsoft Graph credentials not configured; skipping setup.")
        return
    if not importlib.util.find_spec("msal"):
        agent.logger.warning("MSAL not installed; skipping Microsoft Graph setup.")
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
        agent.logger.warning("Failed to acquire Microsoft Graph access token.")
        return

    agent.graph_client = httpx.AsyncClient(
        base_url="https://graph.microsoft.com/v1.0",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=graph_config.get("timeout", 10.0),
    )


async def prime_graph_approval_queue(agent: ApprovalWorkflowAgent) -> None:
    if not agent.graph_client:
        return

    graph_config = agent.config.get("graph", {})
    user_id = graph_config.get("user_id") or os.getenv("GRAPH_USER_ID")
    if not user_id:
        agent.logger.info("Graph user_id not configured; skipping approval queue priming.")
        return

    message_limit = graph_config.get("message_limit", 10)
    task_limit = graph_config.get("task_limit", 10)
    approval_messages = await _fetch_graph_messages(agent, user_id, message_limit)
    approval_tasks = await _fetch_graph_tasks(agent, user_id, task_limit)
    agent.approval_event_queue.extend(approval_messages)
    agent.approval_event_queue.extend(approval_tasks)
    agent.logger.info(
        "Primed approval queue with %s Graph messages and %s tasks.",
        len(approval_messages),
        len(approval_tasks),
    )


async def _fetch_graph_messages(
    agent: ApprovalWorkflowAgent, user_id: str, limit: int
) -> list[dict[str, Any]]:
    if not agent.graph_client:
        return []
    response = await agent.graph_client.get(
        f"/users/{user_id}/messages",
        params={"$top": limit, "$search": '"approval"'},
        headers={"ConsistencyLevel": "eventual"},
    )
    response.raise_for_status()
    payload = response.json()
    return [
        {"source": "graph", "type": "message", "payload": item} for item in payload.get("value", [])
    ]


async def _fetch_graph_tasks(
    agent: ApprovalWorkflowAgent, user_id: str, limit: int
) -> list[dict[str, Any]]:
    if not agent.graph_client:
        return []
    graph_config = agent.config.get("graph", {})
    task_list_id = graph_config.get("task_list_id")
    if not task_list_id:
        task_list_id = await _resolve_graph_task_list_id(agent, user_id)
    if not task_list_id:
        return []
    response = await agent.graph_client.get(
        f"/users/{user_id}/todo/lists/{task_list_id}/tasks",
        params={"$top": limit, "$search": '"approval"'},
        headers={"ConsistencyLevel": "eventual"},
    )
    response.raise_for_status()
    payload = response.json()
    return [
        {"source": "graph", "type": "task", "payload": item} for item in payload.get("value", [])
    ]


async def _resolve_graph_task_list_id(agent: ApprovalWorkflowAgent, user_id: str) -> str | None:
    if not agent.graph_client:
        return None
    response = await agent.graph_client.get(f"/users/{user_id}/todo/lists")
    response.raise_for_status()
    payload = response.json()
    for item in payload.get("value", []):
        if "approval" in (item.get("displayName") or "").lower():
            return item.get("id")
    return None
