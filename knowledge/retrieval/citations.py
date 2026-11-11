"""Stable source references for plans and retrieval results."""


def citation(source: str, revision: str) -> str:
    if not source or not revision:
        raise ValueError("citation needs source and revision")
    return f"{source}@{revision}"
