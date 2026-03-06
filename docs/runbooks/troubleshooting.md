# Troubleshooting Guide

Operational troubleshooting guide for the Multi-Agent PPM Platform.

## Authentication

### JWT Token Expired

**Symptom:** 401 responses with `token_expired` error code.

**Resolution:**
1. Verify the client is refreshing tokens before expiry.
2. Check clock skew between client and server (max 60s allowed).
3. If using dev mode, ensure `AUTH_DEV_MODE=true` is set.

### OIDC Discovery Failure

**Symptom:** 500 errors during authentication with `oidc_discovery_failed` in logs.

**Resolution:**
1. Verify the OIDC issuer URL is reachable from the cluster.
2. Check DNS resolution for the identity provider.
3. Clear cached OIDC config: `kill -USR1 <api-gateway-pid>`.

## Database

### Connection Pool Exhaustion

**Symptom:** `ConnectionPoolError` or timeouts in database operations.

**Resolution:**
1. Check active connections: `SELECT count(*) FROM pg_stat_activity;`
2. Review pool configuration in environment variables.
3. Restart affected service pods if connections are leaked.

## Agent Runtime

### Agent Initialization Failure

**Symptom:** Agent health check returns `unhealthy` status.

**Resolution:**
1. Check agent logs for initialization errors.
2. Verify required configuration is present in agent config service.
3. Ensure dependent services (LLM, database) are accessible.

## Connector Issues

### Sync Failures

**Symptom:** Data sync jobs failing with connector errors.

**Resolution:**
1. Check connector health via `/v1/connectors/{id}/health`.
2. Verify credentials are valid and not expired.
3. Check rate limits on the external system.

## Escalation

If issues cannot be resolved using this guide:

1. Collect relevant logs and metrics.
2. Open an incident in the on-call channel.
3. Escalate to the platform engineering team with collected evidence.
