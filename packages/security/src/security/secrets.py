from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

_DEFAULT_MOUNT_PATH = Path("/mnt/secrets-store")
_FILE_ROOT_ENV_VAR = "SECRETS_FILE_ROOT"
_ALLOW_ABSOLUTE_FILE_PATHS_ENV_VAR = "SECRETS_ALLOW_ABSOLUTE_PATHS"
_ALLOWED_SECRET_FILE_EXTENSIONS = {"", ".txt", ".secret", ".pem", ".key", ".crt", ".json"}

logger = logging.getLogger("security-secrets")


class SecretResolutionError(ValueError):
    pass


def _raise_unresolved(reference_type: str) -> NoReturn:
    raise SecretResolutionError(f"secret reference could not be resolved: {reference_type}")


def _resolve_env_reference(value: str) -> str:
    env_var = value[len("env:") :]
    resolved = os.getenv(env_var)
    if resolved is None:
        _raise_unresolved("env")
    return resolved


def _resolve_braced_env(value: str) -> str:
    env_var = value[2:-1]
    resolved = os.getenv(env_var)
    if resolved is None:
        _raise_unresolved("env")
    return resolved


def _resolve_file_reference(value: str) -> str:
    raw_path = value[len("file:") :]
    candidate_path = Path(raw_path)

    if not raw_path.strip():
        logger.warning("secret_file_reference_rejected", extra={"reason": "empty_path", "scheme": "file"})
        _raise_unresolved("file")

    if any(part == ".." for part in candidate_path.parts):
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "path_traversal", "scheme": "file", "path": raw_path},
        )
        _raise_unresolved("file")

    allow_absolute_paths = os.getenv(_ALLOW_ABSOLUTE_FILE_PATHS_ENV_VAR, "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if candidate_path.is_absolute() and not allow_absolute_paths:
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "absolute_path_not_allowed", "scheme": "file", "path": raw_path},
        )
        _raise_unresolved("file")

    configured_root = Path(os.getenv(_FILE_ROOT_ENV_VAR, str(_DEFAULT_MOUNT_PATH)))
    try:
        root = configured_root.resolve(strict=True)
    except FileNotFoundError:
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "root_missing", "scheme": "file", "root": str(configured_root)},
        )
        _raise_unresolved("file")

    unresolved_candidate = candidate_path if candidate_path.is_absolute() else root / candidate_path

    try:
        candidate = unresolved_candidate.resolve(strict=True)
    except FileNotFoundError:
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "path_missing", "scheme": "file", "path": raw_path},
        )
        _raise_unresolved("file")

    try:
        within_root = candidate.is_relative_to(root)
    except AttributeError:
        within_root = root == candidate or root in candidate.parents
    if not within_root:
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "path_outside_root", "scheme": "file", "path": raw_path, "root": str(root)},
        )
        _raise_unresolved("file")

    if candidate.suffix.lower() not in _ALLOWED_SECRET_FILE_EXTENSIONS:
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "extension_not_allowed", "scheme": "file", "path": raw_path},
        )
        _raise_unresolved("file")

    if not candidate.is_file():
        logger.warning(
            "secret_file_reference_rejected",
            extra={"reason": "not_a_regular_file", "scheme": "file", "path": raw_path},
        )
        _raise_unresolved("file")

    content = candidate.read_text(encoding="utf-8")
    return content.rstrip("\n")


def _keyvault_secret_name_from_uri(secret_uri: str) -> str | None:
    parsed = urlparse(secret_uri)
    if not parsed.scheme or not parsed.netloc:
        return None
    if not parsed.path:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    if parts[0] != "secrets":
        return None
    return parts[1]


def _resolve_keyvault_reference(value: str) -> str | None:
    if value.startswith("@Microsoft.KeyVault(SecretUri=") and value.endswith(")"):
        secret_uri = value[len("@Microsoft.KeyVault(SecretUri=") : -1]
        secret_name = _keyvault_secret_name_from_uri(secret_uri)
        if not secret_name:
            _raise_unresolved("keyvault")
        return _resolve_file_reference(f"file:{_DEFAULT_MOUNT_PATH / secret_name}")
    if value.startswith("keyvault://"):
        parsed = urlparse(value)
        secret_path = parsed.path.lstrip("/")
        if not secret_path:
            _raise_unresolved("keyvault")
        secret_name = secret_path.split("/")[0]
        return _resolve_file_reference(f"file:{_DEFAULT_MOUNT_PATH / secret_name}")
    return None


def resolve_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    if value.startswith("env:"):
        return _resolve_env_reference(value)

    if value.startswith("${") and value.endswith("}"):
        return _resolve_braced_env(value)

    if value.startswith("file:"):
        return _resolve_file_reference(value)

    keyvault = _resolve_keyvault_reference(value)
    if keyvault is not None:
        return keyvault

    return value
