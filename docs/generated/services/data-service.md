# Data Service endpoint reference

Source: `services/data-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `GET` | `/livez` | `livez` |
| `GET` | `/readyz` | `readyz` |
| `GET` | `/readyz/deep` | `deep_readyz` |
| `GET` | `/v1/agent-runs` | `list_agent_runs` |
| `POST` | `/v1/agent-runs` | `ingest_agent_run` |
| `GET` | `/v1/agent-runs/{agent_run_id}` | `get_agent_run` |
| `GET` | `/v1/entities/{schema_name}` | `list_entities` |
| `POST` | `/v1/entities/{schema_name}` | `ingest_entity` |
| `GET` | `/v1/entities/{schema_name}/{entity_id}` | `get_entity` |
| `POST` | `/v1/ingest/connector` | `ingest_connector` |
| `GET` | `/v1/retention/status` | `retention_status` |
| `GET` | `/v1/scenarios` | `list_scenarios` |
| `POST` | `/v1/scenarios` | `ingest_scenario` |
| `GET` | `/v1/scenarios/{scenario_id}` | `get_scenario` |
| `GET` | `/v1/schemas` | `list_schemas` |
| `POST` | `/v1/schemas` | `register_schema` |
| `GET` | `/v1/schemas/{schema_name}/latest` | `get_latest_schema` |
| `GET` | `/v1/schemas/{schema_name}/promotions` | `list_schema_promotions` |
| `GET` | `/v1/schemas/{schema_name}/versions` | `list_schema_versions` |
| `GET` | `/v1/schemas/{schema_name}/versions/{version}` | `get_schema_version` |
| `POST` | `/v1/schemas/{schema_name}/versions/{version}/promote` | `promote_schema_version` |
| `GET` | `/version` | `version` |
