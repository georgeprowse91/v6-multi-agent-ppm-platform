"""Sync helpers: HR system sync, training record sync, capacity allocation refresh."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from resource_utils import has_resource_changed

from resource_actions.helpers import (
    apply_training_record,
    index_skills,
    store_canonical_profile,
)

if TYPE_CHECKING:
    from resource_capacity_agent import ResourceCapacityAgent


async def sync_hr_systems(agent: ResourceCapacityAgent) -> None:
    """Sync resource profiles from all configured HR systems."""
    profiles: list[dict[str, Any]] = []
    if agent.graph_client:
        profiles.extend(await fetch_azure_ad_profiles(agent))
    profiles.extend(await fetch_workday_profiles(agent))
    profiles.extend(await fetch_sap_profiles(agent))
    if agent.hr_profile_provider:
        profiles.extend(list(agent.hr_profile_provider()))
    elif agent.config:
        profiles.extend(agent.config.get("hr_profiles", []))

    merged = agent._merge_profiles(profiles)
    active_resource_ids: set[str] = set()
    if not agent.resource_pool:
        for resource in agent.resource_store.list(agent.default_tenant_id):
            resource_id = resource.get("resource_id")
            if resource_id:
                agent.resource_pool[resource_id] = resource
    for profile in merged:
        resource_id = profile.get("employee_id")
        if not resource_id:
            continue
        active_resource_ids.add(resource_id)
        resource_profile = {
            "resource_id": resource_id,
            "name": profile.get("name"),
            "role": profile.get("role"),
            "skills": profile.get("skills", []),
            "location": profile.get("location", "Unknown"),
            "cost_rate": profile.get("cost_rate", 0.0),
            "certifications": profile.get("certifications", []),
            "availability": profile.get("availability", 1.0),
            "status": profile.get("status", "Active"),
            "created_at": profile.get("created_at", datetime.now(timezone.utc).isoformat()),
            "source_system": profile.get("source_system", "unknown"),
        }
        if resource_id not in agent.capacity_calendar:
            calendar_entry = {
                "resource_id": resource_id,
                "available_hours_per_day": agent.default_working_hours_per_day,
                "working_days": agent.default_working_days,
                "planned_leave": [],
                "holidays": [],
            }
            agent.capacity_calendar[resource_id] = calendar_entry
            agent.calendar_store.upsert(agent.default_tenant_id, resource_id, calendar_entry)
            await agent._persist_resource_schedule(
                resource_id,
                calendar_entry,
                tenant_id=agent.default_tenant_id,
                availability=resource_profile.get("availability", 1.0),
            )
        existing = agent.resource_pool.get(resource_id)
        if not existing:
            agent.resource_pool[resource_id] = resource_profile
            await store_canonical_profile(agent, resource_id, profile, resource_profile)
            agent.resource_store.upsert(agent.default_tenant_id, resource_id, resource_profile)
            await agent._publish_resource_event("resource.added", resource_profile)
        else:
            if has_resource_changed(existing, resource_profile):
                agent.resource_pool[resource_id] = resource_profile
                await store_canonical_profile(agent, resource_id, profile, resource_profile)
                agent.resource_store.upsert(agent.default_tenant_id, resource_id, resource_profile)
                await agent._publish_resource_event("resource.updated", resource_profile)
        if profile.get("status") == "Inactive":
            await agent._deactivate_resource(resource_id, reason="hr_status")
    await agent._deactivate_missing_resources(active_resource_ids)
    await index_skills(agent)


async def fetch_azure_ad_profiles(
    agent: ResourceCapacityAgent,
) -> list[dict[str, Any]]:
    """Fetch resource profiles from Azure Active Directory."""
    if not agent.graph_client:
        return []
    profiles: list[dict[str, Any]] = []
    for user in agent.graph_client.list_users():
        user_id = user.get("id")
        if not user_id:
            continue
        skills = agent.graph_client.list_user_skills(user_id)
        availability = 1.0
        try:
            if agent.calendar_service:
                busy_events = agent.calendar_service.get_availability(
                    user_id,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc) + timedelta(days=30),
                )
            else:
                busy_events = agent.graph_client.get_calendar_availability(
                    user_id,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc) + timedelta(days=30),
                )
            busy_count = len([event for event in busy_events if event.get("showAs") != "free"])
            availability = max(0.0, 1.0 - min(busy_count / 20, 1.0))
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            availability = 1.0
        profiles.append(
            {
                "employee_id": user.get("employeeId") or user_id,
                "name": user.get("displayName"),
                "email": user.get("mail"),
                "role": user.get("jobTitle"),
                "department": user.get("department"),
                "skills": [skill for skill in skills if skill],
                "availability": availability,
                "source_system": "azure_ad",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return profiles


async def fetch_workday_profiles(
    agent: ResourceCapacityAgent,
) -> list[dict[str, Any]]:
    """Fetch resource profiles from Workday HRIS connector."""
    try:
        from connectors.sdk.src.base_connector import (
            ConnectorCategory,
            ConnectorConfig,
        )
        from connectors.workday.src.workday_connector import WorkdayConnector
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        return []
    try:
        config = ConnectorConfig(
            connector_id="workday",
            name="Workday",
            category=ConnectorCategory.HRIS,
            enabled=True,
        )
        connector = WorkdayConnector(config)
        profiles = []
        for worker in connector.read("workers") or []:
            profiles.append(
                {
                    "employee_id": worker.get("id"),
                    "name": worker.get("name"),
                    "status": worker.get("status", "Active"),
                    "source_system": "workday",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return profiles
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Workday sync failed", extra={"error": str(exc)})
        return []


async def fetch_sap_profiles(
    agent: ResourceCapacityAgent,
) -> list[dict[str, Any]]:
    """Fetch resource profiles from SAP SuccessFactors connector."""
    try:
        from connectors.sap_successfactors.src.sap_successfactors_connector import (
            SapSuccessFactorsConnector,
        )
        from connectors.sdk.src.base_connector import (
            ConnectorCategory,
            ConnectorConfig,
        )
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        return []
    try:
        config = ConnectorConfig(
            connector_id="sap_successfactors",
            name="SAP SuccessFactors",
            category=ConnectorCategory.HRIS,
            enabled=True,
        )
        connector = SapSuccessFactorsConnector(config)
        profiles = []
        for user in connector.read("users") or []:
            profiles.append(
                {
                    "employee_id": user.get("userId"),
                    "name": (f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()),
                    "status": user.get("status", "Active"),
                    "source_system": "sap_successfactors",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return profiles
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("SAP SuccessFactors sync failed", extra={"error": str(exc)})
        return []


async def sync_training_records(agent: ResourceCapacityAgent) -> None:
    """Sync training records from the configured LMS and update resource skills."""
    if not agent.training_client or not agent.training_client.is_configured():
        return
    resource_ids = list(agent.resource_pool.keys())
    if not resource_ids:
        return
    records = agent.training_client.fetch_training_records(resource_ids)
    for record in records:
        resource_id = record.get("resource_id")
        if not resource_id:
            continue
        agent.training_records[resource_id] = record
        await apply_training_record(agent, resource_id, record)
    await index_skills(agent)


async def refresh_capacity_allocations(agent: ResourceCapacityAgent) -> None:
    """Pull allocations from external PPM connectors and cache them locally."""
    allocations = []
    allocations.extend(await fetch_planview_allocations(agent))
    allocations.extend(await fetch_jira_tempo_allocations(agent))
    for allocation in allocations:
        resource_id = allocation.get("resource_id")
        if not resource_id:
            continue
        if resource_id not in agent.allocations:
            agent.allocations[resource_id] = []
        agent.allocations[resource_id].append(allocation)
        agent.repository.upsert_capacity_allocation(allocation)
        if agent.db_service:
            await agent.db_service.store(
                "capacity_allocations", allocation.get("allocation_id", ""), allocation
            )
        if agent.redis_client:
            allocation_id = allocation.get("allocation_id")
            if allocation_id:
                agent.redis_client.set(
                    f"allocation:{allocation_id}", json.dumps(allocation), ex=3600
                )
            agent.redis_client.rpush(f"resource_allocations:{resource_id}", json.dumps(allocation))


async def fetch_planview_allocations(
    agent: ResourceCapacityAgent,
) -> list[dict[str, Any]]:
    """Fetch resource allocations from Planview PPM connector."""
    try:
        from connectors.planview.src.planview_connector import PlanviewConnector
        from connectors.sdk.src.base_connector import (
            ConnectorCategory,
            ConnectorConfig,
        )
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        return []
    try:
        config = ConnectorConfig(
            connector_id="planview",
            name="Planview",
            category=ConnectorCategory.PPM,
            enabled=True,
        )
        connector = PlanviewConnector(config)
        endpoint = os.getenv("PLANVIEW_CAPACITY_ENDPOINT", "/api/v1/resource-allocations")
        response = connector._request("GET", endpoint)
        data = response.json().get("items", [])
        allocations = []
        for item in data:
            allocations.append(
                {
                    "allocation_id": item.get("id") or f"planview-{uuid.uuid4().hex}",
                    "resource_id": item.get("resourceId"),
                    "project_id": item.get("projectId"),
                    "start_date": item.get("startDate"),
                    "end_date": item.get("endDate"),
                    "allocation_percentage": float(item.get("allocationPercent", 0)),
                    "source_system": "planview",
                    "status": item.get("status", "Active"),
                }
            )
        return allocations
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Planview allocation sync failed", extra={"error": str(exc)})
        return []


async def fetch_jira_tempo_allocations(
    agent: ResourceCapacityAgent,
) -> list[dict[str, Any]]:
    """Fetch worklog allocations from Jira Tempo API."""
    tempo_url = os.getenv("JIRA_TEMPO_API_URL")
    tempo_token = os.getenv("JIRA_TEMPO_API_TOKEN")
    if not tempo_url or not tempo_token:
        return []
    try:
        import requests

        response = requests.get(
            f"{tempo_url}/worklogs",
            headers={"Authorization": f"Bearer {tempo_token}"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json().get("results", [])
        allocations = []
        for item in data:
            allocations.append(
                {
                    "allocation_id": (item.get("tempoWorklogId") or f"tempo-{uuid.uuid4().hex}"),
                    "resource_id": item.get("author", {}).get("accountId"),
                    "project_id": item.get("issue", {}).get("projectId"),
                    "start_date": item.get("startDate"),
                    "end_date": item.get("startDate"),
                    "allocation_percentage": float(item.get("timeSpentSeconds", 0))
                    / 3600
                    / agent.default_working_hours_per_day
                    * 100,
                    "source_system": "jira_tempo",
                    "status": "active",
                }
            )
        return allocations
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Tempo allocation sync failed", extra={"error": str(exc)})
        return []
