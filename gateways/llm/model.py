"""Provider-neutral planning interface and policy-based model routing."""

from dataclasses import dataclass
from typing import Protocol

import httpx

from apps.api.contracts import RequestCreate
from agents.knowledge.retrieval import KnowledgeHit


class ModelGateway(Protocol):
    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict: ...


class MockModelGateway:
    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        return {
            "cloud": request.cloud.value,
            "environment": request.environment.value,
            "application": request.application.name,
            "action": "simulate",
        }


@dataclass(frozen=True)
class ModelRequirements:
    min_reasoning: int = 1
    max_latency_ms: int = 3000
    max_cost_per_million_tokens: float = 5.0
    residency: str = "local"

    def __post_init__(self):
        if self.min_reasoning < 1 or self.max_latency_ms < 1 or self.max_cost_per_million_tokens < 0 or not self.residency:
            raise ValueError("invalid model routing requirements")


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    reasoning: int
    latency_ms: int
    cost_per_million_tokens: float
    residencies: frozenset[str]

    def __post_init__(self):
        if (not self.name or self.reasoning < 1 or self.latency_ms < 1 or
                self.cost_per_million_tokens < 0 or not self.residencies):
            raise ValueError("invalid model provider profile")


class RoutedModelGateway:
    def __init__(self, providers: list[tuple[ProviderProfile, ModelGateway]],
                 requirements: ModelRequirements):
        self.providers = providers
        self.requirements = requirements
        self.last_provider: str | None = None

    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        eligible = [(profile, provider) for profile, provider in self.providers
                    if profile.reasoning >= self.requirements.min_reasoning
                    and profile.latency_ms <= self.requirements.max_latency_ms
                    and profile.cost_per_million_tokens <= self.requirements.max_cost_per_million_tokens
                    and self.requirements.residency in profile.residencies]
        if not eligible:
            raise ValueError("no model provider meets routing and residency policy")
        profile, provider = min(eligible, key=lambda item: (
            item[0].cost_per_million_tokens, item[0].latency_ms, item[0].name,
        ))
        self.last_provider = profile.name
        return provider.propose(request, context=context)


class HTTPModelProvider:
    """Adapter for an internal model service implementing the gateway JSON contract.

    Source: https://www.python-httpx.org/quickstart/#sending-json-encoded-data
    """

    def __init__(self, endpoint: str, token: str, client: httpx.Client | None = None):
        loopback = endpoint.startswith(("http://127.0.0.1:", "http://localhost:"))
        if (not endpoint.startswith("https://") and not loopback) or not token:
            raise ValueError("model endpoint requires HTTPS outside loopback and a token")
        self.endpoint = endpoint
        self.token = token
        self.client = client or httpx.Client(timeout=3.0, follow_redirects=False)

    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        response = self.client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"request": request.model_dump(mode="json"),
                  "context": [{"source": hit.source, "revision": hit.revision,
                               "excerpt": hit.excerpt} for hit in context]},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("proposal"), dict):
            raise ValueError("model service returned no structured proposal")
        return payload["proposal"]
