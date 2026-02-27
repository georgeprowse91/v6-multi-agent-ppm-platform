import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))

from validate_demo_fixtures import validate_demo_fixtures  # noqa: E402


def test_demo_fixtures_present_and_valid() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    present, expected = validate_demo_fixtures(repo_root)
    assert present == expected == 25
