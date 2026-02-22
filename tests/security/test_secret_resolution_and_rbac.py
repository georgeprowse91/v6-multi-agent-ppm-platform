from pathlib import Path

from security.iam import map_groups_to_roles
from security.secrets import resolve_secret


def test_resolve_secret_env(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "s3cr3t")
    assert resolve_secret("env:TEST_SECRET") == "s3cr3t"


def test_resolve_secret_file(tmp_path: Path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("file-secret\n")
    assert resolve_secret(f"file:{secret_file}") == "file-secret"


def test_rbac_mapping(tmp_path: Path, monkeypatch):
    mapping = tmp_path / "role-mapping.yaml"
    mapping.write_text("""
groups:
  group-1:
    - portfolio_admin
    - compliance_viewer
roles: []
""")
    monkeypatch.setenv("IAM_ROLE_MAPPING_PATH", str(mapping))
    roles = map_groups_to_roles({"groups": ["group-1"]})
    assert "portfolio_admin" in roles
    assert "compliance_viewer" in roles
