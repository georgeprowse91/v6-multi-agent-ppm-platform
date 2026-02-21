# Audit Log Service endpoint reference

Source: `services/audit-log/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/audit/events` | `ingest_event` |
| `GET` | `/v1/audit/events/{event_id}` | `get_event` |
| `GET` | `/v1/audit/evidence/export` | `export_evidence` |
| `GET` | `/version` | `version` |
