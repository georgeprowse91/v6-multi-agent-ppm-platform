# Agent 13: Vendor Procurement Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 13: Vendor Procurement. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-13-vendor-procurement/src`: Implementation source for this component.
- `agents/delivery-management/agent-13-vendor-procurement/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-13-vendor-procurement/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-13-vendor-procurement --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-13-vendor-procurement/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Additional vendor procurement configuration (set via agent config or environment variables) includes:

- `vendor_store_path`, `contract_store_path`, `invoice_store_path`, `vendor_performance_store_path`, `event_store_path`: JSON-backed state paths for tenant-scoped storage.
- `procurement_connectors.enabled_connectors`: list of procurement connectors (`sap_ariba`, `coupa`, `oracle_procurement`, `dynamics_365`).
- `procurement_connectors.connectors`: per-connector configuration payloads for SAP Ariba, Coupa, Oracle Procurement, and Dynamics 365 integrations.
- `erp_ap_connectors.enabled_connectors`: enable ERP/AP connectors for payment initiation.
- `ml_config.azure_ml_enabled`: toggles Azure ML training mode for vendor recommendations and risk scoring.
- `ml_config.training_data`: optional training data used for ML-based vendor scoring.
- `risk_config.risk_sources`: list of third-party risk/sanctions API definitions (`name`, `endpoint`, `category`, `api_key`).
- `risk_config.mock_responses`: map of vendor names to mock compliance responses for testing.
- `event_bus.enabled` / `event_bus.endpoint`: enable publishing events to Azure Service Bus-compatible HTTP endpoint.
- `classification_config.training_data`: training corpus for procurement request categorization.
- `financial_config.endpoint` / `financial_config.budget_data`: budget service endpoint or local budget map for budget checks.
- `analytics_config.endpoint` / `analytics_config.performance_data`: analytics service endpoint or local performance data for SLA and delivery metrics.
- `use_external_approval_agent`: enable the centralized approval workflow agent instead of the local auto-approval fallback.
- `enable_openai_rfp`: enable OpenAI-based RFP generation.
- `enable_ai_scoring`: enable AI-based proposal scoring.
- `enable_ai_vendor_ranking`: enable ML-based vendor ranking for search results.
- `enable_ml_recommendations`: enable ML-based vendor recommendations for procurement requests.
- `form_recognizer.endpoint` / `form_recognizer.api_key` or environment variables `AZURE_FORM_RECOGNIZER_ENDPOINT` / `AZURE_FORM_RECOGNIZER_KEY`: Azure Form Recognizer configuration for contract clause extraction.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
