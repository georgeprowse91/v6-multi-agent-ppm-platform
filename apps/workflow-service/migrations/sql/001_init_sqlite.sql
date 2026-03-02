CREATE TABLE IF NOT EXISTS workflow_definitions (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    owner TEXT NOT NULL,
    description TEXT,
    definition TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_instances (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    current_step_id TEXT,
    idempotency_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_step_runs (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL CHECK(attempts >= 0),
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    output TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id),
    FOREIGN KEY (run_id) REFERENCES workflow_instances(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES workflow_instances(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_approvals (
    approval_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    decision TEXT,
    approver_id TEXT,
    comments TEXT,
    metadata TEXT NOT NULL,
    UNIQUE (run_id, step_id),
    FOREIGN KEY (run_id) REFERENCES workflow_instances(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_state_journal (
    journal_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK(attempt >= 0),
    details TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES workflow_instances(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workflow_instances_tenant_created
ON workflow_instances(tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workflow_events_run_created
ON workflow_events(run_id, created_at);
