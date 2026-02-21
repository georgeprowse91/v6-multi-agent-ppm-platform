# Auth Service

## Purpose

Handles OAuth2/OIDC token exchange, identity validation, and JWT verification for platform APIs and UI clients.


## Running locally

```bash
python -m tools.component_runner run --type service --name auth-service --dry-run
```

## Configuration

Configure issuer, audience, and trusted key settings via environment variables defined in deployment manifests and `.env`.

## Directory structure

| Folder | Description |
| --- | --- |
| [src/](./src/) | Service implementation (auth.py, main.py) |
| [tests/](./tests/) | Test suites |

## Key files

| File | Description |
| --- | --- |
| `main.py` | Application entrypoint |
| `Dockerfile` | Container build definition |

## Generated docs

- Endpoint reference (source of truth): [`docs/generated/services/auth-service.md`](../../docs/generated/services/auth-service.md).
- Regenerate with: `python ops/tools/codegen/generate_docs.py`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

