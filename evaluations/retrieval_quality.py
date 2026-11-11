"""Deterministic retrieval regression measures for approved reference sets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalScore:
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float


def score_retrieval(actual: list[str], expected: set[str]) -> RetrievalScore:
    if not expected:
        raise ValueError("expected references required")
    unique = list(dict.fromkeys(actual))
    matched = [source for source in unique if source in expected]
    first = next((index for index, source in enumerate(unique, 1) if source in expected), None)
    return RetrievalScore(
        recall_at_k=len(matched) / len(expected),
        precision_at_k=len(matched) / len(unique) if unique else 0.0,
        reciprocal_rank=1 / first if first else 0.0,
    )
