# Performance Test Harness

This directory hosts the Locust-based performance harness for exercising API endpoints and connector workflows under load.

## Contents

- `config.yaml`: Load profile and endpoint configuration (users, request rates, duration).
- `quick_config.yaml`: Lightweight critical-path profile for PR smoke runs (under 2 minutes).
- `baselines.json`: Stored baseline metrics for performance comparisons in CI.
- `locustfile.py`: Locust tasks that read the configuration and issue API requests.
- `run_locust.py`: Helper script for running Locust using the configuration values.
- `mock_server.py`: Minimal HTTP server for CI smoke testing.
- `report_summary.py`: Generates a markdown summary from Locust CSV output.

## Configuration

Update `config.yaml` to reflect the environment under test.

```yaml
host: "https://api.local"
users: 50
spawn_rate: 10
run_time: "2m"
request_rate_per_user: 3
endpoints:
  - name: api_health
    method: GET
    path: /api/health
    weight: 2
  - name: connector_sync
    method: POST
    path: /api/connectors/sync
    weight: 1
    json:
      connector_id: "demo"
      run_id: "run-001"
```

- `users`: concurrent users.
- `spawn_rate`: how quickly users are spawned.
- `run_time`: duration of the test.
- `request_rate_per_user`: approximate request rate per user.

## Running locally

1. (Optional) start the mock server for quick verification:

   ```bash
   python tests/performance/mock_server.py --port 8000
   ```

2. Run the performance test with Locust in headless mode:

   ```bash
   python tests/performance/run_locust.py --config tests/performance/config.yaml --csv-prefix tests/performance/results/perf
   ```

3. Generate a summary report:

   ```bash
   python tests/performance/report_summary.py --csv-prefix tests/performance/results/perf --output tests/performance/results/summary.md
   ```

The CSV output (`*_stats.csv`, `*_failures.csv`) and summary markdown can be shared with the team or attached to PRs.

## Running in CI

The pull request workflow starts the mock server, runs the Locust harness with `quick_config.yaml`, compares results against `baselines.json`, and publishes a summary in the PR workflow output. The job also uploads the raw CSV results as build artifacts.

For a real environment test, update `config.yaml` to point at a deployed API host and remove the mock server step in CI.
