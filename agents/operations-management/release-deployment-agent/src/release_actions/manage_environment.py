"""Action handler: manage_environment and check_configuration_drift."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from release_utils import (
    check_azure_policy_compliance,
    generate_environment_id,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def manage_environment(
    agent: ReleaseAgentProtocol, environment_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Manage environment configuration and status.

    Returns environment ID and details.
    """
    agent.logger.info("Managing environment: %s", environment_data.get("name"))

    # Generate environment ID
    env_id = await generate_environment_id()

    # Create environment record
    environment = {
        "environment_id": env_id,
        "name": environment_data.get("name"),
        "type": environment_data.get("type"),
        "configuration": environment_data.get("configuration", {}),
        "version": environment_data.get("version"),
        "status": environment_data.get("status", "Available"),
        "owner": environment_data.get("owner"),
        "reserved_by": None,
        "reserved_until": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store environment
    agent.environments_inventory[env_id] = environment

    # Persist to database
    await agent.db_service.store("environments", env_id, environment)

    return {
        "environment_id": env_id,
        "name": environment["name"],
        "type": environment["type"],
        "status": environment["status"],
        "configuration": environment["configuration"],
    }


async def check_configuration_drift(
    agent: ReleaseAgentProtocol, environment_id: str
) -> dict[str, Any]:
    """
    Detect configuration drift between environments.

    Returns drift analysis.
    """
    agent.logger.info("Checking configuration drift for environment: %s", environment_id)

    environment = agent.environments_inventory.get(environment_id)
    if not environment:
        raise ValueError(f"Environment not found: {environment_id}")

    # Get baseline configuration
    baseline_config = await _get_baseline_configuration(agent, environment.get("type"))

    policy_results = await check_azure_policy_compliance(agent, environment)
    drift_items = await _compare_configurations(
        environment.get("configuration", {}), baseline_config
    )
    policy_drift_items = policy_results.get("drift_items", [])

    combined_drift = drift_items + policy_drift_items
    drift_detected = len(combined_drift) > 0

    return {
        "environment_id": environment_id,
        "drift_detected": drift_detected,
        "drift_items": combined_drift,
        "drift_count": len(combined_drift),
        "baseline_version": baseline_config.get("version"),
        "policy_compliance": policy_results.get("compliance_state"),
        "recommendations": await _generate_drift_recommendations(combined_drift),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _get_baseline_configuration(
    agent: ReleaseAgentProtocol, env_type: str
) -> dict[str, Any]:
    """Get baseline configuration for environment type."""
    if agent.configuration_management_client:
        if hasattr(agent.configuration_management_client, "get_baseline"):
            response = await agent.configuration_management_client.get_baseline(env_type)
            return cast(dict[str, Any], response)
        if hasattr(agent.configuration_management_client, "process"):
            response = await agent.configuration_management_client.process(
                {"action": "get_baseline_configuration", "environment_type": env_type}
            )
            return cast(dict[str, Any], response)
    return {"version": "1.0", "settings": {}, "source": "default"}


async def _compare_configurations(
    current_config: dict[str, Any], baseline_config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare configurations to detect drift."""
    drift = []
    baseline_settings = baseline_config.get("settings", {})
    for key, baseline_value in baseline_settings.items():
        current_value = current_config.get(key)
        if current_value != baseline_value:
            drift.append(
                {
                    "setting": key,
                    "expected": baseline_value,
                    "actual": current_value,
                }
            )
    return drift


async def _generate_drift_recommendations(drift_items: list[dict[str, Any]]) -> list[str]:
    """Generate recommendations for drift remediation."""
    if not drift_items:
        return ["No drift detected - configuration is compliant"]
    return ["Review and align configuration with baseline"]
