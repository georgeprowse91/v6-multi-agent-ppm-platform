# Business Case Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Business Case Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Build and evaluate business cases for demand items entering the portfolio pipeline.
- Perform ROI, NPV, IRR, and payback period calculations for investment recommendations.
- Run scenario analysis and Monte Carlo simulations to model uncertainty.
- Provide sensitivity analysis across cost/revenue assumptions.
- Support multi-currency conversions and configurable discount/inflation rates.

### Inputs
- `action`: `calculate_roi`, `build_business_case`, `scenario_analysis`, `compare_options`.
- `project` payload: `costs`, `benefits`, `cash_flows`, `currency`, `time_horizon` (required); `discount_rate`, `inflation_rate` (optional overrides).
- `scenario` payload (for scenario analysis): `assumptions`, `variations`.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- `calculate_roi`: `roi`, `npv`, `irr`, `payback_period`, `assumptions`, `sensitivity_analysis`, `monte_carlo_summary`.
- `build_business_case`: `business_case_id`, `recommendation`, `financial_summary`, `risk_assessment`.
- `scenario_analysis`: `scenarios`, `comparison`, `best_scenario`, `simulation`.
- Event emission: `business_case.created` with case metadata for downstream agents.

### Decision responsibilities
- Evaluate investment viability based on financial modelling outputs.
- Recommend approve/defer/reject based on configurable thresholds.
- Determine scenario rankings and best-fit recommendations.

### Must / must-not behaviors
- **Must** validate required financial inputs before performing calculations.
- **Must** persist business case records with tenant and audit metadata.
- **Must** publish a `business_case.created` event for downstream agents.
- **Must not** approve funding or commit delivery resources (reserved for portfolio and program agents).
- **Must not** set portfolio priority or sequencing (reserved for the Portfolio Optimisation agent).
- **Must not** manage vendor contracts or procurement decisions.

## Overlap & handoff boundaries

### Demand Intake
- **Overlap risk**: early cost/benefit estimation during intake.
- **Boundary**: The Demand Intake agent captures the request and triage metadata only. It hands off a validated demand record for the Business Case agent to build the business case and investment recommendation.

### Portfolio Optimisation
- **Overlap risk**: both agents touch ROI and investment sizing.
- **Boundary**: The Business Case agent owns the detailed business-case build and investment decision inputs. The Portfolio Optimisation agent consumes validated project-level financials (cost, ROI, expected value, benefits) for prioritization and optimization. The Portfolio Optimisation agent must not recalculate core business cases.

### Financial Management
- **Overlap risk**: profitability and ROI metrics overlap with live financial tracking.
- **Boundary**: The Business Case agent owns initial business case creation and investment recommendations. The Financial Management agent consumes approved business case cash flow inputs and tracks actuals/variance against the approved baseline.

## Functional gaps / inconsistencies & alignment needs

- **Prompt alignment**: ensure upstream prompts supply `costs`, `benefits`, and `cash_flows` with currency and time horizon for calculation readiness.
- **Connector alignment**: validate that ERP and financial connectors pass cost/benefit data consistently.
- **Template alignment**: business case templates should align with the financial summary format expected by the Portfolio Optimisation agent.
- **UI alignment**: business case UI should surface ROI, NPV, IRR, sensitivity charts, and Monte Carlo distributions.

## Checkpoint: business case criteria + dependency map entry

### Business case criteria (minimum)
- Required fields: `costs`, `benefits`, `cash_flows`, `time_horizon`.
- Financial model outputs: ROI, NPV, IRR, payback period.
- Validated against business case schema before persistence.

### Dependency map entry (ready for execution)
- **Upstream**: Demand Intake agent provides validated demand records with business objectives.
- **Core services**: financial modelling engine, notification service, tenant state store, event bus.
- **Downstream**: `business_case.created` event → the Portfolio Optimisation agent for portfolio scoring; financial summary → the Financial Management agent for baseline tracking.

## What's inside

- [src](/agents/portfolio-management/business-case-agent/src): Implementation source for this component.
- [tests](/agents/portfolio-management/business-case-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/business-case-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name business-case-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/business-case-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Advanced financial modelling

The agent supports richer investment modelling driven by `ops/config/agents/business-case-settings.yaml`:

- Configurable `discount_rate` and `inflation_rate` used in NPV/IRR calculations.
- `currency_rates` mapping for converting input costs/benefits/cash flows into a base AUD view.
- Configurable `simulation_iterations` for Monte Carlo NPV simulation.
- Configurable `sensitivity_variations` range applied to cost/revenue assumptions for sensitivity analysis.

#### Configuration file

Example:

```yaml
discount_rate: 0.08
inflation_rate: 0.025
currency_rates:
  AUD: 1.0
  EUR: 1.08
  GBP: 1.25
  JPY: 0.0068
simulation_iterations: 1000
sensitivity_variations:
  - -0.2
  - -0.1
  - 0.0
  - 0.1
  - 0.2
```

#### Response additions

ROI and scenario-analysis responses include:

- `assumptions`: discount/inflation/currency/simulation settings used.
- `sensitivity_analysis`: variation table with NPV and IRR impact.
- `monte_carlo_summary` (for ROI) / `simulation` (per scenario): mean NPV, standard deviation, and probability of negative NPV.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
