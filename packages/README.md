# Packages

Shared libraries intended to be consumed by apps and services once implementations are in place.

## Quickstart

List the available packages:

```bash
ls packages
```

## How to verify

```bash
ls packages/contracts
```

Expected output includes a `src/` directory for the contracts package.

## Key files

- `packages/contracts/src/`: shared API/contract definitions.
- `packages/policy/`: policy helper scaffolding.
- `packages/observability/`: observability helpers scaffolding.

## Example

Search for contract schemas:

```bash
rg -n "schema" packages/contracts/src
```

## Next steps

- Add implementation code under each `packages/<name>/src/` directory.
- Wire package usage into `apps/` and `services/` as those components stabilize.
