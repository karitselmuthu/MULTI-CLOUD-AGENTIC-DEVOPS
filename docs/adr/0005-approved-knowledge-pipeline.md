# ADR 0005: Approved knowledge lives outside agent state

Status: Accepted for the local prototype.

## Context

The planner needs module references, architecture guidance, policy text and runbooks, while workflow metadata and agent context have different lifetimes and access rules.

## Decision

Keep source ingestion, Markdown chunking, embeddings, access filtering and retrieval under `knowledge/`. Qdrant is the active local search adapter. Every query requires a tenant and role set, and Qdrant filters those fields before ranking. The planner passes retrieved excerpts through the model gateway and includes source revisions in the plan digest. `data/vector_store/schema.sql` documents an optional pgvector alternative; it is not applied by control-plane migrations.

## Consequences

The offline hash embedding supports repeatable tests but cannot establish semantic retrieval quality. The local seed metadata is a fixture, not an enterprise approval. Connected publishing needs authenticated approval, document revocation and representative retrieval evaluation before use in a live executor.

Sources: [Qdrant filtering](https://qdrant.tech/documentation/search/filtering/), [Qdrant security](https://qdrant.tech/documentation/security/), [pgvector HNSW](https://github.com/pgvector/pgvector#hnsw).
