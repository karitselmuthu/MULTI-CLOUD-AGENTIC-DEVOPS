"""Agent-facing answer contract with source references."""

from dataclasses import dataclass

from knowledge.retrieval.qdrant import KnowledgeHit


@dataclass(frozen=True)
class KnowledgeAnswer:
    text: str
    sources: tuple[KnowledgeHit, ...]
