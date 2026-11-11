"""Tenant and role scope applied inside the vector search query.

Source: https://qdrant.tech/documentation/search/filtering/#match-any
"""

from dataclasses import dataclass

from qdrant_client import models


@dataclass(frozen=True)
class AccessScope:
    tenant: str
    roles: tuple[str, ...]

    def __post_init__(self):
        if not self.tenant.strip() or not self.roles or any(not role.strip() for role in self.roles):
            raise ValueError("tenant and roles are required for knowledge access")


def qdrant_filter(scope: AccessScope) -> models.Filter:
    return models.Filter(must=[
        models.FieldCondition(key="tenant", match=models.MatchValue(value=scope.tenant)),
        models.FieldCondition(key="roles", match=models.MatchAny(any=list(scope.roles))),
    ])
