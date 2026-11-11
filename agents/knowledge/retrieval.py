"""Qdrant-backed retrieval of explicitly approved reference documents.

Sources: https://qdrant.tech/documentation/quickstart/
         https://qdrant.tech/documentation/tutorials-basics/search-beginners-local/
"""

import hashlib
import math
import re
from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_URL

from qdrant_client import QdrantClient, models


VECTOR_SIZE = 128
COLLECTION = "approved_knowledge_v1"
WORDS = re.compile(r"[a-z0-9][a-z0-9_-]*")


def local_embedding(value: str) -> list[float]:
    """Deterministic token vector for offline tests; replace for semantic search."""
    vector = [0.0] * VECTOR_SIZE
    for word in WORDS.findall(value.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_SIZE
        vector[index] += 1.0
    length = math.sqrt(sum(item * item for item in vector))
    return [item / length for item in vector] if length else vector


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


class KnowledgeIndex:
    def __init__(self, client: QdrantClient, collection: str = COLLECTION, create: bool = True):
        self.client = client
        self.collection = collection
        if not client.collection_exists(collection) and create:
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
            )

    def approve(self, document: ApprovedDocument) -> None:
        if not all((document.source, document.title, document.content, document.tenant,
                    document.revision, document.approved_by)) or not document.roles:
            raise ValueError("approved document requires source, revision, approver and access roles")
        if not document.source.startswith(("https://", "repo://")):
            raise ValueError("source must be a verifiable HTTPS or repository reference")
        if len(document.content) > 20000:
            raise ValueError("document exceeds local chunk size")
        point_id = str(uuid5(NAMESPACE_URL, f"{document.tenant}:{document.source}"))
        self.client.upsert(
            collection_name=self.collection, wait=True,
            points=[models.PointStruct(
                id=point_id, vector=local_embedding(document.title + " " + document.content),
                payload={"source": document.source, "title": document.title,
                         "content": document.content, "tenant": document.tenant,
                         "roles": sorted(set(document.roles)), "revision": document.revision,
                         "approved_by": document.approved_by},
            )],
        )

    def search(self, query: str, *, tenant: str, roles: tuple[str, ...], limit: int = 5) -> list[KnowledgeHit]:
        if not query.strip() or not tenant or not roles or not 1 <= limit <= 20:
            raise ValueError("query, tenant, roles and bounded limit are required")
        # Access filtering is executed by Qdrant before vector ranking, not after retrieval.
        access = models.Filter(must=[
            models.FieldCondition(key="tenant", match=models.MatchValue(value=tenant)),
            models.FieldCondition(key="roles", match=models.MatchAny(any=list(roles))),
        ])
        points = self.client.query_points(
            collection_name=self.collection, query=local_embedding(query),
            query_filter=access, with_payload=True, limit=limit,
        ).points
        return [KnowledgeHit(
            source=str(point.payload["source"]), title=str(point.payload["title"]),
            excerpt=str(point.payload["content"])[:600],
            revision=str(point.payload["revision"]), score=float(point.score),
        ) for point in points if point.payload]


def create_index(url: str | None = None, api_key: str | None = None,
                 create: bool = False) -> KnowledgeIndex:
    """Remote Qdrant needs its own authentication and network controls."""
    loopback = url and url.startswith(("http://127.0.0.1:", "http://localhost:"))
    if url and (not url.startswith("https://") and not loopback or not api_key):
        raise ValueError("Qdrant requires an API key and HTTPS outside loopback")
    return KnowledgeIndex(QdrantClient(url=url, api_key=api_key) if url else QdrantClient(":memory:"),
                          create=create or not url)
