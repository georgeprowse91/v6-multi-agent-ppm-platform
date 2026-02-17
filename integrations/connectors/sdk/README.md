# Connector SDK

## Purpose

Provide shared helpers and scaffolding for building connectors that conform to the platform manifest and mapping model.

## What's inside

- [src](/integrations/connectors/sdk/src): Implementation source for this component.
- [tests](/integrations/connectors/sdk/tests): Test suites and fixtures.

## Connector implementation checklist

Use this checklist for every connector in `integrations/connectors/<connector_id>`:

- [ ] **Runtime entrypoint**: include `src/main.py` and route execution through `ConnectorRuntime`.
- [ ] **Manifest completeness**: include `manifest.yaml` that validates against `registry/schemas/connector-manifest.schema.json`.
- [ ] **Mapping completeness**: include `mappings/*.yaml` files referenced by the manifest, and ensure each validates against `registry/schemas/connector-mapping.schema.json`.
- [ ] **Read capability**: set and implement `maturity.capabilities.read`.
- [ ] **Write capability**: set and implement `maturity.capabilities.write`.
- [ ] **Webhook capability**: set and implement `maturity.capabilities.webhook` and align with `sync.supports_webhooks`.
- [ ] **Retry + idempotency**: document/implement retry behavior and set `maturity.capabilities.idempotent_write` + `maturity.capabilities.conflict_handling` accordingly.
- [ ] **Tests layout**: include a `tests/` directory with contract coverage validating runtime manifest/mapping loading.

## How it's used

The SDK is imported by connector implementations and validated in connector tests.

## How to run / develop / test

```bash
pytest integrations/connectors/sdk/tests
```

## Configuration

Configuration is inherited from the connector runtime and `.env` settings.

## Troubleshooting

- Import errors: install dev dependencies with `make install-dev`.
- Missing helper modules: ensure the SDK package path is correct.
