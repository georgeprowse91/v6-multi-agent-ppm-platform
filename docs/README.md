# Documentation

Product, architecture, runbook, and compliance docs for the platform.

## Quickstart

Open docs locally:

```bash
make docs-serve
```

## How to verify

Validate internal markdown links:

```bash
python scripts/check-links.py
```

Expected output: no lines printed and exit code 0.

## Key files

- `docs/product/`: product requirements and personas.
- `docs/architecture/`: system architecture descriptions.
- `docs/runbooks/`: operational runbooks.
- `docs/api/openapi.yaml`: API specification.

## Example

Show the OpenAPI title:

```bash
rg -n "title:" docs/api/openapi.yaml
```
