"""Retrieval-only local knowledge agent with source references."""

from dataclasses import dataclass

from agents.knowledge.retrieval import KnowledgeHit, KnowledgeIndex


@dataclass(frozen=True)
class KnowledgeAnswer:
    text: str
    sources: tuple[KnowledgeHit, ...]


class EnterpriseKnowledgeAgent:
    def __init__(self, index: KnowledgeIndex):
        self.index = index

    def answer(self, question: str, *, tenant: str, roles: tuple[str, ...]) -> KnowledgeAnswer:
        hits = self.index.search(question, tenant=tenant, roles=roles)
        if not hits:
            return KnowledgeAnswer("No approved source was found for this request.", ())
        return KnowledgeAnswer("\n\n".join(
            f"{hit.title}: {hit.excerpt} [{hit.source}@{hit.revision}]" for hit in hits
        ), tuple(hits))
