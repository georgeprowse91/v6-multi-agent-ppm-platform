from __future__ import annotations

import os

from cryptography.fernet import Fernet
from security.secrets import resolve_secret


class EncryptionKeyError(RuntimeError):
    pass


def get_encryption_key(env_var: str) -> str | None:
    resolved = resolve_secret(os.getenv(env_var))
    if resolved:
        return str(resolved)
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise EncryptionKeyError(f"{env_var} is required in production")
    return None


def _build_fernet(key: str) -> Fernet:
    return Fernet(key.encode("utf-8"))


def encrypt_text(plaintext: str, *, key: str | None = None, env_var: str | None = None) -> str:
    if key is None and env_var:
        key = get_encryption_key(env_var)
    if not key:
        raise EncryptionKeyError("encryption key is required to encrypt data")
    fernet = _build_fernet(key)
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(ciphertext: str, *, key: str | None = None, env_var: str | None = None) -> str:
    if key is None and env_var:
        key = get_encryption_key(env_var)
    if not key:
        raise EncryptionKeyError("encryption key is required to decrypt data")
    fernet = _build_fernet(key)
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
