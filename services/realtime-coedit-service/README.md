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
| `POST /v1/sessions` | Start a co-edit session. |
| `GET /v1/sessions/{session_id}` | Fetch session details. |
| `POST /v1/sessions/{session_id}/stop` | Stop a session and release resources. |
| `POST /v1/sessions/{session_id}/persist` | Persist the final document version. |
| `GET /v1/documents/{document_id}/history` | List recent versions for a document. |
| `GET /v1/ws/documents/{document_id}` | WebSocket endpoint for live co-editing. |

## Configuration

| Environment variable | Description | Default |
| --- | --- | --- |
| `COEDIT_MAX_HISTORY` | Maximum versions retained per document. | `25` |

## Running locally

```bash
python -m tools.component_runner run --type service --name realtime-coedit-service --dry-run
```

## Generated docs

- Endpoint reference (source of truth): [`docs/generated/services/realtime-coedit-service.md`](../../docs/generated/services/realtime-coedit-service.md).
- Regenerate with: `python ops/tools/codegen/generate_docs.py`.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

