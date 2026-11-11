"""Simple lexical tie-breaker for offline Qdrant results."""

import re


def rerank(query: str, hits: list, limit: int) -> list:
    terms = set(re.findall(r"[a-z0-9_-]+", query.lower()))
    return sorted(hits, key=lambda hit: (
        -len(terms & set(re.findall(r"[a-z0-9_-]+", (hit.title + " " + hit.excerpt).lower()))),
        -hit.score, hit.source,
    ))[:limit]
