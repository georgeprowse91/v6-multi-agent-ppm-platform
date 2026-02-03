from __future__ import annotations

import os
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

_DEFAULT_MOUNT_PATH = Path("/mnt/secrets-store")


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
    path = Path(value[len("file:") :])
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _raise_unresolved("file")
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
