# Data Lineage Service endpoint reference

Source: `services/data-lineage-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `GET` | `/v1/lineage/events` | `list_events` |
| `POST` | `/v1/lineage/events` | `ingest_event` |
| `GET` | `/v1/lineage/events/{lineage_id}` | `get_event` |
| `GET` | `/v1/lineage/graph` | `get_graph` |
| `POST` | `/v1/quality/remediate` | `remediate_quality` |
| `POST` | `/v1/quality/remediate/{lineage_id}` | `remediate_lineage_record` |
| `GET` | `/v1/quality/summary` | `get_quality_summary` |
| `GET` | `/v1/retention/status` | `retention_status` |
| `GET` | `/version` | `version` |
