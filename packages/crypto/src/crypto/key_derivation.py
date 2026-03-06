"""Key derivation and secure random token generation.

Uses :mod:`secrets` and :mod:`hashlib` from the standard library, with
optional PBKDF2/HKDF support from the ``cryptography`` package when available.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import secrets

_HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe token.

    Args:
        nbytes: Number of random bytes (the resulting string is longer
            due to base64 encoding).

    Returns:
        A URL-safe base64-encoded token string.
    """
    return secrets.token_urlsafe(nbytes)


def generate_key(nbytes: int = 32) -> bytes:
    """Generate cryptographically secure random bytes suitable for use as a key.

    Args:
        nbytes: Number of random bytes to generate.

    Returns:
        Random bytes.
    """
    return secrets.token_bytes(nbytes)


def derive_key(
    password: str | bytes,
    *,
    salt: bytes | None = None,
    iterations: int = 600_000,
    key_length: int = 32,
    algorithm: str = "sha256",
) -> tuple[bytes, bytes]:
    """Derive a key from a password using PBKDF2-HMAC.

    Uses the ``cryptography`` package when available for a C-accelerated
    implementation, otherwise falls back to :func:`hashlib.pbkdf2_hmac`.

    Args:
        password: The password or passphrase.
        salt: Random salt bytes.  If *None*, 16 random bytes are generated.
        iterations: PBKDF2 iteration count (default mirrors OWASP 2023
            recommendation for SHA-256).
        key_length: Desired key length in bytes.
        algorithm: Hash algorithm name (e.g. ``"sha256"``).

    Returns:
        A ``(derived_key, salt)`` tuple so the salt can be stored alongside
        the derived key.
    """
    if isinstance(password, str):
        password = password.encode("utf-8")
    if salt is None:
        salt = secrets.token_bytes(16)

    _use_cryptography = False
    if _HAS_CRYPTOGRAPHY:
        try:
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes

            _use_cryptography = True
        except BaseException:
            # cryptography may be installed but broken (e.g. missing native backend)
            _use_cryptography = False

    if _use_cryptography:
        _algo_map = {
            "sha256": hashes.SHA256(),  # type: ignore[possibly-undefined]
            "sha384": hashes.SHA384(),
            "sha512": hashes.SHA512(),
        }
        hash_algo = _algo_map.get(algorithm)
        if hash_algo is None:
            raise ValueError(f"Unsupported algorithm for cryptography PBKDF2: {algorithm}")
        kdf = PBKDF2HMAC(  # type: ignore[possibly-undefined]
            algorithm=hash_algo,
            length=key_length,
            salt=salt,
            iterations=iterations,
        )
        derived = kdf.derive(password)
    else:
        derived = hashlib.pbkdf2_hmac(algorithm, password, salt, iterations, dklen=key_length)

    return derived, salt
