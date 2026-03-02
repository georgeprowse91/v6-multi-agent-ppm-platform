# Troubleshooting Guide

This guide covers common operational issues and how to resolve them.

## Authentication failures
- **Symptoms:** `401`/`403` responses, JWT validation errors.
- **Checks:**
  - Confirm Key Vault secret for JWT signing key.
  - Verify `IDENTITY_ISSUER` and `IDENTITY_AUDIENCE` values.
  - Validate clock skew between services.

## Workflow failures
- **Symptoms:** workflows stuck in `running` or `failed`.
- **Checks:**
  - Inspect workflow service logs for exceptions.
  - Ensure Postgres connectivity and migrations are current.
  - Verify queue backlogs are draining.

## Connector sync issues
- **Symptoms:** connector jobs fail, no data ingested.
- **Checks:**
  - Validate connector credentials in Key Vault.
  - Confirm network reachability to external APIs.
  - Inspect connector job logs in telemetry dashboard.

## Elevated latency
- **Symptoms:** p95 latency exceeds SLO.
- **Checks:**
  - Review SLO dashboard for error rate spikes.
  - Inspect database CPU and connection pool saturation.
  - Scale API gateway pods and confirm autoscaling.

## Backup/restore anomalies
- **Symptoms:** backup job alerts, restore fails.
- **Checks:**
  - Verify storage account health and immutability policy.
  - Confirm retention job logs for audit log pipeline.
  - Run DR validation checklist if in doubt.

## Escalation
- If issue persists beyond 30 minutes, engage the on-call lead and open an incident per `docs/runbooks/oncall.md`.
