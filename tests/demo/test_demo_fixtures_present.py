from pathlib import Path

from scripts.validate_demo_fixtures import validate_demo_fixtures


def test_demo_fixtures_present_and_valid() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    present, expected = validate_demo_fixtures(repo_root)
    assert present == expected == 25
