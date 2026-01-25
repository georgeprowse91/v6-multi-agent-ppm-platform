import subprocess
import sys


def test_policy_bundles_validate() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate-policies.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
