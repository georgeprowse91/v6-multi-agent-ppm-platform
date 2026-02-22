from __future__ import annotations

import re
from pathlib import Path

import pytest
from security.secrets import SecretResolutionError, resolve_secret


def test_resolve_env_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOO", "bar")
    assert resolve_secret("env:FOO") == "bar"
    assert resolve_secret("${FOO}") == "bar"


def test_resolve_file_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret_path = tmp_path / "secret"
    secret_path.write_text("super-secret\n", encoding="utf-8")
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(tmp_path))
    assert resolve_secret("file:secret") == "super-secret"


def test_resolve_file_reference_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(tmp_path))
    with pytest.raises(SecretResolutionError):
        resolve_secret("file:../secret")


def test_resolve_file_reference_rejects_absolute_paths_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_path = tmp_path / "secret"
    secret_path.write_text("super-secret\n", encoding="utf-8")
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(tmp_path))
    monkeypatch.delenv("SECRETS_ALLOW_ABSOLUTE_PATHS", raising=False)
    with pytest.raises(SecretResolutionError):
        resolve_secret(f"file:{secret_path}")


def test_resolve_file_reference_rejects_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret").write_text("escape", encoding="utf-8")
    (root / "link").symlink_to(outside / "secret")
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(root))

    with pytest.raises(SecretResolutionError):
        resolve_secret("file:link")


def test_resolve_file_reference_rejects_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(tmp_path))
    with pytest.raises(SecretResolutionError):
        resolve_secret("file:not-found")


def test_resolve_file_reference_rejects_non_file_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    non_file = tmp_path / "dir"
    non_file.mkdir()
    monkeypatch.setenv("SECRETS_FILE_ROOT", str(tmp_path))
    with pytest.raises(SecretResolutionError):
        resolve_secret("file:dir")


def test_missing_reference_is_non_leaky() -> None:
    with pytest.raises(SecretResolutionError) as exc:
        resolve_secret("env:NOT_SET")
    assert "secret reference could not be resolved" in str(exc.value)
    assert "NOT_SET" not in str(exc.value)


def test_prod_configs_contain_only_secret_references() -> None:
    targets = [
        Path("config/environments/prod.yaml"),
        Path("infra/kubernetes/deployment.yaml"),
        Path("infra/kubernetes/secret-provider-class.yaml"),
        Path("infra/kubernetes/service-account.yaml"),
    ]
    sensitive_markers = re.compile(
        r"(api[_-]?key|token|password|secret|connection[_-]?string)",
        re.IGNORECASE,
    )
    allowlist_keys = {
        "secretName",
        "secretProviderClass",
        "secretObjects",
        "objectName",
        "key",
        "clientID",
        "tenantId",
        "name",
        "labels",
        "annotations",
    }
    allowed_value_prefixes = ("file:", "env:", "${", "{{", "keyvault://")

    violations: list[str] = []

    for target in targets:
        content = target.read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = re.match(r"^\s*-?\s*(?P<key>[A-Za-z0-9_.-]+)\s*:\s*(?P<value>.+)$", line)
            if not match:
                continue
            key = match.group("key")
            value = match.group("value").strip().strip('"').strip("'")
            if key in allowlist_keys:
                continue
            if not sensitive_markers.search(key):
                continue
            if value.startswith(allowed_value_prefixes):
                continue
            violations.append(f"{target}:{line_number}:{line}")

    assert not violations, "Possible plaintext secrets detected:\n" + "\n".join(violations)
