from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:  # pragma: no cover - optional dependency
    DefaultAzureCredential = None
    SecretClient = None


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
        self._client = SecretClient(vault_url=config.vault_url, credential=credential)

    def get_secret(self, name: str) -> Optional[str]:
        secret = self._client.get_secret(name)
        return secret.value if secret else None

    def set_secret(self, name: str, value: str) -> None:
        self._client.set_secret(name, value)
