# Realtime Coedit Service

## Purpose

Manages real-time collaborative document editing sessions, including WebSocket
connections, shared document state, and conflict resolution.

## Key capabilities

- WebSocket session management for collaborative editing.
- In-memory document state with versioning and conflict resolution.
- Cursor and presence updates for active collaborators.
- Session lifecycle endpoints for creation, inspection, and persistence.

## Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /healthz` | Health check. |
| `POST /sessions` | Start a co-edit session. |
| `GET /sessions/{session_id}` | Fetch session details. |
| `POST /sessions/{session_id}/stop` | Stop a session and release resources. |
| `POST /sessions/{session_id}/persist` | Persist the final document version. |
| `GET /documents/{document_id}/history` | List recent versions for a document. |
| `GET /ws/documents/{document_id}` | WebSocket endpoint for live co-editing. |

## Configuration

| Environment variable | Description | Default |
| --- | --- | --- |
| `COEDIT_MAX_HISTORY` | Maximum versions retained per document. | `25` |

## Running locally

```bash
python -m tools.component_runner run --type service --name realtime-coedit-service --dry-run
```
