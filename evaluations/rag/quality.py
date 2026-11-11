"""Run a retrieval fixture independently of planning/deployment gates."""

from evaluations.retrieval_quality import RetrievalScore, score_retrieval
from knowledge.retrieval.qdrant import KnowledgeIndex


def evaluate_retrieval_case(index: KnowledgeIndex, query: str, expected: set[str],
                            tenant: str, roles: tuple[str, ...]) -> RetrievalScore:
    hits = index.search(query, tenant=tenant, roles=roles)
    return score_retrieval([hit.source for hit in hits], expected)
