# Knowledge, model gateway and dashboard slice

The implementation keeps four kinds of data separate:

| Data | Owner | Current adapter |
| --- | --- | --- |
| Workflow request, status and audit metadata | PostgreSQL | SQLAlchemy records |
| Immutable plan and evidence artifacts | Object store | `data/object_storage/` MinIO/S3-compatible adapter; local file adapter for tests |
| Approved reference text and search vectors | Qdrant | `knowledge/` pipeline with local in-memory tests and optional authenticated service |
| Disposable context cache | Redis | `data/redis/` optional tenant-prefixed TTL adapter |

No long-lived agent memory is persisted in this slice. The optional Redis cache is disposable and cannot hold workflow approvals or durable state. If memory is added later, it needs its own tenant-scoped contract and retention policy separate from Qdrant documents and PostgreSQL workflows.

The local knowledge agent returns excerpts and `source@revision` references. The `knowledge/` pipeline separates allowlisted ingestion, Markdown chunking, embeddings, tenant/role access filters, Qdrant retrieval, reranking and citations. The planner passes retrieved excerpts through the model gateway and includes source revisions in the plan digest. A changed source revision therefore requires a new plan approval. The seed script indexes five **local fixtures** covering Terraform modules, cloud standards, security policy and a recovery runbook; `approved_by=local-fixture-only` is not a verified enterprise approval. Only an authorized document publishing service should call `KnowledgeIndex.approve` in a connected deployment.

The offline vectorizer is a deterministic 128-dimensional token hash. It makes repeatable local tests possible, but it is not a semantic embedding model and has no production retrieval-quality claim. The retrieval evaluation records recall, precision and reciprocal rank separately from existing planner, security and workflow-reliability tests. The Qdrant query applies tenant and role filters before ranking; remote Qdrant requires an API key and HTTPS except on loopback. The Qdrant service in Docker Compose binds only to loopback and uses a development key.

The model router accepts provider profiles for reasoning, estimated latency, estimated cost and allowed residency. It fails closed if no provider qualifies. Both registered local providers currently use the same offline mock implementation; no external model call or real cost measurement occurs. `HTTPModelProvider` can call a separately operated HTTPS model service with a structured JSON contract; provider capabilities and residency are operator-supplied metadata and must be validated in a connected deployment. Agents use the gateway contract and do not import provider SDKs. `TracedModelGateway` can create an OpenTelemetry span and a Langfuse generation observation when the optional observability dependencies and Langfuse credentials are configured. It sends only routing metadata, not request text or retrieved documents. API detail and worker planning spans use a workflow-derived trace ID for local correlation. A connected OTLP exporter and standard distributed context propagation are still needed for production trace continuity.

The model service contract is `POST {"request": <RequestCreate>, "context": [{"source", "revision", "excerpt"}]}` with bearer authentication and a response of `{"proposal": <PlanProposal>}`. The planner validates the response against `PlanProposal` and rejects any changed cloud, environment or application. A service that receives retrieved excerpts must treat them as untrusted data, even when the document has publishing metadata.

The React dashboard uses token-gated local API endpoints to submit requests and show workflow detail. It limits history to one configured requester. It does not provide enterprise SSO, authenticated approver identity, a live cloud inventory or production deployment history. The existing request and approval endpoints remain local-development interfaces and must be protected before external access.

## Run local Qdrant fixtures

```sh
export QDRANT_API_KEY="$(openssl rand -hex 24)"
docker compose --profile knowledge up -d qdrant
export QDRANT_URL=http://127.0.0.1:6333
export KNOWLEDGE_TENANT=local-team
export KNOWLEDGE_ROLES=planner
uv run --locked python -m agents.knowledge.seed_local
```

Use the same `QDRANT_URL`, `QDRANT_API_KEY`, `KNOWLEDGE_TENANT` and `KNOWLEDGE_ROLES` in the worker process. The worker's configured tenant and roles are a local fixture; connected deployments must derive these from authenticated workload identity rather than environment variables.

## Source references

- [Qdrant local search and filtered query](https://qdrant.tech/documentation/quickstart/)
- [Qdrant authentication and network controls](https://qdrant.tech/documentation/security/)
- [Langfuse Python observation API](https://langfuse.com/docs/observability/sdk/instrumentation)
- [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [React effects for external data](https://react.dev/reference/react/useEffect)
- [Vite development proxy](https://vite.dev/config/server-options#server-proxy)
- [MinIO Python object API](https://docs.min.io/aistor/developers/sdk/python/api/)
- [Redis Python client](https://redis.io/docs/latest/develop/clients/redis-py/)
