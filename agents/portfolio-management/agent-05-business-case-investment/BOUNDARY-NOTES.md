# Agent 05: Business Case & Investment — Boundary Notes

## Intended scope (validated)
- Build business cases, ROI metrics, and investment recommendations for proposed initiatives.
- Accepts demand-context inputs plus cost/benefit estimates and enriches with ERP/CRM/market signals.
- Produces draft business case documents, scenario analyses, historical comparisons, and recommendation payloads.
- Emits business case and recommendation events for downstream portfolio prioritization and governance.

## Inputs and outputs
**Primary inputs**
- `action` selector: `generate_business_case`, `calculate_roi`, `run_scenario_analysis`, `compare_to_historical`, `generate_recommendation`, `get_business_case`.
- `request` payload with at least: `title`, `description`, `project_type`, `estimated_cost`, `estimated_benefits`.
- Optional `business_case_id`, `scenarios`, `filters`, `tenant_id`, `correlation_id`.

**Primary outputs**
- Business case draft document + metrics (NPV/IRR/ROI/payback/TCO).
- Scenario comparison + recommendation.
- Historical comparison benchmarks.
- Investment recommendation payload with confidence and narrative.

## Decision responsibilities
- Computes financial metrics (NPV/IRR/ROI/payback/TCO) and confidence.
- Recommends **approve/defer/reject** based on ROI threshold, payback, and NPV.
- Does **not** finalize approvals; downstream governance handles gate decisions.

## Must / must-not behaviors
**Must**
- Validate ROI inputs against schema + data-quality rules before ROI calculations.
- Persist business case drafts with tenant scoping and emit `business_case.created`.
- Notify requester when draft or recommendation is available.
- Keep recommendation rules deterministic and auditable.

**Must not**
- Must not override portfolio prioritization decisions (Agent 06 owns portfolio optimization).
- Must not change demand intake records (Agent 04 owns intake/source-of-truth).
- Must not approve funding or bypass stage-gate policies (Agent 03/09 own approvals).

## Handoff boundaries + overlap control
**With Agent 04 (Demand & Intake)**
- **Handoff in:** Use demand details (`demand_id`, title, description, business objective) as the starting point.
- **Boundary:** Agent 04 owns intake categorization, dedupe, and initial demand status. Agent 05 should not mutate demand status—only reference `demand_id`.
- **Overlap risk:** Both agents generate “problem statements.” Mitigation: Agent 05 reuses demand description, avoids reclassification.

**With Agent 06 (Portfolio Strategy & Optimization)**
- **Handoff out:** Provide business-case outputs (`financial_metrics`, recommendation, scenario summaries).
- **Boundary:** Agent 06 owns ranking/selection across the portfolio; Agent 05 provides single-initiative analytics.
- **Overlap risk:** Both can compute ROI/score. Mitigation: Agent 06 consumes ROI metrics from Agent 05 rather than recomputing unless inputs are missing.

## Functional gaps / inconsistencies to align
- **Template alignment:** Business-case templates exist in `docs/templates/portfolio-program/`, but Agent 05 expects `templates` in config. Provide a mapping layer or template registry to bind `project_type:methodology` to these templates.
- **Schema clarity:** ROI schema is validated, but `generate_business_case` does not validate request payload against a schema. Introduce a business-case request schema or reuse demand schema + cost/benefit schema.
- **Tenant isolation in vector search:** Historical comparisons use in-memory vector index; ensure tenant-aware search to prevent cross-tenant leakage.
- **Event/UI alignment:** Draft status is always `Draft`. UI should expose status, next steps, and link to the stored business case, including recommendation rationale.
- **Connector expectations:** ERP/CRM/market connectors are optional; UI should surface data provenance and fallback assumptions when connectors are absent.

## Dependency map entry (execution-ready)
```yaml
node: agent-05-business-case-investment
role: business_case_investment
upstream:
  - agent: agent-04-demand-intake
    inputs: [demand_id, title, description, business_objective, requester]
  - connector: erp_client
    inputs: [costs, labor_share, overhead_share, material_share, contingency_rate, cash_flow]
  - connector: crm_client
    inputs: [benefits, revenue_share, savings_share, risk_share, cash_flow]
  - connector: market_client
    inputs: [market_size, growth_rate, competitive_landscape, drivers, risks]
  - store: data/business_case_store.json
    inputs: [existing_business_cases]
downstream:
  - agent: agent-06-portfolio-strategy-optimisation
    outputs: [financial_metrics, scenario_summary, recommendation, confidence_level]
  - agent: agent-03-approval-workflow
    outputs: [recommendation_payload]
  - events:
      - business_case.created
      - investment.recommendation
artifacts:
  - store: data/business_case_store.json
  - schema: data/schemas/roi.schema.json
  - templates:
      - docs/templates/portfolio-program/business-case-template.var1.md
      - docs/templates/portfolio-program/business-case-template.var2.md
      - docs/templates/portfolio-program/business-case-template.var4.md
```
