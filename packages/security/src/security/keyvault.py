from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:  # pragma: no cover - optional dependency
    DefaultAzureCredential = None
    SecretClient = None

if TYPE_CHECKING:
    from azure.keyvault.secrets import SecretClient as SecretClientType
else:  # pragma: no cover - optional dependency
    SecretClientType = Any


class KeyVaultUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class KeyVaultConfig:
    vault_url: str


class KeyVaultClient:
    def __init__(self, config: KeyVaultConfig) -> None:
        if not DefaultAzureCredential or not SecretClient:
            raise KeyVaultUnavailableError("Azure Key Vault SDK not installed")
        credential = DefaultAzureCredential()
        self._client: SecretClientType = SecretClient(
            vault_url=config.vault_url, credential=credential
        )

    def get_secret(self, name: str) -> str | None:
        secret = self._client.get_secret(name)
        return secret.value if secret else None

    def set_secret(self, name: str, value: str) -> None:
        self._client.set_secret(name, value)
