"""Offline provider used by local Temporal workflows."""

from apps.api.contracts import RequestCreate
from knowledge.retrieval.qdrant import KnowledgeHit


class MockModelGateway:
    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        return {
            "cloud": request.cloud.value,
            "environment": request.environment.value,
            "application": request.application.name,
            "action": "simulate",
        }
