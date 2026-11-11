-- Optional pgvector alternative. Source: https://github.com/pgvector/pgvector#hnsw
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS approved_knowledge_chunks (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    revision TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    roles TEXT[] NOT NULL,
    approved_by TEXT NOT NULL,
    embedding vector(128) NOT NULL,
    UNIQUE (tenant_id, source_uri, revision, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_knowledge_tenant_source
    ON approved_knowledge_chunks (tenant_id, source_uri);
CREATE INDEX IF NOT EXISTS ix_knowledge_roles
    ON approved_knowledge_chunks USING gin (roles);
CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_hnsw
    ON approved_knowledge_chunks USING hnsw (embedding vector_cosine_ops);

ALTER TABLE approved_knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE approved_knowledge_chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY approved_knowledge_read ON approved_knowledge_chunks
    FOR SELECT USING (
        tenant_id = current_setting('app.tenant_id', true)
        AND roles && string_to_array(current_setting('app.roles', true), ',')
    );
