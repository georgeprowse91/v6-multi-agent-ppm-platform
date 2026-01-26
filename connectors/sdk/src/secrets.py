from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@dataclass(frozen=True)
class KeyVaultReference:
    vault_name: str
    secret_name: str
    secret_version: str | None


def _parse_keyvault_reference(value: str) -> KeyVaultReference | None:
    if not value.startswith("keyvault://"):
        return None
    parsed = urlparse(value)
    vault_name = parsed.netloc
    secret_path = parsed.path.lstrip("/")
    if not vault_name or not secret_path:
        raise ValueError(f"Invalid key vault reference: {value}")
    parts = secret_path.split("/")
    secret_name = parts[0]
    secret_version = parts[1] if len(parts) > 1 else None
    return KeyVaultReference(
        vault_name=vault_name,
        secret_name=secret_name,
        secret_version=secret_version,
    )


def resolve_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    reference = _parse_keyvault_reference(value)
    if not reference:
        return value
    vault_url = f"https://{reference.vault_name}.vault.azure.net/"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(reference.secret_name, reference.secret_version)
    return secret.value

