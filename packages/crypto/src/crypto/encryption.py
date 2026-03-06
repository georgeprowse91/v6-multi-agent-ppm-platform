"""Symmetric encryption utilities using Fernet (AES-128-CBC + HMAC-SHA256).

Falls back gracefully when the ``cryptography`` package is not installed,
raising a clear error at call time rather than at import time.
"""

from __future__ import annotations

import os

class EncryptionError(RuntimeError):
    """Raised when an encryption or decryption operation fails."""


def _get_fernet(key: str | bytes) -> "cryptography.fernet.Fernet":  # type: ignore[name-defined]
    """Build a Fernet instance from a key (base64-url-safe 32-byte key)."""
    try:
        from cryptography.fernet import Fernet
    except BaseException as exc:
        raise EncryptionError(
            "The 'cryptography' package is required for encryption. "
            "Install it with: pip install cryptography"
        ) from exc

    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def _resolve_key(key: str | bytes | None, env_var: str | None) -> str | bytes:
    """Resolve an encryption key from an explicit value or environment variable."""
    if key is not None:
        return key
    if env_var is not None:
        value = os.environ.get(env_var)
        if value:
            return value
    raise EncryptionError(
        "An encryption key must be provided either directly or via env_var."
    )


def encrypt_text(
    plaintext: str,
    *,
    key: str | bytes | None = None,
    env_var: str | None = None,
) -> str:
    """Encrypt a string and return a URL-safe base64-encoded ciphertext.

    Args:
        plaintext: The text to encrypt.
        key: A Fernet-compatible key (base64-url-safe 32 bytes). If *None*,
            ``env_var`` is used to read the key from the environment.
        env_var: Environment variable name holding the encryption key.

    Returns:
        Base64-encoded ciphertext string.

    Raises:
        EncryptionError: If the key is missing or the ``cryptography``
            package is not installed.
    """
    resolved = _resolve_key(key, env_var)
    fernet = _get_fernet(resolved)
    token: bytes = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(
    ciphertext: str,
    *,
    key: str | bytes | None = None,
    env_var: str | None = None,
) -> str:
    """Decrypt a Fernet token back to plaintext.

    Args:
        ciphertext: The base64-encoded ciphertext produced by :func:`encrypt_text`.
        key: The same Fernet key used for encryption.
        env_var: Environment variable name holding the encryption key.

    Returns:
        Decrypted plaintext string.

    Raises:
        EncryptionError: On key mismatch, tampering, or missing dependencies.
    """
    resolved = _resolve_key(key, env_var)
    fernet = _get_fernet(resolved)
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise EncryptionError(f"Decryption failed: {exc}") from exc


def encrypt_bytes(
    data: bytes,
    *,
    key: str | bytes | None = None,
    env_var: str | None = None,
) -> bytes:
    """Encrypt raw bytes and return the Fernet token as bytes.

    Args:
        data: The bytes to encrypt.
        key: A Fernet-compatible key.
        env_var: Environment variable name holding the encryption key.

    Returns:
        Fernet token bytes.
    """
    resolved = _resolve_key(key, env_var)
    fernet = _get_fernet(resolved)
    return fernet.encrypt(data)


def decrypt_bytes(
    token: bytes,
    *,
    key: str | bytes | None = None,
    env_var: str | None = None,
) -> bytes:
    """Decrypt a Fernet token back to raw bytes.

    Args:
        token: The Fernet token produced by :func:`encrypt_bytes`.
        key: The same Fernet key used for encryption.
        env_var: Environment variable name holding the encryption key.

    Returns:
        Decrypted bytes.

    Raises:
        EncryptionError: On key mismatch, tampering, or missing dependencies.
    """
    resolved = _resolve_key(key, env_var)
    fernet = _get_fernet(resolved)
    try:
        return fernet.decrypt(token)
    except Exception as exc:
        raise EncryptionError(f"Decryption failed: {exc}") from exc


def generate_fernet_key() -> str:
    """Generate a new Fernet-compatible encryption key.

    Returns:
        A URL-safe base64-encoded 32-byte key as a string.
    """
    try:
        from cryptography.fernet import Fernet
    except BaseException as exc:
        raise EncryptionError(
            "The 'cryptography' package is required. "
            "Install it with: pip install cryptography"
        ) from exc

    return Fernet.generate_key().decode("utf-8")
