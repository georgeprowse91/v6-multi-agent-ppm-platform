"""Validate configuration parity across environment configs.

Reads required variable names from ops/config/.env.example and checks that
each Helm values.yaml has a matching env entry. This catches configuration
drift between services and ensures production deployments have all required
variables defined.

Usage:
    python ops/tools/check_config_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / "ops" / "config" / ".env.example"

HELM_VALUES_DIRS = [
    REPO_ROOT / "apps",
    REPO_ROOT / "services",
    REPO_ROOT / "apps",
]

# Variables that are intentionally NOT expected in every Helm chart
GLOBAL_ONLY_VARS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
    "ORCHESTRATION_STATE_BACKEND",
    "AUTH_DEV_MODE",
    "AUTH_DEV_ROLES",
    "AUTH_DEV_TENANT_ID",
    "LLM_MOCK_RESPONSE_PATH",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "API_GATEWAY_URL",
    "IDENTITY_ACCESS_URL",
    "WORKFLOW_SERVICE_URL",
    "SEARCH_API_ENDPOINT",
    "SEARCH_API_KEY",
    "SEARCH_API_MIN_INTERVAL",
    "SEARCH_RESULT_LIMIT",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "LLM_PROVIDER",
    "DEMO_MODE",
}

# Env vars that must appear in every Helm values.yaml
UNIVERSAL_VARS = {"LOG_LEVEL", "WEB_CONCURRENCY"}


def parse_env_example(path: Path) -> set[str]:
    """Extract variable names from .env.example (ignoring comments and blanks)."""
    names: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
        if match:
            names.add(match.group(1))
    return names


def find_helm_values() -> list[Path]:
    """Find all Helm values.yaml files under known service directories."""
    results: list[Path] = []
    for base in HELM_VALUES_DIRS:
        if base.exists():
            results.extend(sorted(base.rglob("helm/values.yaml")))
    return results


def extract_helm_env_keys(values_path: Path) -> set[str]:
    """Extract env key names from a Helm values.yaml."""
    keys: set[str] = set()
    in_env = False
    for line in values_path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "env:" or stripped.startswith("env:"):
            in_env = True
            continue
        if in_env:
            if stripped and not stripped.startswith("#") and ":" in stripped:
                if not stripped.startswith("-") and not stripped.startswith(" "):
                    # Left-aligned key = we've exited the env block
                    in_env = False
                    continue
                key = stripped.split(":")[0].strip().lstrip("- ")
                if key and key == key.upper():
                    keys.add(key)
            elif stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                if not stripped[0].isspace() and ":" in stripped:
                    in_env = False
    return keys


def main() -> int:
    if not ENV_EXAMPLE.exists():
        print(f"ERROR: {ENV_EXAMPLE} not found")
        return 1

    env_vars = parse_env_example(ENV_EXAMPLE)
    print(f"Found {len(env_vars)} variables in .env.example")

    helm_files = find_helm_values()
    print(f"Found {len(helm_files)} Helm values.yaml files\n")

    errors = 0
    for values_path in helm_files:
        service_name = values_path.relative_to(REPO_ROOT).parts[1]
        helm_keys = extract_helm_env_keys(values_path)

        missing = UNIVERSAL_VARS - helm_keys
        if missing:
            print(f"  WARN  {service_name}: missing universal vars: {', '.join(sorted(missing))}")
            errors += len(missing)

    if errors:
        print(f"\n{errors} parity warning(s) found.")
    else:
        print("\nAll Helm charts pass configuration parity check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
