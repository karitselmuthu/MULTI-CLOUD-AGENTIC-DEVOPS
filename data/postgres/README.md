# Control-plane metadata migrations

`python -m apps.api.init_db` applies the ordered SQL files in `migrations/` inside a PostgreSQL transaction and records versions in `schema_migrations`. An advisory transaction lock keeps concurrent initializers from racing. The initial files create the existing workflow/audit tables and indexes. Existing databases created by the earlier SQLAlchemy `create_all` path are treated as a baseline because the table definitions are compatible; verify older custom schemas before upgrading. The runner does not apply the optional pgvector schema.

Source: [SQLAlchemy transaction handling](https://docs.sqlalchemy.org/en/20/core/connections.html#connect-and-begin-once-from-the-engine).
