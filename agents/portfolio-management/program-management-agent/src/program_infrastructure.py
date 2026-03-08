"""
Infrastructure helpers for the Program Management Agent.

Contains initialization routines (Cosmos, ML, LLM, integrations, Service Bus),
external data ingestion, ML health prediction, narrative generation, and
event-handling logic. These are called as methods on the agent instance but
the implementations live here to keep the main class file small.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm.client import LLMGateway

if TYPE_CHECKING:
    from program_management_agent import ProgramManagementAgent


# ------------------------------------------------------------------
# Initialization helpers
# ------------------------------------------------------------------


async def initialize_cosmos(agent: ProgramManagementAgent) -> None:
    if agent.dependency_container and agent.mapping_container:
        return
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    if not endpoint or not key:
        return
    from azure.cosmos import PartitionKey
    from azure.cosmos.aio import CosmosClient

    agent.cosmos_client = CosmosClient(endpoint, credential=key)
    database_name = agent.config.get("cosmos_database", "ppm-programs") if agent.config else None
    agent.cosmos_database = await agent.cosmos_client.create_database_if_not_exists(
        id=database_name or "ppm-programs"
    )
    indexing_policy = {
        "indexingMode": "consistent",
        "automatic": True,
        "includedPaths": [
            {"path": "/program_id/?"},
            {"path": "/tenant_id/?"},
            {"path": "/dependencies/*"},
            {"path": "/*"},
        ],
        "excludedPaths": [{"path": '/"_etag"/?'}],
    }
    agent.dependency_container = await agent.cosmos_database.create_container_if_not_exists(
        id="program_dependencies",
        partition_key=PartitionKey(path="/program_id"),
        indexing_policy=indexing_policy,
    )
    agent.mapping_container = await agent.cosmos_database.create_container_if_not_exists(
        id="program_mappings",
        partition_key=PartitionKey(path="/system"),
    )


async def initialize_ml(agent: ProgramManagementAgent) -> None:
    if agent.ml_workspace or agent.health_model:
        return
    ml_config = agent.config.get("ml_config", {}) if agent.config else {}
    if not ml_config.get("enabled"):
        return
    from azureml.core import Model, Workspace

    if ml_config.get("workspace_config"):
        agent.ml_workspace = Workspace.from_config(path=ml_config["workspace_config"])
    else:
        agent.ml_workspace = Workspace(
            subscription_id=ml_config.get("subscription_id"),
            resource_group=ml_config.get("resource_group"),
            workspace_name=ml_config.get("workspace_name"),
        )
    model_name = ml_config.get("model_name", "program_health_model")
    try:
        agent.health_model = Model(agent.ml_workspace, name=model_name)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        await train_health_model(agent, model_name=model_name)


async def initialize_llm(agent: ProgramManagementAgent) -> None:
    if agent.llm_client is None:
        llm_config = agent.config.get("llm_config", {}) if agent.config else {}
        provider = llm_config.get("provider") or (
            "azure_openai" if os.getenv("AZURE_OPENAI_ENDPOINT") else None
        )
        agent.llm_client = LLMGateway(provider=provider, config=llm_config)


async def initialize_integrations(agent: ProgramManagementAgent) -> None:
    if agent.planview_connector is None:
        planview_config = agent.config.get("planview_config") if agent.config else None
        if planview_config:
            from connectors.planview.src.planview_connector import PlanviewConnector
            from connectors.sdk.src.base_connector import ConnectorConfig

            agent.planview_connector = PlanviewConnector(ConnectorConfig.from_dict(planview_config))
    if agent.clarity_connector is None:
        clarity_config = agent.config.get("clarity_config") if agent.config else None
        if clarity_config:
            from connectors.clarity.src.clarity_connector import ClarityConnector
            from connectors.sdk.src.base_connector import ConnectorConfig

            agent.clarity_connector = ClarityConnector(ConnectorConfig.from_dict(clarity_config))
    agent.jira_base_url = agent.jira_base_url or os.getenv("JIRA_BASE_URL")
    agent.jira_api_token = agent.jira_api_token or os.getenv("JIRA_API_TOKEN")
    agent.azure_devops_org_url = agent.azure_devops_org_url or os.getenv("AZDO_ORG_URL")
    agent.azure_devops_pat = agent.azure_devops_pat or os.getenv("AZDO_PAT")


async def subscribe_to_program_events(agent: ProgramManagementAgent) -> None:
    if agent.service_bus_client:
        return
    connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    topic_name = os.getenv("SERVICE_BUS_TOPIC")
    subscription_name = os.getenv("SERVICE_BUS_SUBSCRIPTION")
    if not connection_string or not topic_name or not subscription_name:
        return
    from azure.servicebus.aio import ServiceBusClient

    agent.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
    agent.service_bus_receiver = agent.service_bus_client.get_subscription_receiver(
        topic_name=topic_name, subscription_name=subscription_name
    )
    agent.service_bus_task = asyncio.create_task(listen_to_program_events(agent))


async def listen_to_program_events(agent: ProgramManagementAgent) -> None:
    if not agent.service_bus_receiver:
        return
    async with agent.service_bus_receiver:
        async for message in agent.service_bus_receiver:
            await handle_program_event(agent, message)
            await agent.service_bus_receiver.complete_message(message)


async def handle_program_event(agent: ProgramManagementAgent, message: Any) -> None:
    payload = getattr(message, "body", None)
    if hasattr(payload, "__iter__"):
        payload = "".join([part.decode("utf-8") for part in payload])
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}
    if not isinstance(payload, dict):
        return
    program_id = payload.get("program_id")
    tenant_id = payload.get("tenant_id", "unknown")
    if not program_id:
        return
    program = agent.program_store.get(tenant_id, program_id)
    if not program:
        return
    updates = payload.get("updates", {})
    program.update(updates)
    agent.program_store.upsert(tenant_id, program_id, program)
    if agent.db_service:
        await agent.db_service.store("programs", program_id, program)
    if updates.get("dependencies"):
        await agent._update_dependency_graph(
            program_id, updates["dependencies"], tenant_id=tenant_id
        )


# ------------------------------------------------------------------
# ML / health prediction helpers
# ------------------------------------------------------------------


async def predict_program_health(
    agent: ProgramManagementAgent, features: dict[str, float]
) -> dict[str, Any]:
    if agent.health_model and hasattr(agent.health_model, "predict"):
        score = agent.health_model.predict([features])[0]
        return {"score": score, "model": getattr(agent.health_model, "name", "custom")}
    score = 1 - (
        0.35 * features.get("schedule_variance", 0)
        + 0.35 * features.get("cost_variance", 0)
        + 0.2 * features.get("risk_indicator", 0)
        + 0.1 * (1 - features.get("external_health", 0))
    )
    return {"score": max(min(score, 1.0), 0.0), "model": "baseline"}


async def compute_benefit_realization_metrics(
    agent: ProgramManagementAgent, program_id: str, project_ids: list[str]
) -> dict[str, Any]:
    if agent.synapse_client:
        return await agent.synapse_client.fetch_benefit_metrics(program_id)
    return {
        "realization_rate": 0.65,
        "benefits_realized": 125000,
        "benefits_target": 190000,
        "projects": project_ids,
    }


async def collect_external_health_signals(
    agent: ProgramManagementAgent, program_id: str, project_ids: list[str]
) -> dict[str, Any]:
    external = await ingest_external_program_data(agent)
    projects = external.get("projects", {})
    health_values: list[float] = []
    dependency_load = 0.0
    for project_id in project_ids:
        project = projects.get(project_id, {})
        if project:
            health_values.append(project.get("health_score", 0.8))
            dependency_load += project.get("dependency_count", 0)
    health_index = sum(health_values) / len(health_values) if health_values else 0.8
    return {
        "program_id": program_id,
        "health_index": health_index,
        "dependency_load": dependency_load,
        "sources": ["planview", "clarity"],
    }


async def generate_program_narrative(
    agent: ProgramManagementAgent,
    program: dict[str, Any],
    *,
    schedule_health: float,
    budget_health: float,
    risk_health: float,
    quality_health: float,
    resource_health: float,
    benefit_metrics: dict[str, Any],
) -> str:
    if not agent.llm_client:
        return "Narrative generation not configured."
    system_prompt = "You are a program management assistant summarizing program health."
    user_prompt = (
        f"Program: {program.get('name')}\n"
        f"Schedule health: {schedule_health:.2f}\n"
        f"Cost health: {budget_health:.2f}\n"
        f"Risk health: {risk_health:.2f}\n"
        f"Quality health: {quality_health:.2f}\n"
        f"Resource health: {resource_health:.2f}\n"
        f"Benefit realization rate: {benefit_metrics.get('realization_rate', 0):.2f}\n"
        "Provide a concise narrative summary of program status."
    )
    response = await agent.llm_client.complete(system_prompt, user_prompt)
    return response.content


# ------------------------------------------------------------------
# External data ingestion
# ------------------------------------------------------------------


async def ingest_external_program_data(agent: ProgramManagementAgent) -> dict[str, Any]:
    data: dict[str, Any] = {"projects": {}, "benefits": {}}
    if agent.planview_connector and agent.planview_connector.authenticate():
        response = agent.planview_connector.read("projects")
        data["projects"].update({proj["id"]: proj for proj in response})
        health = agent.planview_connector.read("program_health")
        for entry in health:
            data["projects"].setdefault(entry["id"], {}).update(entry)
    if agent.clarity_connector and agent.clarity_connector.authenticate():
        response = agent.clarity_connector.read("projects")
        data["projects"].update({proj["id"]: proj for proj in response})
        health = agent.clarity_connector.read("program_health")
        for entry in health:
            data["projects"].setdefault(entry["id"], {}).update(entry)
    for project_id, project in data["projects"].items():
        benefits = project.get("benefits") or {}
        total_benefits = benefits.get("total_benefits", project.get("benefit", 0))
        total_costs = project.get("investment", project.get("cost", 0))
        if total_benefits or total_costs:
            data["benefits"][project_id] = {
                "total_benefits": total_benefits,
                "total_costs": total_costs,
                "benefit_breakdown": benefits,
            }
    return data


# ------------------------------------------------------------------
# Training helper
# ------------------------------------------------------------------


async def train_health_model(agent: ProgramManagementAgent, model_name: str) -> None:
    if not agent.ml_workspace:
        return
    from azureml.core import Model

    model_path = Path(agent.config.get("ml_model_path", "data/program_health_model.json"))
    training_data = await prepare_health_training_data(agent)
    model_payload = {
        "weights": agent.health_score_weights,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_data": training_data,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model_payload))
    agent.health_model = Model.register(
        workspace=agent.ml_workspace,
        model_path=str(model_path),
        model_name=model_name,
    )


async def prepare_health_training_data(agent: ProgramManagementAgent) -> dict[str, Any]:
    external = await ingest_external_program_data(agent)
    projects = external.get("projects", {})
    signals = []
    for project_id, payload in projects.items():
        signals.append(
            {
                "project_id": project_id,
                "schedule_variance": payload.get("schedule_variance", 0.1),
                "cost_variance": payload.get("cost_variance", 0.1),
                "risk_indicator": payload.get("risk_indicator", 0.2),
                "health_score": payload.get("health_score", 0.8),
            }
        )
    return {"samples": signals, "source": "planview/clarity"}
