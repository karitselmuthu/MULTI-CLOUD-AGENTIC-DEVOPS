"""Compatibility import; the knowledge pipeline now owns retrieval."""

from knowledge.embeddings.provider import VECTOR_SIZE, LocalHashEmbedding
from knowledge.retrieval.qdrant import COLLECTION, ApprovedDocument, KnowledgeHit, KnowledgeIndex, create_index


def local_embedding(value: str) -> list[float]:
    return LocalHashEmbedding().embed(value)


__all__ = ["VECTOR_SIZE", "COLLECTION", "ApprovedDocument", "KnowledgeHit", "KnowledgeIndex", "create_index", "local_embedding"]
