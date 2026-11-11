import pytest
import httpx

from apps.api.contracts import RequestCreate
from gateways.llm.model import HTTPModelProvider, MockModelGateway, ModelRequirements, ProviderProfile, RoutedModelGateway
from agents.knowledge.retrieval import KnowledgeHit
from observability.otel.model import TracedModelGateway


REQUEST = RequestCreate.model_validate({
    "cloud": "aws", "environment": "sandbox", "requester": "dev@example.com",
    "application": {"name": "sample-api", "repository": "https://example.com/repo"},
    "infrastructure": {"region": "us-east-1", "module": "sandbox-api"},
    "approval": {"required": True},
})


def test_router_uses_cost_latency_reasoning_and_residency():
    gateway = RoutedModelGateway([
        (ProviderProfile("quick", 1, 200, 0.1, frozenset({"us"})), MockModelGateway()),
        (ProviderProfile("regional", 3, 800, 2.0, frozenset({"eu"})), MockModelGateway()),
        (ProviderProfile("slow", 4, 5000, 0.5, frozenset({"eu"})), MockModelGateway()),
    ], ModelRequirements(min_reasoning=3, max_latency_ms=1000,
                         max_cost_per_million_tokens=3, residency="eu"))
    assert gateway.propose(REQUEST)["action"] == "simulate"
    assert gateway.last_provider == "regional"


def test_router_fails_closed_without_eligible_provider():
    gateway = RoutedModelGateway([
        (ProviderProfile("us-only", 5, 100, 1.0, frozenset({"us"})), MockModelGateway()),
    ], ModelRequirements(residency="eu"))
    with pytest.raises(ValueError, match="no model provider"):
        gateway.propose(REQUEST)
    with pytest.raises(ValueError, match="invalid model provider"):
        ProviderProfile("bad", 0, 100, 1.0, frozenset({"eu"}))


def test_traced_gateway_does_not_send_request_content_to_langfuse():
    class Observation:
        def __init__(self):
            self.calls = []
        def start_as_current_observation(self, **kwargs):
            self.calls.append(kwargs)
            return self
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def update(self, **kwargs):
            self.calls.append(kwargs)
    observer = Observation()
    assert TracedModelGateway(MockModelGateway(), observer).propose(REQUEST)["cloud"] == "aws"
    assert "dev@example.com" not in str(observer.calls)


def test_http_provider_uses_gateway_contract_and_rejects_insecure_endpoint():
    def handle(request):
        assert request.headers["Authorization"] == "Bearer local-token"
        assert b"repo://approved" in request.content
        return httpx.Response(200, json={"proposal": MockModelGateway().propose(REQUEST)})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = HTTPModelProvider("https://model.example.test/propose", "local-token", client)
        hit = KnowledgeHit("repo://approved", "Approved", "Only this excerpt", "v1", 1.0)
        assert provider.propose(REQUEST, context=(hit,))["cloud"] == "aws"
    with pytest.raises(ValueError):
        HTTPModelProvider("http://public.example.test/propose", "token")
