# Connector SDK

Shared utilities for connector authentication, pagination, and retry logic.

## Current state

- SDK source code is in `connectors/sdk/src/`.
- Tests live in `connectors/sdk/tests/`.
- No published package yet; it is consumed by local connector modules.

## Quickstart

List available SDK modules:

```bash
ls connectors/sdk/src
```

## How to verify

```bash
ls connectors/sdk/tests
```

Expected output includes test files that exercise SDK helpers.

## Key files

- `connectors/sdk/src/`: SDK implementation.
- `connectors/sdk/tests/`: SDK tests.

## Example

Search for retry helpers:

```bash
rg -n "retry" connectors/sdk/src
```

## Next steps

- Publish the SDK as a package once connector APIs are stabilized.
- Add integration tests under `connectors/sdk/tests/` that run in CI.
