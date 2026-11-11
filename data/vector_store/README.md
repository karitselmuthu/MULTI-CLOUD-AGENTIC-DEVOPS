# Optional pgvector backend schema

`schema.sql` is an optional PostgreSQL vector-store schema with tenant/source indexes, a role-array index, an HNSW cosine index and row-level read policy. It is **not** applied by the control-plane metadata migrations, because the active local knowledge adapter uses Qdrant. Applying this schema requires a PostgreSQL server with the pgvector extension installed and a dedicated migration role. Its policy reads `app.tenant_id` and `app.roles` session settings; an application must set these from authenticated identity on every transaction before a query. The schema is not a production-ready vector adapter yet.

Source: [pgvector HNSW indexes](https://github.com/pgvector/pgvector#hnsw).
