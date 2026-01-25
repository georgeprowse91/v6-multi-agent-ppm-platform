# Contracts Package

Shared contract definitions for APIs, events, and data models.

## Current state

- Source code lives under `packages/contracts/src/`.
- The package is referenced by validation scripts but not yet published.

## Quickstart

List contract sources:

```bash
ls packages/contracts/src
```

## How to verify

```bash
rg -n "schema" packages/contracts/src
```

Expected output shows contract schema definitions.

## Key files

- `packages/contracts/src/`: contract definitions.

## Example

Search for OpenAPI references:

```bash
rg -n "openapi" packages/contracts/src
```

## Next steps

- Add explicit versioning metadata in `packages/contracts/src/`.
- Publish a package entrypoint when API contracts stabilize.
