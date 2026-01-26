# Audit Log Storage

Audit events are stored as JSONL records in `audit-events.jsonl` during local development.
Use `AUDIT_LOG_STORAGE_PATH` to override the default location.

Each line in the file corresponds to a single validated audit event payload.
