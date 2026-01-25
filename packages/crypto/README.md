# Crypto Package

Cryptography utilities intended for secure token handling and encryption helpers.

## Current state

- No implementation code yet in `packages/crypto/`.
- Security design is documented in `docs/architecture/security-architecture.md`.

## Quickstart

Review the security architecture:

```bash
sed -n '1,40p' docs/architecture/security-architecture.md
```

## How to verify

```bash
rg -n "encryption" docs/architecture/security-architecture.md
```

Expected output highlights encryption-related guidance.

## Key files

- `docs/architecture/security-architecture.md`: security reference.
- `packages/crypto/README.md`: scope and next steps.

## Example

Search for key management references:

```bash
rg -n "key vault|kms" docs/architecture/security-architecture.md
```

## Next steps

- Implement crypto helpers under `packages/crypto/src/`.
- Integrate with `services/identity-access/` for key rotation workflows.
