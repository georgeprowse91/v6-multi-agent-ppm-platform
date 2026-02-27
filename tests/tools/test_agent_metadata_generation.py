import subprocess
import sys
from pathlib import Path


def test_agent_metadata_generation_check() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "ops/scripts/generate_agent_metadata.py", "--check"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"Metadata generator check failed:\n{result.stdout}\n{result.stderr}"
