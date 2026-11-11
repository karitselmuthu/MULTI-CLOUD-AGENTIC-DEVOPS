CREATE TABLE IF NOT EXISTS workflows (
    id VARCHAR(36) PRIMARY KEY,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    request_digest VARCHAR(64) NOT NULL,
    request_json TEXT NOT NULL,
    cloud VARCHAR(16) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    created_at TIMESTAMPTZ NOT NULL
);
