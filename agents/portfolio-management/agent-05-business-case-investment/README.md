# Agent 05: Business Case Investment Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 05: Business Case Investment. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/portfolio-management/agent-05-business-case-investment/src): Implementation source for this component.
- [tests](/agents/portfolio-management/agent-05-business-case-investment/tests): Test suites and fixtures.
- [Dockerfile](/agents/portfolio-management/agent-05-business-case-investment/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-05-business-case-investment --dry-run
```

Run unit tests (if present):

```bash
pytest agents/portfolio-management/agent-05-business-case-investment/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.


## Advanced financial modelling

The agent now supports richer investment modelling driven by `ops/config/agents/business-case-settings.yaml`:

- Configurable `discount_rate` and `inflation_rate` used in NPV/IRR calculations.
- `currency_rates` mapping for converting input costs/benefits/cash flows into a base AUD view.
- Configurable `simulation_iterations` for Monte Carlo NPV simulation.
- Configurable `sensitivity_variations` range applied to cost/revenue assumptions for sensitivity analysis.

### Configuration file

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

### Response additions

ROI and scenario-analysis responses include:

- `assumptions`: discount/inflation/currency/simulation settings used.
- `sensitivity_analysis`: variation table with NPV and IRR impact.
- `monte_carlo_summary` (for ROI) / `simulation` (per scenario): mean NPV, standard deviation, and probability of negative NPV.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
