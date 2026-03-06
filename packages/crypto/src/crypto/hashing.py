"""Hashing and HMAC utilities.

Uses :mod:`hashlib` and :mod:`hmac` from the standard library.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac


def hash_text(
    text: str,
    *,
    algorithm: str = "sha256",
) -> str:
    """Return the hex digest of *text* using the given hash algorithm.

    Args:
        text: The string to hash (encoded as UTF-8).
        algorithm: Any algorithm supported by :mod:`hashlib`
            (e.g. ``"sha256"``, ``"sha512"``, ``"sha3_256"``).

    Returns:
        Lowercase hex digest string.
    """
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def hash_bytes(
    data: bytes,
    *,
    algorithm: str = "sha256",
) -> str:
    """Return the hex digest of raw *data*.

    Args:
        data: The bytes to hash.
        algorithm: Hash algorithm name.

    Returns:
        Lowercase hex digest string.
    """
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def hmac_digest(
    key: str | bytes,
    message: str | bytes,
    *,
    algorithm: str = "sha256",
) -> str:
    """Compute an HMAC hex digest.

    Args:
        key: The HMAC secret key.
        message: The message to authenticate.
        algorithm: Hash algorithm name.

    Returns:
        Lowercase hex digest of the HMAC.
    """
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(message, str):
        message = message.encode("utf-8")
    return _hmac.new(key, message, algorithm).hexdigest()


def verify_hmac(
    key: str | bytes,
    message: str | bytes,
    expected_digest: str,
    *,
    algorithm: str = "sha256",
) -> bool:
    """Verify an HMAC digest in constant time.

    Args:
        key: The HMAC secret key.
        message: The original message.
        expected_digest: The hex digest to compare against.
        algorithm: Hash algorithm name.

    Returns:
        ``True`` if the digest matches, ``False`` otherwise.
    """
    computed = hmac_digest(key, message, algorithm=algorithm)
    return _hmac.compare_digest(computed, expected_digest)
