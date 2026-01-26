from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "analytics-service"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "connector-hub"))
sys.path.insert(0, str(REPO_ROOT / "agents" / "runtime" / "prompts"))

from prompt_registry import list_prompts, load_prompt  # noqa: E402
from job_registry import list_job_manifests, load_job_manifest  # noqa: E402
from sandbox_registry import list_sandbox_configs, load_sandbox_config  # noqa: E402


def test_job_manifests_validate() -> None:
    for manifest in list_job_manifests():
        load_job_manifest(manifest)


def test_prompt_manifests_validate() -> None:
    for prompt in list_prompts():
        load_prompt(prompt)


def test_sandbox_configs_validate() -> None:
    for config in list_sandbox_configs():
        load_sandbox_config(config)
