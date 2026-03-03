"""
Action handlers for data validation and mapping definition.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sync_utils import validate_against_schema

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_validate_data(
    agent: DataSyncAgent, entity_type: str, data: dict[str, Any]
) -> dict[str, Any]:
    """
    Validate data quality.

    Returns validation results.
    """
    agent.logger.info("Validating %s data", entity_type)

    errors = []
    warnings = []

    # Get validation rules for entity type
    validation_rules = await get_validation_rules(agent, entity_type)

    # Apply validation rules
    for rule in validation_rules:
        result = await apply_validation_rule(agent, data, rule)
        if not result.get("valid"):
            if result.get("severity") == "error":
                errors.append(result.get("message"))
            else:
                warnings.append(result.get("message"))

    schema = agent.schema_registry.get(entity_type)
    if schema:
        schema_errors = validate_against_schema(schema, data)
        errors.extend(schema_errors)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


async def handle_define_mapping(
    agent: DataSyncAgent, mapping_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Define data mapping rule.

    Returns mapping rule ID.
    """
    agent.logger.info("Defining mapping: %s", mapping_config.get("name"))

    # Generate mapping ID
    mapping_id = await agent._generate_mapping_id()

    # Create mapping rule
    mapping_rule = {
        "mapping_id": mapping_id,
        "name": mapping_config.get("name"),
        "source_system": mapping_config.get("source_system"),
        "target_entity": mapping_config.get("target_entity"),
        "field_mappings": mapping_config.get("field_mappings", {}),
        "transformations": mapping_config.get("transformations", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store mapping rule
    agent.mapping_rules[mapping_id] = mapping_rule
    agent.transformation_rules.append(
        {
            "entity_type": mapping_rule.get("target_entity"),
            "source_system": mapping_rule.get("source_system"),
            "field_mappings": mapping_rule.get("field_mappings"),
            "transformations": mapping_rule.get("transformations", []),
        }
    )

    await agent._store_record("mapping_rules", mapping_id, mapping_rule)

    return {
        "mapping_id": mapping_id,
        "name": mapping_rule["name"],
        "field_count": len(mapping_rule["field_mappings"]),
    }


async def get_validation_rules(
    agent: DataSyncAgent, entity_type: str
) -> list[dict[str, Any]]:
    """Get validation rules for entity type."""
    if entity_type in agent.validation_rules:
        return agent.validation_rules[entity_type]
    return agent.validation_rules.get(
        "default",
        [
            {"field": "id", "required": True, "severity": "error"},
            {"field": "name", "required": True, "severity": "error"},
        ],
    )


async def apply_validation_rule(
    agent: DataSyncAgent, data: dict[str, Any], rule: dict[str, Any]
) -> dict[str, Any]:
    """Apply validation rule."""
    field = rule.get("field")
    required = rule.get("required", False)
    minimum = rule.get("min")
    maximum = rule.get("max")
    reference = rule.get("reference")

    if required and not data.get(field):  # type: ignore
        return {
            "valid": False,
            "severity": rule.get("severity", "error"),
            "message": f"Required field '{field}' is missing",
        }

    if field and field in data and isinstance(data.get(field), (int, float)):
        value = data.get(field)
        if minimum is not None and value < minimum:
            return {
                "valid": False,
                "severity": rule.get("severity", "error"),
                "message": f"Field '{field}' is below minimum {minimum}",
            }
        if maximum is not None and value > maximum:
            return {
                "valid": False,
                "severity": rule.get("severity", "error"),
                "message": f"Field '{field}' exceeds maximum {maximum}",
            }

    if reference and field:
        referenced_id = data.get(field)
        if referenced_id and not agent.master_records.get(referenced_id):
            return {
                "valid": False,
                "severity": rule.get("severity", "warning"),
                "message": f"Referential integrity check failed for '{field}'",
            }

    return {"valid": True}
