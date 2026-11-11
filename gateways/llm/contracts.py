"""Provider-neutral model interface used by agents and gateway adapters."""

from typing import Protocol

from apps.api.contracts import RequestCreate
from knowledge.retrieval.qdrant import KnowledgeHit


class ModelGateway(Protocol):
    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict: ...
