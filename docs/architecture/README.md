# Architecture Docs

Design references for logical, physical, and security architecture.

## Quickstart

Open the logical architecture doc:

```bash
sed -n '1,40p' docs/architecture/logical-architecture.md
```

## How to verify

List architecture files:

```bash
ls docs/architecture
```

Expected output includes architecture markdown files for logical, physical, and security.

## Key files

- `docs/architecture/logical-architecture.md`
- `docs/architecture/physical-architecture.md`
- `docs/architecture/security-architecture.md`

## Example

Search for "agent" references:

```bash
rg -n "agent" docs/architecture
```
