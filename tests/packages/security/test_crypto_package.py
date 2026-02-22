from __future__ import annotations

import pytest

pytest.importorskip("cryptography")

from cryptography.fernet import Fernet, InvalidToken
from security.crypto import decrypt_text, encrypt_text

FERNET_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


def test_crypto_encrypt_decrypt_roundtrip() -> None:
    plaintext = "sensitive-value"
    ciphertext = encrypt_text(plaintext, key=FERNET_KEY)
    assert ciphertext != plaintext
    assert decrypt_text(ciphertext, key=FERNET_KEY) == plaintext


def test_crypto_signature_verification_failure_on_tamper_and_wrong_key() -> None:
    plaintext = "signed-message"
    ciphertext = encrypt_text(plaintext, key=FERNET_KEY)

    tampered = ciphertext[:-2] + ("AA" if ciphertext[-2:] != "AA" else "BB")
    with pytest.raises(InvalidToken):
        decrypt_text(tampered, key=FERNET_KEY)

    wrong_key = Fernet.generate_key().decode("utf-8")
    with pytest.raises(InvalidToken):
        decrypt_text(ciphertext, key=wrong_key)
