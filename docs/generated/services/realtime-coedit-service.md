# Realtime Coedit Service endpoint reference

Source: `services/realtime-coedit-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `GET` | `/v1/documents/{document_id}/history` | `document_history` |
| `POST` | `/v1/sessions` | `start_session` |
| `GET` | `/v1/sessions/{session_id}` | `get_session` |
| `POST` | `/v1/sessions/{session_id}/persist` | `persist_session` |
| `POST` | `/v1/sessions/{session_id}/stop` | `stop_session` |
| `GET` | `/version` | `version` |
