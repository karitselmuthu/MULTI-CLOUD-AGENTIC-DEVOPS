"""Qdrant-backed retrieval of explicitly approved reference documents.

Sources: https://qdrant.tech/documentation/quickstart/
         https://qdrant.tech/documentation/tutorials-basics/search-beginners-local/
"""

from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_URL

from qdrant_client import QdrantClient, models

from knowledge.access_control import AccessScope, qdrant_filter
from knowledge.chunking import chunk_markdown
from knowledge.embeddings import EmbeddingProvider, LocalHashEmbedding, VECTOR_SIZE
from knowledge.retrieval.rerank import rerank

COLLECTION = "approved_knowledge_v1"


@dataclass(frozen=True)
class ApprovedDocument:
    source: str
    title: str
    content: str
    tenant: str
    roles: tuple[str, ...]
    revision: str
    approved_by: str


@dataclass(frozen=True)
class KnowledgeHit:
    source: str
    title: str
    excerpt: str
    revision: str
    score: float
    chunk_index: int = 0


class KnowledgeIndex:
    def __init__(self, client: QdrantClient, collection: str = COLLECTION,
                 create: bool = True, embedder: EmbeddingProvider | None = None):
        self.client = client
        self.collection = collection
        self.embedder = embedder or LocalHashEmbedding()
        if not client.collection_exists(collection) and create:
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=self.embedder.dimensions, distance=models.Distance.COSINE),
            )

    def approve(self, document: ApprovedDocument) -> None:
        if not all((document.source, document.title, document.content, document.tenant,
                    document.revision, document.approved_by)) or not document.roles:
            raise ValueError("approved document requires source, revision, approver and access roles")
        if not document.source.startswith(("https://", "repo://")):
            raise ValueError("source must be a verifiable HTTPS or repository reference")
        if len(document.content) > 20000:
            raise ValueError("document exceeds local chunk size")
        document_filter = models.Filter(must=[
                models.FieldCondition(key="tenant", match=models.MatchValue(value=document.tenant)),
                models.FieldCondition(key="source", match=models.MatchValue(value=document.source)),
            ])
        previous_ids = []
        offset = None
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection, scroll_filter=document_filter,
                limit=100, offset=offset, with_payload=False, with_vectors=False,
            )
            previous_ids.extend(record.id for record in records)
            if offset is None:
                break
        chunks = chunk_markdown(document.content)
        points = [models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"{document.tenant}:{document.source}:{document.revision}:{chunk.index}")),
            vector=self.embedder.embed(document.title + " " + chunk.heading + " " + chunk.text),
            payload={"source": document.source, "title": document.title,
                     "content": chunk.text, "chunk_index": chunk.index,
                     "tenant": document.tenant,
                     "roles": sorted(set(document.roles)), "revision": document.revision,
                     "approved_by": document.approved_by},
        ) for chunk in chunks]
        # Write the replacement first so a failed upload preserves the approved version.
        self.client.upsert(
            collection_name=self.collection, wait=True,
            points=points,
        )
        stale_ids = list(set(previous_ids) - {point.id for point in points})
        if stale_ids:
            self.client.delete(
                collection_name=self.collection, wait=True,
                points_selector=models.PointIdsList(points=stale_ids),
            )

    def search(self, query: str, *, tenant: str, roles: tuple[str, ...], limit: int = 5) -> list[KnowledgeHit]:
        if not query.strip() or not tenant or not roles or not 1 <= limit <= 20:
            raise ValueError("query, tenant, roles and bounded limit are required")
        # Access filtering is executed by Qdrant before vector ranking, not after retrieval.
        access = qdrant_filter(AccessScope(tenant, roles))
        points = self.client.query_points(
            collection_name=self.collection, query=self.embedder.embed(query),
            query_filter=access, with_payload=True, limit=min(limit * 3, 60),
        ).points
        hits = [KnowledgeHit(
            source=str(point.payload["source"]), title=str(point.payload["title"]),
            excerpt=str(point.payload["content"])[:600],
            revision=str(point.payload["revision"]), score=float(point.score),
            chunk_index=int(point.payload.get("chunk_index", 0)),
        ) for point in points if point.payload]
        ordered = rerank(query, hits, len(hits))
        unique: list[KnowledgeHit] = []
        seen: set[tuple[str, str]] = set()
        for hit in ordered:
            key = (hit.source, hit.revision)
            if key not in seen:
                unique.append(hit)
                seen.add(key)
        return unique[:limit]


def create_index(url: str | None = None, api_key: str | None = None,
                 create: bool = False) -> KnowledgeIndex:
    """Remote Qdrant needs its own authentication and network controls."""
    loopback = url and url.startswith(("http://127.0.0.1:", "http://localhost:"))
    if url and (not url.startswith("https://") and not loopback or not api_key):
        raise ValueError("Qdrant requires an API key and HTTPS outside loopback")
    return KnowledgeIndex(QdrantClient(url=url, api_key=api_key) if url else QdrantClient(":memory:"),
                          create=create or not url)
