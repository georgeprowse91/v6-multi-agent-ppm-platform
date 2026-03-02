# Outbound Dependency Client Inventory

## LLM providers
- `packages/llm/src/llm/client.py` (`OpenAIProviderAdapter`, `AzureProviderAdapter`) uses HTTP clients for completion + streaming.

## Workflow HTTP clients
- `apps/orchestration-service/src/workflow_client.py` calls workflow-service APIs.
- `apps/workflow-service/src/agent_client.py` and runtime HTTP step execution in `apps/workflow-service/src/workflow_runtime.py`.

## Identity / OIDC clients
- `packages/security/src/security/auth.py` uses OIDC discovery, JWKS, and token fetch.
- `apps/web/src/oidc_client.py` implements browser-facing OIDC interactions.
- `apps/api-gateway/src/api/middleware/security.py` contains OIDC/JWKS fetch logic.

## Connector APIs
- Connector SDK base call path in `connectors/sdk/src/base_connector.py` with connector implementations inheriting it.
- Web/API proxy connector routes in `apps/api-gateway/src/api/routes/connectors.py`.

## Search and external research clients
- `apps/api-gateway/src/api/routes/risk_research.py` delegates external risk research through agent paths.
- `apps/web/src/*_proxy.py` modules call upstream platform APIs over HTTP.

## Other outbound HTTP clients discovered in `apps/*/src` and `packages/*`
- `apps/analytics-service/src/main.py` + `apps/analytics-service/src/kpi_engine.py`.
- `apps/api-gateway/src/api/routes/analytics.py` + `apps/api-gateway/src/api/routes/lineage.py`.
- `apps/web/src/main.py` multiple service calls.
