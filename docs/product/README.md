# Product dashboards

## Portfolio health & lifecycle dashboards

The workspace dashboard provides portfolio-level analytics alongside lifecycle stage-gate progress. Navigate to the SPA project workspace (`/app/projects/:projectId`) and select the **Dashboard** tab to see the portfolio health KPIs, lifecycle stage-gate progress indicators, and supporting charts.

### Demo mode

1. Start the web UI with demo mode enabled:

   ```bash
   export DEMO_MODE=true
   ```

2. Open the workspace and select the **Dashboard** tab:

   ```
   /app/projects/demo-1
   ```

Demo mode loads static JSON from `examples/demo-scenarios/portfolio-health.json` and `examples/demo-scenarios/lifecycle-metrics.json` to populate KPIs and stage-gate progress indicators.

### Production mode

When `DEMO_MODE` is unset or `false`, the dashboard calls the following API endpoints:

- `GET /api/portfolio-health?project_id=<id>`
- `GET /api/lifecycle-metrics?project_id=<id>`

These endpoints return mocked analytics payloads by default (intended to be replaced with live analytics feeds). The lifecycle dashboard includes clickable stage-gate indicators; selecting a stage-gate navigates to the first activity in that stage within the workspace.
