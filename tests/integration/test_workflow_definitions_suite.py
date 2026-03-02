from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-service" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_definitions import load_definition  # noqa: E402


def test_load_definition_accepts_valid_yaml(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("""
$schema: "https://json-schema.org/draft/2020-12/schema"
type: object
required: [steps]
properties:
  steps:
    type: array
    minItems: 1
""".strip())
    definition = tmp_path / "valid.workflow.yaml"
    definition.write_text("""
metadata:
  name: Valid
steps:
  - id: step-1
    type: task
    config:
      agent: router
      action: run
""".strip())

    loaded = load_definition(definition, schema)

    assert loaded["steps"][0]["id"] == "step-1"


def test_load_definition_rejects_schema_and_custom_validation_errors(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("""
$schema: "https://json-schema.org/draft/2020-12/schema"
type: object
required: [metadata, steps]
properties:
  metadata:
    type: object
  steps:
    type: array
    minItems: 1
""".strip())

    schema_invalid = tmp_path / "schema-invalid.workflow.yaml"
    schema_invalid.write_text("steps: []")
    with pytest.raises(ValueError, match="Workflow definition invalid"):
        load_definition(schema_invalid, schema)

    custom_invalid = tmp_path / "custom-invalid.workflow.yaml"
    custom_invalid.write_text("""
metadata:
  name: Broken
steps:
  - id: a
    type: task
    config:
      agent: one
      action: run
    next: b
  - id: b
    type: task
    config: {}
""".strip())

    with pytest.raises(ValueError, match="requires agent/action"):
        load_definition(custom_invalid, schema)
