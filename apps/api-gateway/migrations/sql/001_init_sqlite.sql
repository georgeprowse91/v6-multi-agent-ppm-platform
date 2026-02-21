CREATE TABLE IF NOT EXISTS document_sessions (
    session_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_by TEXT NOT NULL,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    collaborators_json TEXT NOT NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version >= 1)
);

CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version >= 1),
    content TEXT NOT NULL,
    persisted_at TEXT NOT NULL,
    persisted_by TEXT NOT NULL,
    summary TEXT,
    metadata_json TEXT NOT NULL,
    UNIQUE(document_id, version)
);

CREATE INDEX IF NOT EXISTS idx_document_sessions_tenant
ON document_sessions(tenant_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_versions_doc_version
ON document_versions(document_id, version DESC);
