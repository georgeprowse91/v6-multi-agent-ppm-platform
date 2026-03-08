from __future__ import annotations

from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from security.keyvault import KeyVaultClient, KeyVaultConfig, KeyVaultUnavailableError
from security.secrets import resolve_secret as _resolve_secret

__all__ = ["resolve_secret", "fetch_keyvault_secret"]


def resolve_secret(value: Optional[str]) -> Optional[str]:
    return _resolve_secret(value)


def fetch_keyvault_secret(keyvault_url: Optional[str], secret_name: Optional[str]) -> Optional[str]:
    if not keyvault_url or not secret_name:
        return None
    try:
        client = KeyVaultClient(KeyVaultConfig(vault_url=keyvault_url))
    except KeyVaultUnavailableError:
        return None
    return client.get_secret(secret_name)
