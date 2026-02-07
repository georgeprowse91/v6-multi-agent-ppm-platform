#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def _load_public_key() -> bytes:
    b64_key = os.getenv("SIGNING_PUBLIC_KEY_B64")
    key_path = os.getenv("SIGNING_PUBLIC_KEY_PATH", "config/signing/dev_signing_public.pem")

    if b64_key:
        return base64.b64decode(b64_key)
    return Path(key_path).read_bytes()


def main() -> int:
    artifact_path = Path(os.getenv("SIGN_ARTIFACT", "dist/sbom.json"))
    signature_path = Path(os.getenv("SIGNATURE_OUTPUT", "dist/sbom.json.sig"))

    if not artifact_path.exists() or not signature_path.exists():
        raise SystemExit("Artifact or signature missing")

    public_key = load_pem_public_key(_load_public_key())
    digest = hashlib.sha256(artifact_path.read_bytes()).digest()

    public_key.verify(
        signature_path.read_bytes(),
        digest,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    print("Signature verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
