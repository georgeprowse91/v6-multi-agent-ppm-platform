from __future__ import annotations

from pathlib import Path

from ops.tools.config_validator import validate_configs


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validate_configs_passes_for_valid_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "ops" / "config"
    schema_dir = tmp_path / "ops" / "schemas"

    _write(
        config_dir / "agents" / "intent-routing.yaml",
        """
version: 1
default_min_confidence: 0.6
fallback_intent: general_query
intents:
  - name: general_query
    min_confidence: 0.0
    routes: []
""".strip(),
    )
    _write(
        schema_dir / "intent-routing.schema.json",
        """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["version", "default_min_confidence", "fallback_intent", "intents"],
  "properties": {
    "version": {"type": "integer"},
    "default_min_confidence": {"type": "number"},
    "fallback_intent": {"type": "string"},
    "intents": {"type": "array"}
  },
  "additionalProperties": false
}
""".strip(),
    )

    issues, skipped = validate_configs(config_dir=config_dir, schema_dir=schema_dir)

    assert issues == []
    assert skipped == []


def test_validate_configs_reports_errors_with_line_numbers(tmp_path: Path) -> None:
    config_dir = tmp_path / "ops" / "config"
    schema_dir = tmp_path / "ops" / "schemas"

    _write(
        config_dir / "agents" / "approval_policies.yaml",
        """
budget_thresholds:
  - 10000
escalation_timeout_hours: 48
risk_thresholds:
  high: 12
  medium: 24
  low: 48
criticality_levels:
  critical: 6
  high: 12
  normal: 24
  low: 48
reminder_before_deadline_hours: 24
default_chain_type: waterfall
digest_interval_minutes: 60
response_time_threshold_hours: 48
""".strip(),
    )
    _write(
        schema_dir / "approval_policies.schema.json",
        """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["default_chain_type"],
  "properties": {
    "default_chain_type": {"type": "string", "enum": ["sequential", "parallel"]}
  },
  "additionalProperties": true
}
""".strip(),
    )

    issues, skipped = validate_configs(config_dir=config_dir, schema_dir=schema_dir)

    assert skipped == []
    assert len(issues) == 1
    assert issues[0].config_path.name == "approval_policies.yaml"
    assert issues[0].line == 14
    assert "default_chain_type" in issues[0].message


def test_validate_configs_skips_files_without_schema(tmp_path: Path) -> None:
    config_dir = tmp_path / "ops" / "config"
    schema_dir = tmp_path / "ops" / "schemas"

    _write(config_dir / "tenants" / "default.yaml", "name: default")

    issues, skipped = validate_configs(config_dir=config_dir, schema_dir=schema_dir)

    assert issues == []
    assert skipped == [config_dir / "tenants" / "default.yaml"]
