# Agent 13 Vendor Procurement — Scope & Boundary Checkpoint

Checkpoint goal: procurement workflow boundaries ready for execution, with clear ownership,
inputs/outputs, decision responsibilities, and inter-agent handoffs.

## 1) Intended scope (Agent 13)

**Primary mission:** manage the vendor/procurement lifecycle from onboarding through
invoicing/payment initiation, with vendor performance tracking and procurement eventing. This
agent is the system of record for vendor profiles, procurement requests, RFPs, proposals,
contracts, purchase orders, invoices, and vendor performance state in its tenant stores, and it
publishes lifecycle events to downstream systems. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L835-L942】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2622-L2678】

### Key workflows in scope

- **Vendor onboarding & compliance screening**: captures vendor profile, runs sanctions/credit/
  anti‑corruption checks, computes risk score, assigns compliance status, and triggers mitigation
  workflows when flagged/blocked. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1340-L1438】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】
- **Procurement intake**: creates procurement requests, categorizes them, checks budget
  availability, sets approval path, and tracks request state. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1454-L1549】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2732-L2756】
- **RFP/RFQ creation and publication**: selects template, generates RFP content (template or LLM),
  publishes document, and sends to external procurement connectors. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2780-L2862】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1548-L1664】
- **Proposal intake and scoring**: accepts proposals, evaluates them via AI or ML scoring, and
  selects vendors. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2870-L2915】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1666-L1781】
- **Contract lifecycle**: creates contracts, extracts key clauses, publishes to document store,
  and supports contract signing. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2917-L2990】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1881-L2035】
- **Purchase order + invoice lifecycle**: creates POs, performs invoice submission, three‑way
  matching, and initiates payment via ERP/AP connectors. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2992-L3089】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3089-L3185】
- **Vendor performance & analytics**: tracks SLA/quality/compliance metrics, generates
  scorecards, and publishes performance events. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3187-L3415】
- **Vendor research**: optional web search summarization for external signals. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2283-L2419】

## 2) Inputs & outputs (contracted interface)

### Supported actions (inputs)

Agent 13 accepts the following actions and input payload shapes:

- `onboard_vendor` → `vendor` profile payload (legal name, contact, category, etc.). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1048-L1138】
- `create_procurement_request` → `request` payload (requester, description, estimated_cost,
  project/program context, dates). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1048-L1154】
- `generate_rfp`, `submit_proposal`, `evaluate_proposals`, `select_vendor` → `rfp_id`, `proposal`,
  `criteria`, and `vendor_id` as applicable. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1155-L1271】
- `create_contract`, `sign_contract` → `contract` payload and `contract_id`. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1155-L1271】
- `create_purchase_order`, `submit_invoice`, `reconcile_invoice` → `purchase_order`, `invoice`,
  and `invoice_id`. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1155-L1271】
- `track_vendor_performance`, `get_vendor_scorecard` → `vendor_id`. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1155-L1244】
- `search_vendors`, `get_vendor_profile`, `update_vendor_profile`, `list_vendor_profiles` → query
  `criteria`, `vendor_id`, and `updates`. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1244-L1271】
- `research_vendor` → `vendor_id` or `vendor_name` (+ optional `domain`). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1110-L1154】

### Expected outputs

Outputs are standardized per action (ID, status, and key metadata). Examples:

- **Vendor onboarding** → vendor ID, compliance status, risk score, and next steps. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1340-L1438】
- **Procurement request** → request ID, status, budget availability, approval routing, and next
  steps. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1454-L1549】
- **RFP** → RFP ID, deadline, invited vendor list, and next steps. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1548-L1664】
- **Contract** → contract ID, term/value summary, and signing state. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1881-L2035】
- **Invoice reconciliation** → three‑way match results and payment initiation status. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3089-L3185】
- **Vendor scorecard** → overall score, performance metrics, compliance status, and
  recommendations. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2419-L2594】

## 3) Decision responsibilities (must/must-not)

### Must responsibilities

- **Must** run vendor compliance screening on onboarding and use policy to decide blocked/flagged
  status. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1340-L1438】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】
- **Must** determine procurement approval routing based on estimated cost and
  `procurement_threshold`. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2732-L2756】
- **Must** check budget availability for requests via the financial client (or future Agent 12
  integration). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2732-L2768】
- **Must** publish procurement lifecycle events (vendor onboarding, RFP publish, vendor
  selection, contract creation, invoice reconciliation, performance updates). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2622-L2678】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1548-L1664】
- **Must** initiate mitigation workflows when compliance violations are detected (policy
  enforcement event handlers). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2554-L2608】

### Must-not responsibilities

- **Must not** be the enterprise system of record for budgets, forecasts, or cost variance
  analytics (belongs to Agent 12). Agent 13 only consumes budget availability as a gating signal.
  【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2732-L2768】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L12-L52】
- **Must not** own enterprise regulatory frameworks, controls, or audit evidence
  (belongs to Agent 16). Agent 13 focuses on vendor-specific compliance screening and sanctions
  checks. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L1-L56】
- **Must not** override formal approvals outside its approval workflow integration; if external
  approvals are enabled, it must defer to that agent for approval outcomes. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L939-L1034】

## 4) Overlap & leakage analysis + handoff boundaries

### Agent 12 (Financial Management)

**Potential overlap**

- Budget availability checks in procurement intake vs. budget ownership in Agent 12. Agent 13
  currently uses `FinancialManagementClient` with `budget_data` or API configuration. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L805-L830】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2732-L2768】
- Invoice reconciliation/payment initiation overlaps with Agent 12’s cost tracking and financial
  reporting. Agent 13 initiates payments after three‑way match; Agent 12 should record those
  payments as actuals and update variance. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3089-L3185】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L20-L55】

**Handoff boundary**

- **Agent 13 → Agent 12:** send budget check requests at procurement intake and send “PO created,”
  “invoice reconciled,” and “payment initiated” events for Agent 12 to record actuals and update
  forecast/variance. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1454-L1549】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3089-L3185】
- **Agent 12 → Agent 13:** return budget availability and funding allocation decisions that gate
  procurement approvals. 【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L194-L244】

### Agent 16 (Compliance & Regulatory)

**Potential overlap**

- Vendor compliance checks (sanctions/credit/anti‑corruption) may overlap with enterprise
  compliance frameworks and audit evidence collection. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L38-L92】

**Handoff boundary**

- **Agent 13 → Agent 16:** supply vendor compliance outcomes and sanctions hits as evidence or
  control inputs (e.g., “Vendor compliance failed” events). 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1408-L1423】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2554-L2608】
- **Agent 16 → Agent 13:** provide regulatory policy updates that may change procurement
  compliance policy thresholds or required checks. 【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L292-L360】

## 5) Functional gaps / inconsistencies + required alignment

### Gaps / inconsistencies

- **Budget ownership gap:** Agent 13 runs budget checks locally; formal budget ownership and
  variance logic live in Agent 12. Align to always query Agent 12 or a shared finance service
  for budget availability in production. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L805-L830】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L20-L55】
- **Compliance policy split:** Agent 13 uses its own compliance policy and sanctions/risk checks,
  while Agent 16 manages frameworks, controls, and audit evidence. Define a shared event and
  evidence schema so compliance outcomes are auditable and consistent. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L38-L92】
- **Document management divergence:** RFPs and contracts are optionally published in Agent 13 via
  `DocumentManagementService`, but there is no explicit tie‑back to compliance evidence or audit
  storage. Cross‑link documents to Agent 16 evidence records. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1588-L1657】【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L1-L56】
- **Approval integration:** Procurement approval routing is computed locally; if external
  approvals are enabled, ensure the approval workflow agent is configured and that UI surfaces
  the approval record. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L939-L1034】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1454-L1549】

### Required alignment (prompt/tool/template/connector/UI)

- **RFP generation prompt & templates:** If `enable_openai_rfp` is on, UI should capture
  `requirements`, `evaluation_criteria`, and `template_id` to ensure prompt context is complete.
  【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2780-L2862】
- **Proposal scoring:** If `enable_ai_scoring` is enabled, ensure criteria weights are explicit in
  UI/requests so the AI scoring prompt is grounded and reproducible. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2870-L2915】
- **Connector readiness:** Procurement and ERP/AP connectors must be configured in tenant config
  (`enabled_connectors`, `connectors`) before go‑live; otherwise, results are “fallback” or
  “skipped.” Surface connector status in operational UI. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L53-L140】
- **Compliance UI:** Present compliance status (`pending`, `flagged`, `blocked`) and next steps
  for vendor onboarding so the manual remediation workflow is clear. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L2681-L2729】
- **Invoice reconciliation UI:** Three‑way match discrepancies should be displayed as line‑item
  exceptions, with manual override/approval hooks. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L3015-L3087】

## 6) Execution checkpoint (ready-to-run boundary statement)

- **Agent 13 owns** vendor onboarding, RFP/proposal/contract/PO/invoice workflows and vendor
  performance analytics.
- **Agent 12 owns** budgets, cost/actuals/variance/forecasting, and financial reporting.
- **Agent 16 owns** regulatory frameworks, controls, evidence, audits, and compliance dashboards.

Agent 13 should only proceed with procurement approvals and vendor selection once budget
availability (Agent 12) and compliance screening (Agent 13 with evidence surfaced to Agent 16)
are confirmed. 【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1340-L1438】【F:agents/delivery-management/agent-13-vendor-procurement/src/vendor_procurement_agent.py†L1454-L1549】【F:agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py†L194-L244】【F:agents/delivery-management/agent-16-compliance-regulatory/src/compliance_regulatory_agent.py†L292-L360】
