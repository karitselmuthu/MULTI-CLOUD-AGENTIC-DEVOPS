CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(36) NOT NULL REFERENCES workflows(id),
    event_type VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
