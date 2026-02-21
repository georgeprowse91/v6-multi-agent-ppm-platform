# Data Sync Service endpoint reference

Source: `services/data-sync-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `GET` | `/v1/sync/conflicts` | `list_conflicts` |
| `GET` | `/v1/sync/jobs` | `list_sync_jobs` |
| `POST` | `/v1/sync/jobs/{connector}/{entity}/run` | `run_sync_job` |
| `GET` | `/v1/sync/logs` | `list_sync_logs` |
| `POST` | `/v1/sync/propagate` | `propagate_update` |
| `POST` | `/v1/sync/run` | `run_sync` |
| `GET` | `/v1/sync/status/{job_id}` | `get_sync_status` |
| `GET` | `/v1/sync/summary` | `get_sync_summary` |
| `GET` | `/version` | `version` |
