#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key


def _load_private_key() -> bytes:
    b64_key = os.getenv("SIGNING_PRIVATE_KEY_B64")
    key_path = os.getenv("SIGNING_PRIVATE_KEY_PATH")

    if b64_key:
        return base64.b64decode(b64_key)
    if key_path:
        return Path(key_path).read_bytes()
    raise SystemExit(
        "Signing key missing. Set SIGNING_PRIVATE_KEY_B64 or SIGNING_PRIVATE_KEY_PATH."
    )


def main() -> int:
    artifact_path = Path(os.getenv("SIGN_ARTIFACT", "dist/sbom.json"))
    signature_path = Path(os.getenv("SIGNATURE_OUTPUT", "dist/sbom.json.sig"))

    if not artifact_path.exists():
        raise SystemExit(f"Artifact not found: {artifact_path}")
    private_key = load_pem_private_key(_load_private_key(), password=None)

    digest = hashlib.sha256(artifact_path.read_bytes()).digest()
    signature = private_key.sign(
        digest,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )

    signature_path.write_bytes(signature)
    print(f"Signature written to {signature_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
