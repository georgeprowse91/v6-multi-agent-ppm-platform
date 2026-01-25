# Document Service

Document ingestion, storage, and retrieval workflows for the platform.

## Current state

- Migrations live under `apps/document-service/migrations/`.
- Policy templates for document handling live under `apps/document-service/policies/`.
- There is no standalone service binary yet; the assets are used by other services.

## Quickstart

Inspect the document policy templates:

```bash
rg -n "policy" apps/document-service/policies
```

## How to verify

```bash
ls apps/document-service/migrations
```

Expected output lists migration files for the document service schema.

## Key files

- `apps/document-service/migrations/`: database migrations.
- `apps/document-service/policies/`: document handling policies.
- `apps/document-service/README.md`: current state and usage notes.

## Example

Open the first migration file:

```bash
ls apps/document-service/migrations | head -n 1
```

## Next steps

- Implement API handlers under `apps/document-service/src/`.
- Integrate storage backends (see `services/audit-log/storage/`).
