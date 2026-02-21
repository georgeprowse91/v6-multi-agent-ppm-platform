# Schema Promotion Rollback Runbook

## Purpose

Provide a safe, repeatable rollback path when a promoted schema version causes ingestion or downstream processing failures in staging/production environments.

## Triggers

- Spike in `4xx/5xx` responses on data-service ingest endpoints after a schema promotion.
- Validation errors indicating incompatible payloads for recently promoted schema versions.
- Consumer failures in analytics/workflow systems tied to new schema fields.

## Preconditions

1. Identify the impacted schema and promoted version (`<schema>@<bad_version>`).
2. Identify the last known good promoted version (`<schema>@<good_version>`).
3. Confirm blast radius (environments, tenants, connector feeds).

## Rollback Procedure

1. **Freeze new promotions/ingesters**
   - Pause promotion pipelines and disable scheduled ingest jobs for impacted connectors.
2. **Re-promote last known good version**
   - Execute:
     - `POST /v1/schemas/<schema>/versions/<good_version>/promote`
     - Body: `{ "environment": "<env>" }`
3. **Validate environment promotion records**
   - Verify `GET /v1/schemas/<schema>/promotions` includes `<good_version>` for `<env>` as latest effective promotion.
4. **Replay/repair failed ingests**
   - Re-run failed connector sync jobs and inspect validation error counts.
5. **Communicate incident status**
   - Update incident channel + status page with rollback completion and current ingestion status.

## Verification Checklist

- Ingestion for impacted schema succeeds in `<env>`.
- Error budget burn returns to baseline.
- No new incompatible payload errors for `<schema>`.
- Monitoring dashboards reflect healthy throughput/latency.

## Post-Incident Actions

- Open a follow-up PR to fix the schema change with compatible evolution.
- Update `data/schemas/examples/<schema>.json` with corrective payload snapshots.
- Add/expand compatibility tests in `services/data-service/tests/`.
