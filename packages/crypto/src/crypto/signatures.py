"""Digital signature utilities using HMAC-based message signing.

For scenarios requiring asymmetric signatures (RSA/EC), callers should use
the ``cryptography`` package directly.  This module provides a simple
HMAC-SHA256 sign/verify flow suitable for internal service-to-service
message authentication.
"""

from __future__ import annotations

import hmac as _hmac
import hashlib


def sign_message(
    key: str | bytes,
    message: str | bytes,
    *,
    algorithm: str = "sha256",
) -> str:
    """Create an HMAC signature for a message.

    Args:
        key: The signing secret.
        message: The message to sign.
        algorithm: Hash algorithm name.

    Returns:
        Hex-encoded signature string.
    """
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(message, str):
        message = message.encode("utf-8")
    return _hmac.new(key, message, algorithm).hexdigest()


def verify_signature(
    key: str | bytes,
    message: str | bytes,
    signature: str,
    *,
    algorithm: str = "sha256",
) -> bool:
    """Verify an HMAC signature in constant time.

    Args:
        key: The signing secret.
        message: The original message.
        signature: The hex-encoded signature to verify.
        algorithm: Hash algorithm name.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    expected = sign_message(key, message, algorithm=algorithm)
    return _hmac.compare_digest(expected, signature)
