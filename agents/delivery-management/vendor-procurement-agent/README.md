# Vendor Procurement Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Vendor Procurement Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Vendor onboarding, registration, and profile management.
- Contract creation, negotiation tracking, and lifecycle management.
- RFP generation and proposal evaluation/scoring.
- Invoice processing and payment initiation via ERP/AP connectors.
- Vendor performance tracking, SLA monitoring, and risk/compliance screening.
- Procurement request classification and budget validation.

### Inputs
- `action`: `register_vendor`, `search_vendors`, `create_contract`, `generate_rfp`, `score_proposal`, `process_invoice`, `track_performance`, `screen_compliance`, `classify_request`, `check_budget`.
- `vendor` payload: name, category, capabilities, certifications, contact details.
- `contract` payload: vendor_id, terms, value, start/end dates, SLA definitions.
- `rfp` payload: requirements, evaluation criteria, timeline.
- `proposal` payload: vendor responses, pricing, technical approach.
- `invoice` payload: vendor_id, contract_id, line items, amounts.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- Vendor records with registration status and compliance screening results.
- Contract records with lifecycle status, milestones, and clause extraction.
- RFP documents and proposal scoring matrices.
- Invoice processing results and payment initiation records.
- Performance scorecards with SLA compliance, delivery metrics, and risk flags.
- Event emission: `vendor.registered`, `contract.created`, `invoice.processed`, `vendor.compliance.flagged`.

### Decision responsibilities
- Determine vendor compliance status based on third-party risk/sanctions screening.
- Score and rank proposals using configurable or ML-based scoring weights.
- Classify procurement requests into categories for routing.
- Validate budget availability before procurement commitment.
- Flag vendors on compliance watchlists and block procurement when policy requires.

### Must / must-not behaviors
- **Must** validate required fields for each action before processing.
- **Must** persist vendor, contract, invoice, and performance records with tenant scoping.
- **Must** publish procurement lifecycle events for downstream agents.
- **Must** enforce compliance policies (block on fail, flag on watchlist) when configured.
- **Must not** approve budgets or financial commitments (delegated to the Financial Management agent).
- **Must not** modify project scope or schedule baselines.
- **Must not** bypass approval workflows when `use_external_approval_agent` is enabled.

## Overlap & handoff boundaries

### Financial Management
- **Overlap risk**: vendor invoices and procurement costs influence financial tracking.
- **Boundary**: The Vendor Procurement agent owns vendor onboarding, contract management, invoice capture, and procurement approvals. The Financial Management agent consumes invoice/actuals data to update cost tracking and forecasts, and provides budget availability checks back to the Vendor Procurement agent.

### Program Management
- **Overlap risk**: program-level vendor synergies overlap with procurement actions.
- **Boundary**: The Program Management agent flags program-level vendor synergies and consolidation opportunities. The Vendor Procurement agent owns the actual procurement actions, vendor relationships, and contract execution.

## Functional gaps / inconsistencies & alignment needs

- **Approval integration**: ensure the centralized approval workflow agent is invoked when `use_external_approval_agent` is enabled, rather than falling back to local auto-approval.
- **Budget validation**: confirm financial agent endpoint or local budget data is configured for budget availability checks.
- **Compliance screening**: document the expected API contract for third-party risk/sanctions sources and mock response behavior for testing.
- **UI alignment**: vendor management UI should surface compliance status, contract lifecycle, performance scorecards, and procurement request classification.
- **Connector alignment**: ensure ERP/AP connectors (SAP Ariba, Coupa, Oracle Procurement, Dynamics 365) are configured with credentials and endpoint mappings.

## Checkpoint: vendor procurement lifecycle + dependency map entry

### Vendor procurement lifecycle
1. **Request**: classify procurement request and validate budget.
2. **Source**: search vendors, generate RFP, collect proposals.
3. **Evaluate**: score proposals, screen compliance, rank vendors.
4. **Contract**: create contract, extract clauses, track milestones.
5. **Execute**: process invoices, initiate payments, track delivery.
6. **Monitor**: track performance, monitor SLAs, flag risks.

### Dependency map entry
- **Upstream**: procurement requests from project teams, budget data from the Financial Management agent.
- **Core services**: approval workflow, compliance screening APIs, ERP/AP connectors, event bus.
- **Downstream**: Financial Management agent (invoice/actuals for cost tracking), Program Management agent (vendor synergy signals).

## What's inside

- [src](/agents/delivery-management/vendor-procurement-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/vendor-procurement-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/vendor-procurement-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name vendor-procurement-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/vendor-procurement-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

Additional vendor procurement configuration (set via agent config or environment variables) includes:

- `vendor_store_path`, `contract_store_path`, `invoice_store_path`, `vendor_performance_store_path`, `event_store_path`: JSON-backed state paths for tenant-scoped storage.
- `procurement_connectors.enabled_connectors`: list of procurement connectors (`sap_ariba`, `coupa`, `oracle_procurement`, `dynamics_365`).
- `procurement_connectors.connectors`: per-connector configuration payloads for SAP Ariba, Coupa, Oracle Procurement, and Dynamics 365 integrations.
- `erp_ap_connectors.enabled_connectors`: enable ERP/AP connectors for payment initiation.
- `ml_config.azure_ml_enabled`: toggles Azure ML training mode for vendor recommendations and risk scoring.
- `ml_config.training_data`: optional training data used for ML-based vendor scoring.
- `ml_config.scoring_weights`: optional weight overrides for ML-based vendor and proposal scoring.
- `risk_config.risk_sources`: list of third-party risk/sanctions API definitions (`name`, `endpoint`, `category`, `api_key`).
- `risk_config.mock_responses`: map of vendor names to mock compliance responses for testing.
- `compliance_policy`: policies for compliance enforcement (`block_on_fail`, `flag_on_watchlist`, `risk_threshold`).
- `event_bus.enabled` / `event_bus.endpoint`: enable publishing events to Azure Service Bus-compatible HTTP endpoint.
- `task_management.queue_config`: workflow task queue configuration for mitigation tasks.
- `communications_config.use_agent` / `communications_config.agent_config`: notify stakeholders via the communications agent.
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
