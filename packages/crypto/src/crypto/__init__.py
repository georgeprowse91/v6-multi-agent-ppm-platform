"""Cryptographic primitives for the PPM platform.

Provides encrypt/decrypt, hashing, key derivation, and digital signature
utilities built on Python's standard library and the ``cryptography`` package.
"""

from crypto.encryption import decrypt_bytes, decrypt_text, encrypt_bytes, encrypt_text
from crypto.hashing import hash_bytes, hash_text, hmac_digest, verify_hmac
from crypto.key_derivation import derive_key, generate_key, generate_token
from crypto.signatures import sign_message, verify_signature

__all__ = [
    # Encryption
    "encrypt_text",
    "decrypt_text",
    "encrypt_bytes",
    "decrypt_bytes",
    # Hashing
    "hash_text",
    "hash_bytes",
    "hmac_digest",
    "verify_hmac",
    # Key derivation
    "derive_key",
    "generate_key",
    "generate_token",
    # Signatures
    "sign_message",
    "verify_signature",
]
