# ADR 0001: Persist intake before starting orchestration

Status: accepted for Week 1.

## Context

The roadmap requires request contracts and persistent workflow state before recoverable agents. The repository starts with only a README. Cloud mutation must remain behind later identity, policy and approval gates.

## Decision

Use FastAPI and Pydantic for a strict intake contract. Store the request, SHA-256 request digest, workflow ID and audit event in PostgreSQL in one transaction. Require an idempotency key and enforce uniqueness in the database. Return `received` until Temporal owns transitions in Week 2. Use SQLAlchemy 2.0 ORM for persistence and a separate `init_db` local bootstrap command.

## Consequences

This provides a stable API and durable intake record. It is not yet an executable workflow or an approval system. Week 2 must add a dispatch design that avoids the database commit/Temporal start gap, for example an outbox, and add schema migrations before shared deployments.

## Sources

- https://fastapi.tiangolo.com/tutorial/body/
- https://pydantic.dev/docs/validation/latest/concepts/fields/
- https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- https://docs.sqlalchemy.org/en/20/orm/session_basics.html
