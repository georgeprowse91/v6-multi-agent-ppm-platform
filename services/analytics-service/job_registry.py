from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from security.config import load_yaml

JOB_MANIFEST_DIR = Path(__file__).resolve().parent / "jobs" / "manifests"
SCHEMA_PATH = JOB_MANIFEST_DIR.parent / "schema" / "job-manifest.schema.json"


def list_job_manifests() -> list[Path]:
    return sorted(JOB_MANIFEST_DIR.glob("*.yaml"))


def load_job_manifest(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], load_yaml(path))
    schema = cast(dict[str, Any], load_yaml(SCHEMA_PATH))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise ValueError(f"Job manifest validation failed: {formatted}")
    return payload
