# Repository additions integration review

The requested directories are present alongside the existing V2 tree. Status distinguishes working local code from schemas or host contracts awaiting connected systems.

| Requested addition | Status | Evidence or remaining gate |
| --- | --- | --- |
| `apps/developer-portal/` | Host contract | Backstage frontend plugin and request views build as a package; authenticated host backend and registration remain open |
| `agents/knowledge/` | Local | Retrieval-only agent, contracts and grounding instruction |
| `knowledge/ingestion/` | Local | Allowlisted repository Markdown ingestion with source and ACL metadata |
| `knowledge/chunking/` | Local | Bounded Markdown chunks with overlap and heading labels |
| `knowledge/retrieval/` | Local | Qdrant search, lexical reranking and stable citations |
| `knowledge/embeddings/` | Local | Provider contract and deterministic hash embedding; semantic model open |
| `knowledge/access_control/` | Local | Tenant/role filter applied by Qdrant before ranking |
| `gateways/llm/providers/` | Local | Mock and authenticated HTTP adapters |
| `gateways/llm/routing/` | Local | Capability, cost, latency and residency policy with bounded transport fallback |
| `gateways/llm/quotas/` | Local | Atomic in-process tenant call/cost limits; distributed accounting open |
| `data/postgres/` | Local | Versioned transactional metadata migrations; existing schema validation open |
| `data/vector_store/` | Schema only | Optional pgvector table, indexes and read RLS; no active adapter or extension test |
| `data/object_storage/` | Adapter | MinIO and local artifact adapters; connected bucket policy open |
| `data/redis/` | Adapter | Optional tenant TTL cache; connected Redis open |
| `evaluations/rag/` | Local | Fixture queries and recall/precision/rank gate |
| `evaluations/model_routing/` | Local | Policy check and fallback/quota tests |
| `evaluations/context_quality/` | Local | Citation grounding and injected-document regression |
| `observability/langfuse/` | Config only | Server-side SDK factory; connected trace export open |
| `observability/genai_tracing/` | Local | OTel span wrapper and workflow-derived trace correlation; standard propagation open |
| `docs/adr/` | Recorded | ADRs 0005–0007 explain boundaries and remaining connected gates |

Compatibility imports preserve the previous `agents/knowledge/retrieval.py`, `gateways/llm/model.py`, `orchestration/state/artifacts.py`, `orchestration/state/cache.py` and `observability/otel/` paths. No existing V2 directory was removed.
