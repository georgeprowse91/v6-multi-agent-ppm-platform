from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from schema_registry import compare_schemas, is_bump_sufficient, parse_semver  # noqa: E402
from schema_tool import main  # noqa: E402


def test_compare_schemas_detects_minor_change() -> None:
    old = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    new = {
        "type": "object",
        "properties": {"id": {"type": "string"}, "description": {"type": "string"}},
        "required": ["id"],
    }

    result = compare_schemas(old, new)

    assert result.change_type == "minor"
    assert result.backward_compatible is True
    assert result.forward_compatible is False


def test_parse_semver_requires_three_parts() -> None:
    assert parse_semver("1.2.3") == (1, 2, 3)


def test_bump_sufficiency() -> None:
    assert is_bump_sufficient("patch", "minor") is True
    assert is_bump_sufficient("major", "minor") is False


def test_migration_scaffold_and_dry_run(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "data" / "schemas" / "examples").mkdir(parents=True)
    fixture = repo / "data" / "schemas" / "examples" / "project.json"
    fixture.write_text(json.dumps({"id": "p-1"}))

    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)

    # Reuse real script modules while forcing repo root.
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr("schema_tool.REPO_ROOT", repo)

    rc = main(["migration", "scaffold", "--schema", "project", "--from-version", "1.0.0", "--to-version", "2.0.0"])
    assert rc == 0

    migration_file = repo / "data" / "schemas" / "migrations" / "project" / "1.0.0_to_2.0.0.py"
    assert migration_file.exists()

    rc_dry = main(["migration", "dry-run", "--schema", "project", "--from-version", "1.0.0", "--to-version", "2.0.0"])
    assert rc_dry == 0
