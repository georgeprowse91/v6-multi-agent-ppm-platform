import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "analytics-service"))
sys.path.insert(0, str(REPO_ROOT / "integrations" / "apps" / "connector-hub"))
from job_registry import list_job_manifests, load_job_manifest  # noqa: E402
from sandbox_registry import list_sandbox_configs, load_sandbox_config  # noqa: E402

from prompt_registry import PromptRegistry  # noqa: E402


def test_job_manifests_validate() -> None:
    for manifest in list_job_manifests():
        load_job_manifest(manifest)


def test_prompt_manifests_validate() -> None:
    registry = PromptRegistry(prompts_root=REPO_ROOT / "prompts")
    for agent_dir in (REPO_ROOT / "prompts").iterdir():
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        version = registry.latest_version(agent_id)
        record = registry.get_prompt_record(agent_id, version)
        assert record.content


def test_sandbox_configs_validate() -> None:
    for config in list_sandbox_configs():
        load_sandbox_config(config)


def test_new_schemas_validate() -> None:
    schema_dir = REPO_ROOT / "data" / "schemas"
    schema_names = [
        "demand.schema.json",
        "resource.schema.json",
        "roi.schema.json",
        "agent_config.schema.json",
    ]

    for schema_name in schema_names:
        schema = json.loads((schema_dir / schema_name).read_text())
        Draft202012Validator.check_schema(schema)


def test_schema_enum_consistency() -> None:
    schema_dir = REPO_ROOT / "data" / "schemas"
    classification_enum = ["public", "internal", "confidential", "restricted"]
    classification_schemas = [
        "audit-event.schema.json",
        "budget.schema.json",
        "document.schema.json",
        "issue.schema.json",
        "portfolio.schema.json",
        "program.schema.json",
        "project.schema.json",
        "risk.schema.json",
        "vendor.schema.json",
        "work-item.schema.json",
    ]
    # Minimum required status values for each schema (actual enums may be supersets)
    status_enums = {
        "budget.schema.json": ["draft", "approved", "committed"],
        "document.schema.json": ["draft", "review", "approved", "archived"],
        "issue.schema.json": ["open", "in_progress", "resolved", "closed"],
        "portfolio.schema.json": ["planning", "active", "archived"],
        "program.schema.json": ["planning", "active", "closed"],
        "project.schema.json": ["initiated", "planning", "execution", "monitoring", "closed"],
        "resource.schema.json": ["active", "inactive", "on_leave"],
        "risk.schema.json": ["open", "mitigated", "closed"],
        "vendor.schema.json": ["active", "inactive", "pending"],
        "work-item.schema.json": ["todo", "in_progress", "done", "blocked"],
    }

    for schema_name in classification_schemas:
        schema = json.loads((schema_dir / schema_name).read_text())
        properties = schema["properties"]
        assert properties["classification"]["enum"] == classification_enum

    for schema_name, expected_status in status_enums.items():
        schema = json.loads((schema_dir / schema_name).read_text())
        properties = schema["properties"]
        actual_status = properties["status"]["enum"]
        assert set(expected_status).issubset(set(actual_status)), (
            f"{schema_name}: expected status values {expected_status!r} not all present in {actual_status!r}"
        )


def test_project_schema_new_optional_fields() -> None:
    schema_dir = REPO_ROOT / "data" / "schemas"
    schema = json.loads((schema_dir / "project.schema.json").read_text())
    properties = schema["properties"]

    assert "benefits_realisation_plan" in properties
    assert properties["benefits_realisation_plan"]["type"] == "string"

    assert "regulatory_category" in properties
    assert properties["regulatory_category"]["type"] == "string"
    assert properties["regulatory_category"]["enum"] == ["low", "medium", "high"]

    # Optional fields should not be required
    assert "benefits_realisation_plan" not in schema["required"]
    assert "regulatory_category" not in schema["required"]
