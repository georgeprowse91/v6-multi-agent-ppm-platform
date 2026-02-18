CREATE TABLE IF NOT EXISTS workflow_definitions (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    owner TEXT NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_instances (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    payload JSONB NOT NULL,
    current_step_id TEXT,
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_step_runs (
    run_id TEXT NOT NULL REFERENCES workflow_instances(run_id) ON DELETE CASCADE,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL CHECK (attempts >= 0),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    output JSONB NOT NULL,
    PRIMARY KEY (run_id, step_id)
);

CREATE TABLE IF NOT EXISTS workflow_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_instances(run_id) ON DELETE CASCADE,
    step_id TEXT,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_approvals (
    approval_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_instances(run_id) ON DELETE CASCADE,
    step_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    decision TEXT,
    approver_id TEXT,
    comments TEXT,
    metadata JSONB NOT NULL,
    UNIQUE (run_id, step_id)
);

CREATE TABLE IF NOT EXISTS workflow_state_journal (
    journal_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES workflow_instances(run_id) ON DELETE CASCADE,
    step_id TEXT,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workflow_instances_tenant_created
ON workflow_instances(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_events_run_created
ON workflow_events(run_id, created_at);
