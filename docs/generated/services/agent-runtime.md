# Agent Runtime Service endpoint reference

Source: `services/agent-runtime/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `GET` | `/v1/agents` | `list_agents` |
| `POST` | `/v1/agents/{agent_id}/execute` | `execute_agent` |
| `GET` | `/v1/connectors` | `list_connectors` |
| `POST` | `/v1/connectors/{connector_id}/actions` | `run_connector_action` |
| `GET` | `/v1/events` | `list_events` |
| `POST` | `/v1/events/publish` | `publish_event` |
| `GET` | `/v1/orchestration/config` | `get_orchestration_config` |
| `PUT` | `/v1/orchestration/config` | `update_orchestration_config` |
| `POST` | `/v1/orchestration/run` | `run_orchestration` |
| `GET` | `/version` | `version` |
